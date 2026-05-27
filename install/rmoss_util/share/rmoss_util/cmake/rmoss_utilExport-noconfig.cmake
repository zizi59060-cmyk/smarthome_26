#----------------------------------------------------------------
# Generated CMake target import file.
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "rmoss_util::rmoss_util" for configuration ""
set_property(TARGET rmoss_util::rmoss_util APPEND PROPERTY IMPORTED_CONFIGURATIONS NOCONFIG)
set_target_properties(rmoss_util::rmoss_util PROPERTIES
  IMPORTED_LOCATION_NOCONFIG "${_IMPORT_PREFIX}/lib/librmoss_util.so"
  IMPORTED_SONAME_NOCONFIG "librmoss_util.so"
  )

list(APPEND _cmake_import_check_targets rmoss_util::rmoss_util )
list(APPEND _cmake_import_check_files_for_rmoss_util::rmoss_util "${_IMPORT_PREFIX}/lib/librmoss_util.so" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
