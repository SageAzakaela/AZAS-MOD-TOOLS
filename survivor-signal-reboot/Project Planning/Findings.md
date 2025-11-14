# Findings

## Official modding APIs (stored copies)
- `Project Planning/References/modding_index1.html` is the method index that ties every radio-related class into one table (e.g., `RadioScript.AddBroadcast`, `RecordedMedia.getAllMediaForCategory`, etc.).
- `Project Planning/References/zombie_radio_package.html` lists the key packages: `zombie.radio`, `zombie.radio.devices`, `zombie.radio.media`, `zombie.radio.scripting`, and the classes they register, so we know which namespaces to track.

## Radio core and scripting hooks
- `Project Planning/References/RadioAPI.html` only exposes timestamp helpers plus `getChannels`, so the real runtime control lives elsewhere.
- `Project Planning/References/RadioScript.html` (zombie.radio.scripting.RadioScript) gives us `AddBroadcast` (with optional immediate airing), `getBroadcastList`, `getValidAirBroadcast`, `getValidAirBroadcastDebug`, `getCurrentBroadcast`, and `getBroadcastWithID`. Those bindings are the starting point for any custom broadcast queue.
- `Project Planning/References/RadioBroadCast.html` lets each broadcast track its list of `RadioLine` entries, `AddRadioLine`, `getLines`, and exposes helper methods such as `getAdvertLines`, `getCurrentLine`, and `getID`, which is likely the GUID the player referenced in the old tool.
- `Project Planning/References/RadioLine.html` shows that every line carries its text, color (r/g/b), `getAirTime`, `getEffectsString`, and flags such as `isCustomAirTime`. While it does not expose moodle names directly, the effect string can include mappings (e.g., moodle/sound combos we can parse).

## Media library and broadcast content
- `Project Planning/References/MediaData.html` describes how media entries are built: `addLine(text, r, g, b, codes)`, along with getters for `getAuthorEN`, `getCategory`, and `getEffectString`. We can reuse this builder once we know how to hook real sounds to the encoded `codes` value.
- `Project Planning/References/RecordedMedia.html` exposes utilities such as `getAllMediaForCategory`, `getAllMediaForType`, `getCategories`, `getIndexForMediaData`, and `getMediaForName`. That registry is probably responsible for the baked-in broadcast library; we can investigate it to swap in new audio or metadata.

## Device and preset controls
- `Project Planning/References/DeviceData.html` handles the runtime device state: `addBattery`, `addHeadphones`, `addMediaItem`, `canBePoweredHere`, and the getters that determine what is currently active. Altering this class (or wrapping it) is how we can let a radio/TV accept new media files.
- `Project Planning/References/DevicePresets.html` manages the preset-frequency pairs with `addPreset` and `clearPresets`, so the limit on stations ties back to this tiny helper.
- `Project Planning/References/radio_devices_package.html` captures other helpers such as `DeviceEmitter`, `PresetEntry`, and the `WaveSignalDevice` interface for hooking into signal propagation.

## Application architecture & sample data
- `survivor-signal-reboot/ssr/core/models.py` defines our domain objects (`Voice`, `Line`, `Broadcast`, `Channel`, `AdvertScript`, `VHSTape`, `CDCompilation`, `RecordedMediaEntry`, etc.) plus the `Project` container that owns them. `Project.ensure_sample_data` seeds `voice_echo`, a Harbor Radio channel with a Morning Signal broadcast, a VHS reel, a CD, a sample recorded-media entry, and a starter advert so the UI opens with content when nothing vanilla is imported.
- The same module implements `AppContext`, which tracks the active broadcast/channel/VHS/CD IDs, exposes helpers like `add_broadcast` and `add_vhs`, registers refresh callbacks for UI tabs, and optionally auto-loads vanilla `RadioData.xml` and recorded media when `settings.auto_load_vanilla` from `survivor-signal-reboot/ssr/config/settings.py` is true.
- Every UI tab consumes this single source of truth, so calls to `context.notify_data_changed()` propagate through `ssr/core/models.py` and keep lists, trees, and transcripts in sync across the notebook.

## IO pipeline & serialization
- `survivor-signal-reboot/ssr/io/importers.py` parses `RadioData.xml`, records color-to-voice mappings, builds `AdvertScript`/`AdvertBroadcast` bundles, constructs `Channel` schedules, and populates `Broadcast`/`Line` data. `import_recorded_media` reads the recorded-media Lua plus the `Recorded_Media_EN.txt` translation file when present so entries keep their localized titles/authors/lines.
- `survivor-signal-reboot/ssr/io/exporter.py` walks the context, regenerates `<Voices>`, `<Channels>`, `<BroadcastEntry>`, and `<LineEntry>` nodes (with RGB values derived from the configured voice colors), writes `RadioData.xml`, and emits the companion `recorded_media.lua` plus the translation file for the recorded-media entries.
- `survivor-signal-reboot/ssr/io/serializer.py` can flatten voices, broadcasts, channels, VHS tapes, CDs, and recorded media into JSON, which the Export tab and Assistant tab reuse for snapshots, the magic button output, and saves that the user can inspect or archive.

