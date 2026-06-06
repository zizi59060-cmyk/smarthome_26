#include "cuda_pointcloud_preprocessor/cuda_filter.hpp"

#include <cmath>

namespace cuda_pointcloud_preprocessor
{

namespace
{

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

}  // namespace cuda_pointcloud_preprocessor
