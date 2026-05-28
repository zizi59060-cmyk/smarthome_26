cmake_minimum_required(VERSION 3.8)
project(robot_serial_comm)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(geometry_msgs REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/ObjectTarget.msg"
  DEPENDENCIES builtin_interfaces geometry_msgs
)

ament_python_install_package(${PROJECT_NAME})

install(
  PROGRAMS scripts/serial_comm_node
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY launch config
  DESTINATION share/${PROJECT_NAME}
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
