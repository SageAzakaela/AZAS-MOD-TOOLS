# Rules & Blends Tool - Initial Design

## Overview
- Purpose: provide a single, interactive desktop tool for loading, inspecting, and editing `Rules.txt` and `Blends.txt` while being able to preview how tiles blend in an isometric view.
- Platform: Python 3 with `tkinter` for a native window, `Pillow` for image loading/previews, and standard library modules for parsing/saving.
- Layout: a split UI that exposes tile sources, datasets (rules/blends), inline editing, and a visual preview so trial and error work becomes predictable.

## Data Model
- `AliasRule` encapsulates the `name` and `tiles` list from `Rules.txt`.
- `BlendRule` stores fields such as `layer`, `mainTile`, `blendTile`, `dir`, `exclude`, plus any extra key/values to make parsing resilient.
- Tile metadata comes from scanning the `vanilla` and `custom_tiles` directories, looking for PNG sheets and inferring tile names/aliases by following the `_xx` suffix schema.
- A lightweight state file (JSON) keeps track of recently used directories, color assignments, and custom aliases so the UI can restore them between runs.

## GUI Layout
- **Left pane**: directory browser + tile list viewer that lets users click a tileset and see all tile names it contains; color swatches can be assigned to help with previews.
- **Center pane**: isometric preview canvas that stacks the selected main tile, blend tile, and directional overlays; it works with either actual tile imagery (cropping the 128x256 regions when available) or simple color-coded placeholders when the image isn't found.
- The preview uses Project Zomboid's 26.67deg isometric projection to match the in-game perspective.
- **Right pane**: tabbed editor with two tabs, "Rules" and "Blends". Each tab shows a `ttk.Treeview` list of entries and a form for editing key/value fields, including alias lists and blend settings.
- **Bottom bar**: status/status & quick actions for reloading files, saving back to disk, and toggling auto-generated preview updates.

## Workflow
1. Load `Rules.txt`/`Blends.txt` from either the vanilla pack or a custom directory.
2. Select an entry in the tree to populate the form, then edit fields or add/remove tiles within the alias list.
3. Click a tile in the tile list viewer to preview it immediately in the center pane; use the 'assign color' shortcut to keep previews legible.
4. Save changes back to the original files or export a new copy; the preview stays in sync so the designer can confirm layering/directions before applying edits.

This initial layout aims to cover the key pain points - visualizing blends, editing text-based rules, and onboarding new tilesets - before refining further features.
