# To Do

## Understanding the existing toolchain
- Unzip `WordZed.zip`/`Survivor Radio Template.zip` (or import them into a workspace) so we can inspect how the current editor stores broadcasts, lines, and preset frequency data.
- Catalog the formats/things that were painful in the original UI (alignment, testing loops, moodle associations) so the new fork avoids them.
- Trace `survivor-signal-reboot/ssr/core/models.py` (especially `Project.ensure_sample_data` and `AppContext.notify_data_changed`) so we understand how every tab refreshes when new imports or edits mutate the shared state.

## Research and experimentation
- Walk through `Project Planning/References/RadioScript.html`, `RadioBroadCast.html`, and `RadioLine.html` to confirm what parameters we can drive from our new UI, especially the broadcast ID/line data we want to reuse.
- Use the `Project Planning/References/MediaData.html` + `RecordedMedia.html` files to map the native media registry and identify where we could insert custom audio or real-world files.
- Investigate `Project Planning/References/DeviceData.html`/`DevicePresets.html` to understand how radios/TVs currently enforce preset counts and power requirements.
- Search the actual PZ install (`D:\SteamLibrary\steamapps\common\ProjectZomboid`) for the source of the static noise loop or the `Loop` mode so we know which assets/configs we can override.
- Map how `survivor-signal-reboot/ssr/config/settings.py` + `ssr/ui/tabs/config_tab.py` handle auto-loading versus manual selection so the user path for `RadioData.xml`/`recorded_media.lua` is documented and extendable.

## Design & prototypes
- Draft a new editor screen that lets us visualize broadcasts, preview audio, and tie each line to a moodle plus optional sound (with playback timing controls).
- Prototype a way to schedule broadcasts that stay in sync even if the player adjusts the in-game time manually (e.g., by storing relative timestamps or linking to `RadioScript.timeToTimeStamp`).
- Plan how to expose `DeviceEmitter`/`WaveSignalDevice` capabilities to the user so they can tweak range, signal quality, or static noise intensity.
- Design editing controls for `ChannelScheduleEntry` so the Channels tab (and worldbuilding planner) can set day/start/end ranges and delete entries instead of defaulting to day 0, start 0 every time.
- Sketch how the Assistant "magic button" and AI prompts should consume `serialize_context`/current broadcast data, so those random motivations become a real generative workflow once `ssr/ai` has content.

## Integration & automation
- Hook the File menu (Export Broadcasts, Build Mod, Preferences, etc.) in `survivor-signal-reboot/ssr/ui/app.py` up to the exporter/config/assistant helpers so every entry does something useful.
- Tie the Export tab's snapshot view and the `Magic Button` output to the same exporter/serializer pipeline so we can reuse serialized snapshots for mod builds or AI prompts without duplicating logic.

## Next steps
- Capture new findings in this folder as we go so the `Project Planning` docs stay current.
- Keep this backlog updated as experiments uncover blockers or new feature ideas.
- Validate the exporter by writing a `RadioData.xml`/`recorded_media.lua` snapshot, drop it into the game, and confirm the new broadcasts (and VHS/CD data) play as intended.
- Track the work needed for the AI Assistant tab (motivations, suggestions, magic button) and the Export tab (serializers, mod builder) once the GUI layout stabilizes.
- Add tests that cover importing/exporting the advert scripts/lines and the associated transcript data so those flows stay reliable as we edit them in the app.
- Keep documenting the AI Assistant/magic button workflow as we add real prompts so the planning notes capture how `serialize_context` and the UI interact.
- Transform the ErinRadio reference `ERINRADIO.xml` into an exporter spec: map each voice/channel/broadcast entry to our data model and verify GUID/color line mappings; document it inside `Project Planning/References` so we can track parity.
- Define the folder layout and exported files (radio XML, recorded media + translation, mod descriptor, thumbnail, optional scripts) that ErinRadio expects; plan exporter steps to copy templates and fill templates for a ready-to-publish mod folder.
- **Blank-slate / custom mod builder**
- Decide how a fresh project should start when no vanilla data is loaded (default voices/channels, sample broadcast, or a guided wizard).
- Add UI affordances to mark entries as VHS/CD/Recorded manually so the Recorded Media tab doesn’t rely on vanilla categories alone.
- Capture the steps to configure exports for a homebrew mod (metadata, package name, icons, expected folder structure) so we can automate the mod builder later.
- Ensure the Export tab or assistant can bundle the configured data into a ready-to-drop mod folder even when the project began from scratch.

