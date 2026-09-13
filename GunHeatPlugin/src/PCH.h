#pragma once

#include "F4SE/F4SE.h"
#include "RE/Fallout.h"

#include <spdlog/spdlog.h>

#include <algorithm>
#include <array>
#include <atomic>
#include <cctype>
#include <charconv>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstring>
#include <filesystem>
#include <format>
#include <fstream>
#include <functional>
#include <mutex>
#include <string>
#include <string_view>
#include <type_traits>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <variant>

using namespace std::literals;

// Dear-Modding's F4SE::Init installs spdlog as the default logger. The logger:: calls
// throughout the source predate the library switch and keep their names through this.
namespace logger
{
	using spdlog::critical;
	using spdlog::debug;
	using spdlog::error;
	using spdlog::info;
	using spdlog::trace;
	using spdlog::warn;
}

#include "Version.h"
