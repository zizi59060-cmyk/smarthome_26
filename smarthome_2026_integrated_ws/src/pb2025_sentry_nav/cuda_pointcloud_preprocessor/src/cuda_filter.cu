#include "cuda_pointcloud_preprocessor/cuda_filter.hpp"

#include <cuda_runtime.h>
#include <thrust/copy.h>
#include <thrust/device_vector.h>
#include <thrust/host_vector.h>

#include <cmath>

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

}  // namespace cuda_pointcloud_preprocessor
