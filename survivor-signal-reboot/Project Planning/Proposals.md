# Proposals

## QoL improvements for the editor
- Replace the existing WordZed grid with a broadcast-centric UI that shows each `RadioBroadcast` (see `Project Planning/References/RadioBroadCast.html`) and lets designers preview/move `RadioLine`s, set colors, and tie lines to moodles or sound files without juggling separate duration codes.
- Add a live preview control that uses `Project Planning/References/RadioScript.html` to call `getBroadcastWithID`/`AddBroadcast`, so we can push changes straight into the running game for testing and see how each line looks/plays.

## Expanding media control
- Let modders specify real audio files instead of the rigid in-game `RecordedMedia` entries by wrapping `Project Planning/References/MediaData.html` / `RecordedMedia.html`: map categories/types to folders, load metadata automatically, and feed them through `getAllMediaForCategory` when building a broadcast.
- Surface `DeviceData` and `DevicePresets` (see `Project Planning/References/DeviceData.html` and `DevicePresets.html`) to the UI so players can define new preset lists, enforce battery/headphone states, and attach custom media items to radios/TVs with fewer steps.
- Incorporate `WaveSignalDevice`/`DeviceEmitter` data (`Project Planning/References/radio_devices_package.html`) to allow tweaking signal range, looped static, and the number of visible stations, which the base game currently hard-codes.

## System-level proposals
- Build a project-level planner (this folder is a start) that tracks research, to-dos, and concept decisions so we can reason about broadcast GUIDs, loop state, and moodle-triggered audio in one place.
- Document the `D:\SteamLibrary\steamapps\common\ProjectZomboid` install and any relevant modding wiki references (when we can access them) so we always know where to find the engine sources that govern playback/looping.
- Use the actual `ChannelScheduleEntry` data from `survivor-signal-reboot/ssr/core/models.py` to drive the planning tab/assistant timeline so the planner and worldbuilding notes always reflect the schedule currently configured in the radio tab.

## Survivor Signal Reboot
- Build a standalone Python app named *Survivor Signal Reboot* that reflects your preferred flow: world planning -> voices/channels -> broadcast creation -> media assignment -> export/build.
- Focus the UI on a modern-retro dark mode with neon accents, Spectral Medium font where possible, and Project Zomboid inspired icons; expose the tabs you outlined (Config, Planning, Voices, Channels, Radio, Televisions, Advertisement, VHS, CDs, Cassettes, Export, Assistant) plus a customizable top bar (File, Preferences, Export, About, Donate!).
- Implement a core model (`Voice`, `Line`, `Broadcast`, `Channel`, `Project`) and media-specific modules (`ssr/media/radio.py`, `television.py`, `advertisement.py`, `vhs.py`, `cd.py`, `cassette.py`) so adding future devices (e.g., branching computer or net-voyage narratives) is straightforward.
- Create Planning/Assistant tab hooks to AI: timeline visualization, motivational prompts, suggestion generation, worldbuilding Q&A, "magic button" world/story/broadcast generation, and refine options for every generated item.
- Feed the `serialize_context` output into `ssr/ai` so the assistant/magic button evolves from the present random motivators into real generative prompts that can suggest new lines, adverts, or recorded media that align with the currently active voices, broadcasts, and schedule.
- Keep the Python project organized with `ssr/core`, `ssr/ui`, `ssr/media`, `ssr/io`, `ssr/ai`, and `ssr/utils` packages so documentation, IO/export logic, and the new feature set stay coordinated with what we've already captured in `Project Planning`.

