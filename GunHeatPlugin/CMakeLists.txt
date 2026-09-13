cmake_minimum_required(VERSION 3.20)

# GunHeat 0.20.0 moved to Dear-Modding CommonLibF4 and xmake (xmake.lua beside this file,
# tools/build_0200.py) so one DLL supports 1.10.163, 1.10.984, 1.11.221 and 1.11.240. This CMake
# build targets the alandtse fork and 1.10.163 only and cannot compile the ported source. It is
# kept unchanged below for reference; the 0.17.x line builds from codex/puff-overlap-persistence.
message(FATAL_ERROR "GunHeat 0.20.0+ builds with xmake: run tools/build_0200.py (see docs/MULTI_RUNTIME_PLAN.md).")

option(COPY_BUILD "Copy the build output to the Fallout 4 directory." OFF)

macro(set_from_environment VARIABLE)
	if (NOT DEFINED ${VARIABLE} AND DEFINED ENV{${VARIABLE}})
		set(${VARIABLE} $ENV{${VARIABLE}})
	endif ()
endmacro()

set_from_environment(Fallout4Path)
set_from_environment(VCPKG_INSTALLATION_ROOT)
set_from_environment(CommonLibF4Path)

set(VCPKG_TARGET_TRIPLET "x64-windows-static-md" CACHE STRING "")

if (DEFINED VCPKG_INSTALLATION_ROOT)
	set(CMAKE_TOOLCHAIN_FILE "${VCPKG_INSTALLATION_ROOT}/scripts/buildsystems/vcpkg.cmake" CACHE STRING "")
else ()
	message(WARNING "VCPKG_INSTALLATION_ROOT is not set. Continuing without vcpkg.")
endif ()

set(Boost_USE_STATIC_RUNTIME OFF CACHE BOOL "")
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL" CACHE STRING "")

project(GunHeat VERSION 0.1.0 LANGUAGES CXX)

configure_file(${CMAKE_CURRENT_SOURCE_DIR}/cmake/Version.h.in ${CMAKE_CURRENT_BINARY_DIR}/include/Version.h @ONLY)
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/cmake/version.rc.in ${CMAKE_CURRENT_BINARY_DIR}/version.rc @ONLY)

if (PROJECT_SOURCE_DIR STREQUAL PROJECT_BINARY_DIR)
	message(FATAL_ERROR "In-source builds are not allowed.")
endif ()

if (MSVC AND NOT ${CMAKE_GENERATOR} STREQUAL "Ninja")
	add_compile_options(/MP)
endif ()

set(CMAKE_INTERPROCEDURAL_OPTIMIZATION ON)
set(CMAKE_INTERPROCEDURAL_OPTIMIZATION_DEBUG OFF)
set(Boost_USE_STATIC_LIBS ON)

if (NOT TARGET CommonLibF4)
	if (DEFINED CommonLibF4Path AND EXISTS "${CommonLibF4Path}/CommonLibF4/CMakeLists.txt")
		add_subdirectory("${CommonLibF4Path}/CommonLibF4" CommonLibF4)
	elseif (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/../../../Claude/Projects/Fallout Mod Expansion/CommonLibF4/CommonLibF4/CMakeLists.txt")
		add_subdirectory("${CMAKE_CURRENT_SOURCE_DIR}/../../../Claude/Projects/Fallout Mod Expansion/CommonLibF4/CommonLibF4" CommonLibF4)
	elseif (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/../CommonLibF4/CommonLibF4/CMakeLists.txt")
		add_subdirectory("${CMAKE_CURRENT_SOURCE_DIR}/../CommonLibF4/CommonLibF4" CommonLibF4)
	else ()
		message(FATAL_ERROR "CommonLibF4 not found. Set CommonLibF4Path to the checkout root.")
	endif ()
endif ()

find_package(spdlog REQUIRED CONFIG)

include(cmake/sourcelist.cmake)

source_group(TREE ${CMAKE_CURRENT_SOURCE_DIR} FILES ${SOURCES})
source_group(TREE ${CMAKE_CURRENT_BINARY_DIR} FILES ${CMAKE_CURRENT_BINARY_DIR}/include/Version.h)

add_library(${PROJECT_NAME} SHARED ${SOURCES} ${CMAKE_CURRENT_BINARY_DIR}/version.rc)

target_compile_definitions(${PROJECT_NAME} PRIVATE _UNICODE)
target_compile_features(${PROJECT_NAME} PRIVATE cxx_std_23)
target_include_directories(${PROJECT_NAME} PRIVATE ${CMAKE_CURRENT_BINARY_DIR}/include ${CMAKE_CURRENT_SOURCE_DIR}/src)
target_link_libraries(${PROJECT_NAME} PRIVATE CommonLibF4::CommonLibF4 spdlog::spdlog)
target_precompile_headers(${PROJECT_NAME} PRIVATE src/PCH.h)

if (MSVC)
	target_compile_options(${PROJECT_NAME} PRIVATE /sdl /utf-8 /Z7 /permissive- /Zc:preprocessor /W4 "$<$<CONFIG:RELEASE>:/Zc:inline;/JMC-;/Ob3>")
	target_link_options(${PROJECT_NAME} PRIVATE /WX "$<$<CONFIG:DEBUG>:/INCREMENTAL;/OPT:NOREF;/OPT:NOICF>" "$<$<CONFIG:RELEASE>:/INCREMENTAL:NO;/OPT:REF;/OPT:ICF>")
endif ()

if (COPY_BUILD)
	if (DEFINED Fallout4Path)
		add_custom_command(
			TARGET ${PROJECT_NAME}
			POST_BUILD
			COMMAND ${CMAKE_COMMAND} -E make_directory "${Fallout4Path}/Data/F4SE/Plugins"
			COMMAND ${CMAKE_COMMAND} -E copy "$<TARGET_FILE:${PROJECT_NAME}>" "${Fallout4Path}/Data/F4SE/Plugins/"
			COMMAND ${CMAKE_COMMAND} -E copy "$<TARGET_PDB_FILE:${PROJECT_NAME}>" "${Fallout4Path}/Data/F4SE/Plugins/"
		)
	else ()
		message(WARNING "Fallout4Path is not defined. Skipping post-build copy.")
	endif ()
endif ()
