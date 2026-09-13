#pragma once

// Version constants for the xmake build. The numbers arrive as GUNHEAT_VERSION_* defines from
// GUNHEAT_VERSION in xmake.lua, so the version is set in one place. The 0.17.x CMake build
// generated this header from cmake/Version.h.in instead; that build does not compile this source.

#define GUNHEAT_STRINGIFY_IMPL(a_value) #a_value
#define GUNHEAT_STRINGIFY(a_value) GUNHEAT_STRINGIFY_IMPL(a_value)

namespace Version
{
	inline constexpr std::uint32_t MAJOR = GUNHEAT_VERSION_MAJOR;
	inline constexpr std::uint32_t MINOR = GUNHEAT_VERSION_MINOR;
	inline constexpr std::uint32_t PATCH = GUNHEAT_VERSION_PATCH;
	inline constexpr auto          NAME = GUNHEAT_STRINGIFY(GUNHEAT_VERSION_MAJOR) "." GUNHEAT_STRINGIFY(GUNHEAT_VERSION_MINOR) "." GUNHEAT_STRINGIFY(GUNHEAT_VERSION_PATCH) ""sv;
	inline constexpr auto          PROJECT = "BarrelHeatEffect"sv;
	// What F4SEPlugin_Query reports to F4SE, packed exactly as F4SEPlugin_Version packs it, so
	// f4se.log names the same build on every runtime. Query reported MAJOR alone up to 0.20.2,
	// which is 0 for any 0.x release: on 1.10.163 - the only runtime admitted through Query -
	// f4se.log read "BarrelHeatEffect 00000000" and could not tell one build from another.
	inline constexpr std::uint32_t PACKED = REL::Version{
		static_cast<std::uint16_t>(MAJOR),
		static_cast<std::uint16_t>(MINOR),
		static_cast<std::uint16_t>(PATCH),
		0
	}.pack();
}
