-- GunHeat: one DLL for Fallout 4 1.10.163, 1.10.984, 1.11.221 and 1.11.240.
--
-- Built on Dear-Modding-FO4 CommonLibF4 (lib/commonlibf4, a pinned submodule), which carries
-- per-runtime relocation IDs for the original, next-gen and anniversary runtimes. The CMake
-- build beside this file targets the alandtse fork and 1.10.163 only; it belongs to the 0.17.x
-- line and cannot build this source. See docs/MULTI_RUNTIME_PLAN.md.
--
-- Build with tools/build_0200.py, which pins the xmake binary and the library commits.

set_xmakever("3.0.0")

local GUNHEAT_VERSION = "1.0.0"

set_languages("c++23")
set_warnings("allextra")
set_encodings("utf-8")

add_rules("mode.releasedbg")
set_defaultmode("releasedbg")

-- Keep build-machine paths out of runtime diagnostics and the PE debug directory.
-- Apply in the parent scope so included library targets use the same compiler option.
local source_root = path.translate(path.directory(os.scriptdir())) .. "\\"
add_cxflags("/d1trimfile:" .. source_root, { tools = "cl", force = true })
add_shflags("/PDBALTPATH:%_PDB%", { tools = "link", force = true })

includes("lib/commonlibf4")

-- Set after the include: the library's own xmake files call set_project too, and the last call
-- names the project in the DLL's version resource. Set before it, ProductName read
-- "dearmoddingui-api".
set_project("GunHeat")
set_version(GUNHEAT_VERSION)
set_license("GPL-3.0-or-later")

local major, minor, patch = GUNHEAT_VERSION:match("^(%d+)%.(%d+)%.(%d+)$")

target("BarrelHeatEffect", function()
    -- The plugin rule builds the DLL, its version resource and F4SEPlugin_Version. Its
    -- template is replaced by res/commonlibf4-plugin.cpp.in - the file name must stay the
    -- same, because the rule compiles the generated file by that name - so the DLL declares
    -- exactly the runtimes above instead of every next-gen and anniversary build.
    add_rules("commonlibf4.plugin", {
        name = "BarrelHeatEffect",
        author = "o14",
        description = "Animated barrel heat-refraction haze",
        plugin_template = path.join(os.scriptdir(), "res", "commonlibf4-plugin.cpp.in")
    })

    -- Numbers only: src/Version.h builds the version string from these, which avoids passing
    -- a quoted string through the compiler command line.
    add_defines(
        "GUNHEAT_VERSION_MAJOR=" .. major,
        "GUNHEAT_VERSION_MINOR=" .. minor,
        "GUNHEAT_VERSION_PATCH=" .. patch
    )

    add_files("src/*.cpp")
    add_headerfiles("src/*.h")
    add_includedirs("src")
    set_pcxxheader("src/PCH.h")

    -- The plugin rule installs after every build. Keep that inside the build tree: this project
    -- never deploys from a build, and the verified DLL is copied into Data/ by hand.
    set_installdir(path.join(os.scriptdir(), "build-xmake", "install"))
end)
