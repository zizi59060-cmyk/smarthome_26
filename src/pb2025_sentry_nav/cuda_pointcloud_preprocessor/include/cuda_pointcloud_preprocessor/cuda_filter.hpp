#pragma once

#include <cstddef>
#include <vector>

namespace cuda_pointcloud_preprocessor
{

struct PointXYZI
{
  float x;
  float y;
  float z;
  float intensity;
  float time{0.0f};
};

struct FilterConfig
{
  float min_x;
  float max_x;
  float min_y;
  float max_y;
  float min_z;
  float max_z;
  float min_range;
  float max_range;
  float min_intensity;
  float max_intensity;
};

bool cudaAvailable();

std::size_t filterCpu(
  const std::vector<PointXYZI> & input,
  std::vector<PointXYZI> & output,
  const FilterConfig & config);

std::size_t filterCuda(
  const std::vector<PointXYZI> & input,
  std::vector<PointXYZI> & output,
  const FilterConfig & config);

std::size_t voxelDownsampleCpu(
  const std::vector<PointXYZI> & input,
  std::vector<PointXYZI> & output,
  float leaf_size);

std::size_t voxelDownsampleCuda(
  const std::vector<PointXYZI> & input,
  std::vector<PointXYZI> & output,
  float leaf_size);

std::size_t voxelDownsample(
  const std::vector<PointXYZI> & input,
  std::vector<PointXYZI> & output,
  float leaf_size,
  bool prefer_cuda = true,
  bool * used_cuda = nullptr);

}  // namespace cuda_pointcloud_preprocessor
