cmake_minimum_required(VERSION 3.8)
project(rosmaster_hardware)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY launch
  DESTINATION share/${PROJECT_NAME}
)

install(
  PROGRAMS
    scripts/yahboom_driver.py
    scripts/rosmaster_odom.py
    scripts/heading_controller.py
    scripts/safety_stop.py
  DESTINATION lib/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
