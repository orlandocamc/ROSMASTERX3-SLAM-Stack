cmake_minimum_required(VERSION 3.8)
project(rosmaster_bringup)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY launch config rviz gazebo
  DESTINATION share/${PROJECT_NAME}
)

install(
  PROGRAMS scripts/twist_stamper.py
  DESTINATION lib/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
