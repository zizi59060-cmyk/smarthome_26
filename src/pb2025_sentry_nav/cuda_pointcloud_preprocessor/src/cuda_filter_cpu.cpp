#include "cuda_pointcloud_preprocessor/cuda_filter.hpp"

#include <cmath>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <unordered_map>

namespace cuda_pointcloud_preprocessor
{

namespace
{

struct Accumulator
{
  float x{0.0f};
  float y{0.0f};
  float z{0.0f};
  float intensity{0.0f};
  float time{0.0f};
  int count{0};
};

bool passFilter(const PointXYZI & point, const FilterConfig & config)
{
  if (!std::isfinite(point.x) || !std::isfinite(point.y) || !std::isfinite(point.z)) {
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

std::int64_t voxelKey(const PointXYZI & point, float leaf_size)
{
  constexpr std::int64_t mask = (1LL << 21) - 1LL;
  constexpr std::int64_t bias = 1LL << 20;

  const auto ix = static_cast<std::int64_t>(std::floor(point.x / leaf_size));
  const auto iy = static_cast<std::int64_t>(std::floor(point.y / leaf_size));
  const auto iz = static_cast<std::int64_t>(std::floor(point.z / leaf_size));

  if (
    ix < -bias || ix >= bias || iy < -bias || iy >= bias || iz < -bias || iz >= bias) {
    return std::numeric_limits<std::int64_t>::max();
  }

  return ((ix + bias) & mask) << 42 | ((iy + bias) & mask) << 21 | ((iz + bias) & mask);
}

}  // namespace

#ifndef CUDA_POINTCLOUD_PREPROCESSOR_HAS_CUDA
bool cudaAvailable()
{
  return false;
}

std::size_t filterCuda(
  const std::vector<PointXYZI> & input,
  std::vector<PointXYZI> & output,
  const FilterConfig & config)
{
  return filterCpu(input, output, config);
}

std::size_t voxelDownsampleCuda(
  const std::vector<PointXYZI> & input,
  std::vector<PointXYZI> & output,
  float leaf_size)
{
  (void)leaf_size;
  return voxelDownsampleCpu(input, output, leaf_size);
}
#endif

std::size_t filterCpu(
  const std::vector<PointXYZI> & input,
  std::vector<PointXYZI> & output,
  const FilterConfig & config)
{
  output.clear();
  output.reserve(input.size());

  for (const auto & point : input) {
    if (passFilter(point, config)) {
      output.push_back(point);
    }
  }

  return output.size();
}

std::size_t voxelDownsampleCpu(
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

  std::unordered_map<std::int64_t, Accumulator> voxels;
  voxels.reserve(input.size());

  for (const auto & point : input) {
    if (!std::isfinite(point.x) || !std::isfinite(point.y) || !std::isfinite(point.z)) {
      continue;
    }
    const auto key = voxelKey(point, leaf_size);
    if (key == std::numeric_limits<std::int64_t>::max()) {
      continue;
    }
    auto & acc = voxels[key];
    acc.x += point.x;
    acc.y += point.y;
    acc.z += point.z;
    acc.intensity += point.intensity;
    acc.time += point.time;
    acc.count += 1;
  }

  output.reserve(voxels.size());
  for (const auto & item : voxels) {
    const auto & acc = item.second;
    if (acc.count <= 0) {
      continue;
    }
    const auto inv_count = 1.0f / static_cast<float>(acc.count);
    output.push_back(PointXYZI{
      acc.x * inv_count,
      acc.y * inv_count,
      acc.z * inv_count,
      acc.intensity * inv_count,
      acc.time * inv_count});
  }

  return output.size();
}

std::size_t voxelDownsample(
  const std::vector<PointXYZI> & input,
  std::vector<PointXYZI> & output,
  float leaf_size,
  bool prefer_cuda,
  bool * used_cuda)
{
  if (used_cuda) {
    *used_cuda = false;
  }

  if (prefer_cuda && cudaAvailable()) {
    try {
      const auto size = voxelDownsampleCuda(input, output, leaf_size);
      if (used_cuda) {
        *used_cuda = true;
      }
      return size;
    } catch (const std::exception &) {
      if (used_cuda) {
        *used_cuda = false;
      }
    }
  }

  return voxelDownsampleCpu(input, output, leaf_size);
}

}  // namespace cuda_pointcloud_preprocessor
