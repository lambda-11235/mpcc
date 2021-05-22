
cmake_minimum_required(VERSION 3.0)
project(mudt)

include_directories(${CMAKE_CURRENT_SOURCE_DIR}/lib)
set(CMAKE_CXX_STANDARD 11)

add_subdirectory(lib)
add_subdirectory(src)