## Gaps we still need to fill
- None of the stored HTMLs mention how static noise or the loop mode is triggered, so we may need to inspect the Java source (if available in the PZ install or the tool) or dig into `zombie.radio.globals`/`zombie.radio.devices` assets.
- Many of the high-level features (moodles tied to sound, manual tuning, overriding time progression) will require reverse-engineering how Broadcast GUIDs, Line IDs, and Advert GUIDs are consumed by the game; the docs merely expose getters/setters and not the engine behavior.
- The `File` menu (see `survivor-signal-reboot/ssr/ui/app.py`) still exposes Export/Preferences/Build Mod/About entries that have no callbacks, so wiring those to the serializer/exporter/config flows remains open.
- `ssr/ui/tabs/channels_tab.py` only lets you append schedule entries at 00:00 with day 0, so we still need UI controls for adjusting day/start/end and deleting entries before we can accurately map a broadcast timeline into the world.
- The `assistant_tab`/`planning_tab` text and buttons are placeholders powered by random strings; they will need real AI-driven prompts, timeline integration, and serialized context awareness once `ssr/ai` is implemented.

## UI/importer progress (recent work)
- `survivor-signal-reboot/ssr/ui/app.py` spins up the neon Tkinter Notebook, adds the File/Preferences/Export/Help menu bar, wires the `TAB_ORDER`, and exposes the `Load Vanilla Radio`/`Load Recorded Media` actions that delegate to `config_tab.load_*`.
- Config tab now handles manual/selected XML and Lua loads, calls the shared importer, and updates every tab via `AppContext.notify_data_changed`.
- `ssr/ui/tabs/radio_tab.py` lays out channel and broadcast lists, detailed metadata fields, line editing controls (voice, moodle, effects, sound file), transcript preview, GUID copy helpers, and buttons to refresh/apply titles that keep `AppContext` in sync.
- `ssr/ui/tabs/channels_tab.py` exposes the channel roster, frequency/category editing, auto-advert toggle, schedule list, and broadcast assignment; it is the place to surface `ChannelScheduleEntry` editing and inform the worldbuilding planner.
- `ssr/ui/tabs/voices_tab.py` provides a neon palette, text/notes area, usage stats, and a broadcast usage tree so designers can see which voices cover which broadcasts and lines.
- `ssr/ui/tabs/export_tab.py` shows the serialized JSON snapshot produced by `ssr/io/serializer.py`, lets you save it, and exports radio/recorded media XML+Lua via the exporter helpers.
- `ssr/ui/tabs/assistant_tab.py` demonstrates the "magic button" flow: canned motivations/suggestions, a prompt entry, and serialization diagnostics ready for AI integrations once `ssr/ai` is populated.
- `ssr/ui/tabs/adverts_tab.py` mirrors the radio tab but for adverts, letting you add/duplicate/delete advert scripts, manage nested broadcasts, edit lines, and copy transcripts/colors while reusing shared voice metadata.
- `ssr/ui/tabs/recorded_tab.py` and `planning_tab.py` already display recorded media entries/metadata and worldbuilding prompts, respectively, so the UI can already support storytelling context even before the AI assistant is wired up.
- The radio, voices, TV, advert, VHS, CD, and cassette tabs all register refresh callbacks so new imports instantly repaint treeviews and listboxes while keeping the dark/neon style consistent.

## Tests
- `survivor-signal-reboot/tests/test_exporter.py` ensures `export_radio_data` recreates schedules, broadcasts, and line colors correctly and that `export_recorded_media` produces the Lua/translation pair with the right keys/colors.
- `survivor-signal-reboot/tests/test_roundtrip.py` imports the actual `RadioData.xml` and recorded media from the local PZ install (when available), writes them back out, and asserts that every channel, broadcast, and line survives the roundtrip; that test is skipped if the files are missing.
- `survivor-signal-reboot/tests/conftest.py` temporarily disables `settings.auto_load_vanilla` so pytest runs with reproducible state.

## Blank-slate mod building
- The app currently loads vanilla data by default, but we need a documented workflow for starting from nothing (default voices/channels, guided planning prompts, placeholder recorded media) so authors can build entirely new mods.
- Recorded Media categories are inferred from `RecordedMedia.lua`, so we still need UI controls and data models that let users tag entries as Home VHS/Retail VHS/CD when they create them by hand.
- The Export workbench should capture the mod metadata (name, version, target folder, dependencies) so building a brand-new mod without a vanilla reference feels intentional and repeatable.
- ErinRadio reference: `Project Planning/References/ERINRADIO.xml` shows the exact voice GUIDs/colors, channels, broadcast schedules, and broadcast lines the mod uses. We can compare this to our serialized output to ensure parity, so the exporter can reproduce ErinRadio's file structure with identical GUIDs/effects.
- Mod packaging notes: the final mod folder needs `media/radio/RadioData.xml`, `media/lua/shared/RecordedMedia/recorded_media.lua`, `media/lua/shared/Translate/EN/Recorded_Media_EN.txt`, the thumbnail image (PNG), and `mod.info`/`mod.txt` descriptor. The exporter should start from a project XML/blank template, fill in the data, and copy these files into a ready-to-publish directory.

## External resources that failed to fetch
- `https://pzwiki.net/wiki/Modding` is blocked by Cloudflare (challenge page returns JavaScript), so we could not grab that wiki copy. I flagged this here so we can try a browser or another network path later.

