# Concept List

- **Broadcasts**: `zombie.radio.scripting.RadioBroadCast` (see `Project Planning/References/RadioBroadCast.html`) wraps a sequence of `RadioLine`s, has an ID/GUID, and lets the script build new schedules with `AddRadioLine` and `getCurrentLine`.
- **Lines**: `RadioLine` holds the text, RGB color, airtime, effects code, and custom-time flag that define what the player actually hears/reads (see `Project Planning/References/RadioLine.html`). It is the natural place to capture moodle-to-audio pairings.
- **Broadcast scripting**: `RadioScript` (see `Project Planning/References/RadioScript.html`) exposes `AddBroadcast`, `getValidAirBroadcast`, `getCurrentBroadcast`, and the broadcast list itself, making it the main entry point for dynamically injecting radio content.
- **Media catalog**: `MediaData` and `RecordedMedia` (see `Project Planning/References/MediaData.html` and `Project Planning/References/RecordedMedia.html`) describe the raw media lines and the registry helpers (`getAllMediaForCategory`, `getIndexForMediaData`, etc.) that we can repurpose to point at new sound assets.
- **Device state**: `DeviceData` (see `Project Planning/References/DeviceData.html`) ties the hardware (battery, headphones, media items) to the scripts. `DevicePresets` (see `Project Planning/References/DevicePresets.html`) is the narrow spot that currently controls the limited preset/frequency list.
- **Device signal plumbing**: `DeviceEmitter`, `PresetEntry`, and the `WaveSignalDevice` interface shown in `Project Planning/References/radio_devices_package.html` model how radios/TVs broadcast signals through the world, which matters if we want to inject new loops or static noise layers.
- **Radio API surface**: `RadioAPI` is limited to timestamp helpers and `getChannels` (see `Project Planning/References/RadioAPI.html`), so the rest of our feature set has to live in the scripting and media packages.
- **Existing tools**: `WordZed.zip` and `Survivor Radio Template.zip` (stored in the repo root) show how the old UI packaged broadcasts; we will mine them for layout ideas and formats we aim to improve.

