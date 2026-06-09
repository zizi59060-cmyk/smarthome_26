cmake_minimum_required(VERSION 3.10)
project(cuda_pointcloud_preprocessor)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)

include(CheckLanguage)
check_language(CUDA)
if(CMAKE_CUDA_COMPILER)
  enable_language(CUDA)
  find_package(CUDAToolkit QUIET)
endif()

add_library(pointcloud_filter
  src/cuda_filter_cpu.cpp
)

target_include_directories(pointcloud_filter PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

if(CMAKE_CUDA_COMPILER AND CUDAToolkit_FOUND)
  target_sources(pointcloud_filter PRIVATE src/cuda_filter.cu)
  target_compile_definitions(pointcloud_filter PUBLIC CUDA_POINTCLOUD_PREPROCESSOR_HAS_CUDA=1)
  set_target_properties(pointcloud_filter PROPERTIES
    CUDA_SEPARABLE_COMPILATION ON
    CUDA_STANDARD 17
    CUDA_STANDARD_REQUIRED ON)
  target_link_libraries(pointcloud_filter CUDA::cudart)
else()
  message(WARNING "CUDA toolkit not found. cuda_pointcloud_preprocessor will build with CPU fallback only.")
endif()

add_executable(cuda_pointcloud_preprocessor_node
  src/cuda_pointcloud_preprocessor_node.cpp
)

target_link_libraries(cuda_pointcloud_preprocessor_node pointcloud_filter)
ament_target_dependencies(cuda_pointcloud_preprocessor_node
  rclcpp
  sensor_msgs
)

install(TARGETS pointcloud_filter
  EXPORT export_pointcloud_filter
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)

install(TARGETS cuda_pointcloud_preprocessor_node
  RUNTIME DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY include/
  DESTINATION include
)

ament_export_include_directories(include)
ament_export_libraries(pointcloud_filter)
ament_export_targets(export_pointcloud_filter HAS_LIBRARY_TARGET)
ament_package()
