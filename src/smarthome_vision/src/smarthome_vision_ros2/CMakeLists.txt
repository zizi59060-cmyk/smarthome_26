cmake_minimum_required(VERSION 3.16)
project(smarthome_vision)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(ament_cmake REQUIRED)
find_package(ament_index_cpp REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(cv_bridge REQUIRED)
find_package(image_transport REQUIRED)
find_package(camera_info_manager REQUIRED)
find_package(robot_serial_comm REQUIRED)
find_package(OpenCV REQUIRED COMPONENTS
  core
  imgproc
  highgui
)
find_package(rosidl_default_generators REQUIRED)
find_package(OpenVINO REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/DetectedTarget.msg"
  DEPENDENCIES builtin_interfaces std_msgs
)

include_directories(
  include
  ${OpenCV_INCLUDE_DIRS}
)

add_library(${PROJECT_NAME}_core SHARED
  src/crc16.cpp
  src/pose_solver.cpp
  src/openvino_detector.cpp
  src/detector.cpp
  src/traditional_qr_detector.cpp
)

ament_target_dependencies(${PROJECT_NAME}_core
  rclcpp
  sensor_msgs
  std_msgs
  geometry_msgs
  cv_bridge
  image_transport
  camera_info_manager
  robot_serial_comm
)

target_link_libraries(${PROJECT_NAME}_core
  ${OpenCV_LIBS}
  openvino::runtime
)

add_executable(vision_node
  src/vision_node.cpp
)

ament_target_dependencies(vision_node
  ament_index_cpp
  rclcpp
  sensor_msgs
  std_msgs
  geometry_msgs
  cv_bridge
  image_transport
  camera_info_manager
  robot_serial_comm
)

target_link_libraries(vision_node
  ${PROJECT_NAME}_core
)

rosidl_get_typesupport_target(cpp_typesupport_target ${PROJECT_NAME} "rosidl_typesupport_cpp")
target_link_libraries(vision_node "${cpp_typesupport_target}")

install(TARGETS
  ${PROJECT_NAME}_core
  LIBRARY DESTINATION lib
  ARCHIVE DESTINATION lib
  RUNTIME DESTINATION bin
)

install(TARGETS
  vision_node
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY include/
  DESTINATION include/
)

install(DIRECTORY launch config assets
  DESTINATION share/${PROJECT_NAME}
)

ament_export_include_directories(include)
ament_export_dependencies(rosidl_default_runtime)

ament_package()
