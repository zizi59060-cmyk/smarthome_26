#----------------------------------------------------------------
# Generated CMake target import file.
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "rmoss_cam::rmoss_cam" for configuration ""
set_property(TARGET rmoss_cam::rmoss_cam APPEND PROPERTY IMPORTED_CONFIGURATIONS NOCONFIG)
set_target_properties(rmoss_cam::rmoss_cam PROPERTIES
  IMPORTED_LOCATION_NOCONFIG "${_IMPORT_PREFIX}/lib/librmoss_cam.so"
  IMPORTED_SONAME_NOCONFIG "librmoss_cam.so"
  )

list(APPEND _cmake_import_check_targets rmoss_cam::rmoss_cam )
list(APPEND _cmake_import_check_files_for_rmoss_cam::rmoss_cam "${_IMPORT_PREFIX}/lib/librmoss_cam.so" )

# Import target "rmoss_cam::usb_cam_component" for configuration ""
set_property(TARGET rmoss_cam::usb_cam_component APPEND PROPERTY IMPORTED_CONFIGURATIONS NOCONFIG)
set_target_properties(rmoss_cam::usb_cam_component PROPERTIES
  IMPORTED_LOCATION_NOCONFIG "${_IMPORT_PREFIX}/lib/libusb_cam_component.so"
  IMPORTED_SONAME_NOCONFIG "libusb_cam_component.so"
  )

list(APPEND _cmake_import_check_targets rmoss_cam::usb_cam_component )
list(APPEND _cmake_import_check_files_for_rmoss_cam::usb_cam_component "${_IMPORT_PREFIX}/lib/libusb_cam_component.so" )

# Import target "rmoss_cam::virtual_cam_component" for configuration ""
set_property(TARGET rmoss_cam::virtual_cam_component APPEND PROPERTY IMPORTED_CONFIGURATIONS NOCONFIG)
set_target_properties(rmoss_cam::virtual_cam_component PROPERTIES
  IMPORTED_LOCATION_NOCONFIG "${_IMPORT_PREFIX}/lib/libvirtual_cam_component.so"
  IMPORTED_SONAME_NOCONFIG "libvirtual_cam_component.so"
  )

list(APPEND _cmake_import_check_targets rmoss_cam::virtual_cam_component )
list(APPEND _cmake_import_check_files_for_rmoss_cam::virtual_cam_component "${_IMPORT_PREFIX}/lib/libvirtual_cam_component.so" )

# Import target "rmoss_cam::image_task_demo_component" for configuration ""
set_property(TARGET rmoss_cam::image_task_demo_component APPEND PROPERTY IMPORTED_CONFIGURATIONS NOCONFIG)
set_target_properties(rmoss_cam::image_task_demo_component PROPERTIES
  IMPORTED_LOCATION_NOCONFIG "${_IMPORT_PREFIX}/lib/libimage_task_demo_component.so"
  IMPORTED_SONAME_NOCONFIG "libimage_task_demo_component.so"
  )

list(APPEND _cmake_import_check_targets rmoss_cam::image_task_demo_component )
list(APPEND _cmake_import_check_files_for_rmoss_cam::image_task_demo_component "${_IMPORT_PREFIX}/lib/libimage_task_demo_component.so" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
