#----------------------------------------------------------------
# Generated CMake target import file.
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "rmoss_projectile_motion::rmoss_projectile_motion" for configuration ""
set_property(TARGET rmoss_projectile_motion::rmoss_projectile_motion APPEND PROPERTY IMPORTED_CONFIGURATIONS NOCONFIG)
set_target_properties(rmoss_projectile_motion::rmoss_projectile_motion PROPERTIES
  IMPORTED_LOCATION_NOCONFIG "${_IMPORT_PREFIX}/lib/librmoss_projectile_motion.so"
  IMPORTED_SONAME_NOCONFIG "librmoss_projectile_motion.so"
  )

list(APPEND _cmake_import_check_targets rmoss_projectile_motion::rmoss_projectile_motion )
list(APPEND _cmake_import_check_files_for_rmoss_projectile_motion::rmoss_projectile_motion "${_IMPORT_PREFIX}/lib/librmoss_projectile_motion.so" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
