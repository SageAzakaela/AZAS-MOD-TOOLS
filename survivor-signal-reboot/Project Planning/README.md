# Project Planning

## Motivation
- Rebuild WordZed so the interface for building and testing radio mods is less tedious and more reliable.
- Give modders explicit control over broadcasts, moods, static noise, device loops, and the kinds of media that can be attached to radios/TVs.

## Resources captured here
- `Project Planning\References/modding_index1.html` plus the per-package pages (radio summary, `RadioScript`, `RadioBroadCast`, `RadioLine`, `MediaData`, `RecordedMedia`, `RadioAPI`, and the device/effects package summaries) document the low-level APIs we can drive.
- `D:\SteamLibrary\steamapps\common\ProjectZomboid` is still the authoritative game install we can use for testing/asset grabs.
- The `WordZed.zip` and `Survivor Radio Template.zip` archives show how the existing tooling packages its data.

## Where to start
- Read `Findings.md` for the concrete hooks exposed by the stock APIs.
- Use `Concepts.md` to keep the vocabulary we want to support aligned.
- Officer the `ToDo.md` backlog whenever new insights arrive.
- Proposals are in `Proposals.md` so we can compare future ideas against what we already intend to do.
- Explore the `survivor-signal-reboot/ssr/ui` module for the neon, tabbed GUI layout and `run.py` once we begin wiring the actual Python app.
- The `survivor-signal-reboot/ssr/core` module now provides `AppContext` plus sample voices/channels, and the `voices_tab`, `channels_tab`, `radio_tab`, `tv_tab`, VHS/CD/ad/assistant tabs, and the export tab consume that shared state for editing names, colors, frequencies, schedules, broadcasts, and other media metadata.
- The `File` menu now exposes “Load Vanilla Radio”/“Load Recorded Media”, which populate every tab (radio, TV, VHS, CDs) from `RadioData.xml` and `recorded_media.lua` using the default Project Zomboid install path so the UI opens straight into the vanilla broadcasts if the config flag is enabled; imported voices get playful “Robert X” aliases so you can follow them easily while testing.
- Settings (see `ssr/config/settings.py`) default to `D:\SteamLibrary\steamapps\common\ProjectZomboid`, but you can override `PZ_HOME` or edit the dataclass if your install lives elsewhere or you want a blank slate.
- `ssr/io/exporter.py` plus the Export tab now write `RadioData.xml`, `recorded_media.lua`, and `Recorded_Media_EN.txt` so you can generate mod-ready files for Project Zomboid and compare them to the vanilla data.
- `survivor-signal-reboot/ssr/ui/tabs/export_tab.py` and `survivor-signal-reboot/ssr/ui/tabs/assistant_tab.py` now show how to serialize the shared state (via `ssr/io/serializer.py`) so we can surface AI prompts, magic-button summaries, and export-ready snapshots ready for mod packaging.
- `survivor-signal-reboot/ssr/io/serializer.py` can already convert the configured voices, channels, and broadcasts (including GUIDs) into a JSON-friendly structure for future export work.

