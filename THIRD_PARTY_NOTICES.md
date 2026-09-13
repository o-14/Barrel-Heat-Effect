# Third-party notices

## CommonLibF4

Barrel Heat Effect uses Dear Modding FO4's multi-runtime CommonLibF4 fork.

- Source: <https://github.com/Dear-Modding-FO4/commonlibf4>
- Pinned commit: `2aaefd104754b59b16e435b2859b299bb68dd8a2`
- License: GPL-3.0-or-later with the Modding Exception and the GPL-3.0 Linking Exception -
  `Licenses/GPL-3.0.txt`, `Licenses/GPL-3.0-EXCEPTIONS.txt`
- The original CommonLibF4, Copyright (c) 2019 ryan-rsm-mckenzie, is MIT-licensed; its notice
  is carried in the fork and reproduced as `Licenses/CommonLibF4-MIT.txt`

Its dependencies, pinned by that commit:

- **commonlib-shared** - <https://github.com/Dear-Modding-FO4/commonlib-shared> at
  `e30b310a19621ff9f635cf2c456fe633559c1c24`, GPL-3.0-or-later with the same exceptions.
- **DearModdingUI-API** - <https://github.com/Dear-Modding-FO4/DearModdingUI-API> at
  `9ddb9a8dacef8c5a116fabd3fe3a453cc446f830`, a header-only build dependency. This mod does not
  include or call it.

## spdlog

CommonLibF4 links spdlog 1.16.0 for logging.

- Source: <https://github.com/gabime/spdlog/tree/v1.16.0>
- Copyright (c) 2016 Gabi Melman
- License: MIT - `Licenses/spdlog-MIT.txt`
- Build configuration: compiled library using the C++ standard formatting library

## Required separately, not distributed

F4SE and Address Library for F4SE Plugins are required at runtime and installed by the player.
Neither is included in or linked into this mod.
