// Compile-time guards on every engine field GunHeat reads or writes.
//
// The values are the offsets the compiler actually produced for the 0.17.x build - alandtse
// CommonLibF4 on 1.10.163, proven in game - probed with that build's exact compiler flags. The
// Dear-Modding CommonLibF4 this build uses compiles every one of them to the same offset, and it
// treats these classes as identical on 1.10.163, 1.10.984 and 1.11.x, so one set of offsets
// serves all four runtimes.
//
// Do not take offsets from the "// NN" comments in either library's headers. In both libraries
// they are stale for ModelReferenceEffect::artObject3D (comment 0xD0, compiled 0xC8) and
// BSLightingShaderMaterialBase::refractionPower (comment 0x78, compiled 0x84). These asserts
// caught that on the first 0.20.0 build, when they had been copied from the comments.
//
// If a library update ever moves one of these, the build fails here instead of the game reading
// the wrong memory.

namespace
{
	using EquippedItem = std::remove_cvref_t<decltype(std::declval<RE::MiddleHighProcessData&>().equippedItems[0])>;
	using ObjectInstance = decltype(std::declval<EquippedItem&>().item);
}

// HazeManager::FindFireNode - the player's muzzle node
static_assert(offsetof(RE::Actor, currentProcess) == 0x300);
static_assert(offsetof(RE::AIProcess, middleHigh) == 0x08);
static_assert(offsetof(RE::MiddleHighProcessData, equippedItems) == 0x288);
static_assert(offsetof(EquippedItem, item) == 0x00);
static_assert(offsetof(EquippedItem, data) == 0x20);
static_assert(offsetof(ObjectInstance, object) == 0x00);
static_assert(offsetof(RE::EquippedWeaponData, fireNode) == 0x30);

// HazeManager - the art object's 3D, parking and teardown
static_assert(offsetof(RE::ModelReferenceEffect, artObject3D) == 0xC8);
static_assert(offsetof(RE::ReferenceEffect, finished) == 0x40);
static_assert(offsetof(RE::BSTempEffect, lifetime) == 0x10);

// HazeManager - scene graph walk, placement and size
static_assert(offsetof(RE::NiAVObject, local) == 0x30);
static_assert(offsetof(RE::NiAVObject, world) == 0x70);
static_assert(offsetof(RE::NiNode, children) == 0x120);
static_assert(offsetof(RE::BSGeometry, properties) == 0x130);

// HazeManager::ApplyRefraction / ApplyScroll - the material the effect is driven through
static_assert(offsetof(RE::BSShaderProperty, material) == 0x58);
static_assert(offsetof(RE::BSShaderMaterial, texCoordOffset) == 0x0C);
static_assert(offsetof(RE::BSLightingShaderMaterialBase, refractionPower) == 0x84);

// Config - weapon typing and caliber-scaled heat
static_assert(offsetof(RE::TESObjectWEAP, weaponData) == 0x198);
static_assert(offsetof(RE::TESAmmo, data) == 0x160);
static_assert(offsetof(RE::AMMO_DATA, projectile) == 0x00);
static_assert(offsetof(RE::AMMO_DATA, damage) == 0x10);
