# Metadata cleanup plan

Prepare a corrected 1.0.0 release from the published v1.0.0 source. Keep the existing author email.
Preserve existing archives and remote history until publication is explicitly approved.

1. Confirm lineage using the tag commit, retained build and published asset digest. Back up both
   existing packages and source snapshots with relative-path SHA256 manifests.
2. Work in a new branch and isolated worktree based on the public tag. Maintain a second isolated
   private worktree for source-feed fixes. Commit this plan before building.
3. Confirm compiled-script header layout using the game's disassembler. Replace only the three
   metadata strings with a bare source filename and neutral build identity. Keep all other bytes.
   Validate neutral disassembly and semantic equivalence with the existing comparison tool.
4. Remove embedded build paths using supported compiler/linker flags, with no library edits or
   binary patching. Verify the options on this compiler and build with pinned dependencies.
5. Replace absolute local paths in tracked text with relative paths, neutral examples or explicit
   environment inputs. Remove the unrelated mod attribution. Apply the source changes to the
   private source feed as well. Preserve gameplay code, settings, assets and ESP.
6. Prepare source history as a new single root commit in a separate local repository. Keep the
   dependency gitlink; verify recursive pins and rebuild from a fresh short-path clone.
7. Produce standard and Nexus install ZIPs in a new output folder. Preserve every ordered INI
   value, unchanged ESP/MCM/mesh/texture bytes, and script meaning. Use the existing packagers.
8. Scan every package entry and every tracked blob reachable from the clean commit in ASCII and
   UTF-16LE. Record only clean scan results, never the search literals. Explain binary section
   changes and explicitly identify anything not verified.
9. Stop for approval before any remote force-push, tag move, release replacement or Nexus upload.
   Provide a short game-test checklist and explain that prior downloads cannot be recalled.

The current version remains 1.0.0 at the user's request. No new gameplay or game-test claim.
