#include "Config.h"
#include "HazeManager.h"
#include "Papyrus.h"

namespace
{
	constexpr auto CONTROLLER_QUEST_ID = "GunHeatControllerQuest"sv;

	// Every runtime this DLL is built and declared for. F4SE 0.7.x enforces the last three
	// through F4SEPlugin_Version (res/commonlibf4-plugin.cpp.in), and F4SEPlugin_Query below
	// enforces the first. Load checks again so an unexpected runtime is refused with a log line
	// instead of running against addresses nobody has verified.
	constexpr std::array SUPPORTED_RUNTIMES{
		F4SE::RUNTIME_1_10_163,
		F4SE::RUNTIME_1_10_984,
		F4SE::RUNTIME_1_11_221,
		F4SE::RUNTIME_1_11_240,
	};

	[[nodiscard]] std::string_view RuntimeFamily()
	{
		if (REX::FModule::IsRuntimeOG()) {
			return "original"sv;
		}
		if (REX::FModule::IsRuntimeNG()) {
			return "next-gen"sv;
		}
		return "anniversary"sv;
	}

	void QueueControllerQuestStart()
	{
		const auto* tasks = F4SE::GetTaskInterface();
		if (!tasks) {
			logger::warn("controller quest start skipped: F4SE task interface unavailable");
			return;
		}

		tasks->AddTask([]() {
			const auto command = std::format("startquest {}", CONTROLLER_QUEST_ID);
			logger::info("executing deferred controller quest start: {}", command);
			RE::Console::ExecuteCommand(command.c_str());
			logger::info("deferred controller quest start command returned");
		});
		logger::info("controller quest start queued for next game-thread task");
	}
}

// Called only by F4SE 0.6.x, whose last release (0.6.23) is the 1.10.163 loader. F4SE 0.7.x
// reads F4SEPlugin_Version instead and never calls this.
F4SE_PLUGIN_QUERY(const F4SE::QueryInterface* a_f4se, F4SE::PluginInfo* a_info)
{
	a_info->infoVersion = F4SE::PluginInfo::kVersion;
	a_info->name = Version::PROJECT.data();
	a_info->version = Version::PACKED;

	if (a_f4se->IsEditor()) {
		return false;
	}

	return a_f4se->RuntimeVersion() == F4SE::RUNTIME_1_10_163;
}

F4SE_PLUGIN_LOAD(const F4SE::LoadInterface* a_f4se)
{
	// Same log as the 0.17.x build: GunHeat.log in My Games/Fallout4/F4SE, truncated at start,
	// flushed on every info line, and timestamped - diagnosis leans on all three.
	F4SE::Init(a_f4se, { .logName = "BarrelHeatEffect", .logPattern = "[%H:%M:%S.%e] [%^%l%$] %v" });

	// Checked before anything else touches the runtime: the library's own runtime lookup ends
	// the process for versions it does not know, and a line in the log is more useful.
	const auto runtime = a_f4se->RuntimeVersion();
	if (std::ranges::find(SUPPORTED_RUNTIMES, runtime) == SUPPORTED_RUNTIMES.end()) {
		logger::critical("{} v{}: Fallout 4 {} is not supported; this build supports 1.10.163, 1.10.984, 1.11.221 and 1.11.240",
			Version::PROJECT, Version::NAME, runtime);
		return false;
	}

	// Four runtimes are supported now, so every report needs to say which one it came from.
	logger::info("{} v{} on Fallout 4 {} ({} runtime)", Version::PROJECT, Version::NAME, runtime, RuntimeFamily());

	Config::Get().Load("Data/F4SE/Plugins/BarrelHeatEffect.ini");

	const auto* papyrus = F4SE::GetPapyrusInterface();
	if (!papyrus || !papyrus->Register(Papyrus::Register)) {
		logger::critical("failed to register Papyrus natives");
		return false;
	}

	if (const auto* messaging = F4SE::GetMessagingInterface()) {
		messaging->RegisterListener([](F4SE::MessagingInterface::Message* a_msg) {
			switch (a_msg->type) {
			case F4SE::MessagingInterface::kGameLoaded:
				logger::info("game lifecycle message {}; clearing transient visual state", a_msg->type);
				HazeManager::Get().StartPacer();
				HazeManager::Get().Clear();
				Config::Get().Load("Data/F4SE/Plugins/BarrelHeatEffect.ini");
				break;
			case F4SE::MessagingInterface::kPostLoadGame:
			case F4SE::MessagingInterface::kNewGame:
				logger::info("game lifecycle message {}; clearing transient visual state and scheduling controller", a_msg->type);
				HazeManager::Get().StartPacer();
				HazeManager::Get().Clear();
				Config::Get().Load("Data/F4SE/Plugins/BarrelHeatEffect.ini");
				QueueControllerQuestStart();
				break;
			default:
				break;
			}
		});
	}

	logger::info("loaded");
	return true;
}
