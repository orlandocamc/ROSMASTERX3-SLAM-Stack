cmake_minimum_required(VERSION 3.8)
project(rosmaster_zmq_bridge)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY launch
  DESTINATION share/${PROJECT_NAME}
)

install(
  PROGRAMS
    scripts/zmq_video_publisher.py
    scripts/zmq_sensors_publisher.py
    scripts/zmq_cmd_subscriber.py
    scripts/flask_teleop_server.py
  DESTINATION lib/${PROJECT_NAME}
)

install(
  DIRECTORY examples
  DESTINATION share/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
