#include "cuda_pointcloud_preprocessor/cuda_filter.hpp"

#include <cuda_runtime.h>
#include <thrust/copy.h>
#include <thrust/device_vector.h>
#include <thrust/functional.h>
#include <thrust/host_vector.h>
#include <thrust/iterator/transform_iterator.h>
#include <thrust/remove.h>
#include <thrust/reduce.h>
#include <thrust/sort.h>
#include <thrust/transform.h>

#include <cmath>
#include <cstdint>
#include <limits>

namespace cuda_pointcloud_preprocessor
{

struct FilterPredicate
{
  FilterConfig config;

  __host__ __device__ static bool isFinite(float value)
  {
    return !isnan(value) && !isinf(value);
  }

  __host__ __device__ bool operator()(const PointXYZI & point) const
  {
    if (!isFinite(point.x) || !isFinite(point.y) || !isFinite(point.z)) {
      return false;
    }

    if (point.x < config.min_x || point.x > config.max_x || point.y < config.min_y ||
        point.y > config.max_y || point.z < config.min_z || point.z > config.max_z) {
      return false;
    }

    if (point.intensity < config.min_intensity || point.intensity > config.max_intensity) {
      return false;
    }

    const float range_sq = point.x * point.x + point.y * point.y + point.z * point.z;
    return range_sq >= config.min_range * config.min_range &&
           range_sq <= config.max_range * config.max_range;
  }
};

struct VoxelPoint
{
  long long key;
  float x;
  float y;
  float z;
  float intensity;
  float time;
  int count;
};

constexpr long long kInvalidVoxelKey = 0x7fffffffffffffffLL;

struct MakeVoxelPoint
{
  float leaf_size;

  __host__ __device__ long long makeKey(const PointXYZI & point) const
  {
    constexpr long long mask = (1LL << 21) - 1LL;
    constexpr long long bias = 1LL << 20;

    const long long ix = static_cast<long long>(floorf(point.x / leaf_size));
    const long long iy = static_cast<long long>(floorf(point.y / leaf_size));
    const long long iz = static_cast<long long>(floorf(point.z / leaf_size));

    if (ix < -bias || ix >= bias || iy < -bias || iy >= bias || iz < -bias || iz >= bias) {
      return kInvalidVoxelKey;
    }

    return ((ix + bias) & mask) << 42 | ((iy + bias) & mask) << 21 | ((iz + bias) & mask);
  }

  __host__ __device__ VoxelPoint operator()(const PointXYZI & point) const
  {
    if (
      !(leaf_size > 0.0f) || !FilterPredicate::isFinite(point.x) ||
      !FilterPredicate::isFinite(point.y) || !FilterPredicate::isFinite(point.z)) {
      return VoxelPoint{kInvalidVoxelKey, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0};
    }

    return VoxelPoint{
      makeKey(point), point.x, point.y, point.z, point.intensity, point.time, 1};
  }
};

struct IsInvalidVoxelPoint
{
  __host__ __device__ bool operator()(const VoxelPoint & point) const
  {
    return point.key == kInvalidVoxelKey || point.count <= 0;
  }
};

struct VoxelPointKeyLess
{
  __host__ __device__ bool operator()(const VoxelPoint & lhs, const VoxelPoint & rhs) const
  {
    return lhs.key < rhs.key;
  }
};

struct SameVoxelKey
{
  __host__ __device__ bool operator()(const VoxelPoint & lhs, const VoxelPoint & rhs) const
  {
    return lhs.key == rhs.key;
  }
};

struct VoxelKey
{
  __host__ __device__ long long operator()(const VoxelPoint & point) const { return point.key; }
};

struct VoxelPointSum
{
  __host__ __device__ VoxelPoint operator()(const VoxelPoint & lhs, const VoxelPoint & rhs) const
  {
    return VoxelPoint{
      lhs.key,
      lhs.x + rhs.x,
      lhs.y + rhs.y,
      lhs.z + rhs.z,
      lhs.intensity + rhs.intensity,
      lhs.time + rhs.time,
      lhs.count + rhs.count};
  }
};

struct VoxelCentroid
{
  __host__ __device__ PointXYZI operator()(const VoxelPoint & point) const
  {
    const float inv_count = point.count > 0 ? 1.0f / static_cast<float>(point.count) : 0.0f;
    return PointXYZI{
      point.x * inv_count,
      point.y * inv_count,
      point.z * inv_count,
      point.intensity * inv_count,
      point.time * inv_count};
  }
};

bool cudaAvailable()
{
  int device_count = 0;
  return cudaGetDeviceCount(&device_count) == cudaSuccess && device_count > 0;
}

std::size_t filterCuda(
  const std::vector<PointXYZI> & input,
  std::vector<PointXYZI> & output,
  const FilterConfig & config)
{
  output.clear();
  if (input.empty()) {
    return 0;
  }

  thrust::device_vector<PointXYZI> device_input(input.begin(), input.end());
  thrust::device_vector<PointXYZI> device_output(input.size());
  const auto output_end =
    thrust::copy_if(device_input.begin(), device_input.end(), device_output.begin(), FilterPredicate{config});
  const auto output_size = static_cast<std::size_t>(output_end - device_output.begin());

  output.resize(output_size);
  thrust::copy(device_output.begin(), output_end, output.begin());
  return output.size();
}

std::size_t voxelDownsampleCuda(
  const std::vector<PointXYZI> & input,
  std::vector<PointXYZI> & output,
  float leaf_size)
{
  output.clear();
  if (input.empty()) {
    return 0;
  }
  if (!(leaf_size > 0.0f) || !std::isfinite(leaf_size)) {
    output = input;
    return output.size();
  }

  thrust::device_vector<PointXYZI> device_input(input.begin(), input.end());
  thrust::device_vector<VoxelPoint> keyed_points(input.size());
  thrust::transform(
    device_input.begin(), device_input.end(), keyed_points.begin(), MakeVoxelPoint{leaf_size});

  const auto valid_end =
    thrust::remove_if(keyed_points.begin(), keyed_points.end(), IsInvalidVoxelPoint{});
  keyed_points.erase(valid_end, keyed_points.end());
  if (keyed_points.empty()) {
    return 0;
  }

  thrust::sort(keyed_points.begin(), keyed_points.end(), VoxelPointKeyLess{});

  thrust::device_vector<long long> reduced_keys(keyed_points.size());
  thrust::device_vector<VoxelPoint> reduced_points(keyed_points.size());
  const auto key_begin = thrust::make_transform_iterator(keyed_points.begin(), VoxelKey{});
  const auto reduced_end = thrust::reduce_by_key(
    key_begin, key_begin + keyed_points.size(), keyed_points.begin(), reduced_keys.begin(),
    reduced_points.begin(), thrust::equal_to<long long>(), VoxelPointSum{});
  const auto reduced_size = static_cast<std::size_t>(reduced_end.second - reduced_points.begin());

  thrust::device_vector<PointXYZI> centroids(reduced_size);
  thrust::transform(
    reduced_points.begin(), reduced_points.begin() + reduced_size, centroids.begin(),
    VoxelCentroid{});

  output.resize(reduced_size);
  thrust::copy(centroids.begin(), centroids.end(), output.begin());
  return output.size();
}

}  // namespace cuda_pointcloud_preprocessor
