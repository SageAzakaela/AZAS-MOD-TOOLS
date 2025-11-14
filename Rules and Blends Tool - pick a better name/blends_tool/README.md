## Blends Editor

This focused tool only works with `Blends.txt` and exposes the blend entries, direction, and exclusion lists without the full rules/tiles complexity.

### Running
1. `pip install -r requirements.txt` (if not already).
2. `python -m blends_tool` from the repo root.

### Features
- Filter blends by their `mainTile` using the left-side filter.
- Edit layer/main/blend/direction fields on the right.
- Manage each blend’s exclusion list via the box below (add new names, remove selected ones).
- Use **Move up/down** to reorder entries and set the priority you want the optimizer to respect.
- `Optimize by priority` regenerates every `exclude` list so each blend ignores the main tiles that appear before it in that order.
- Save writes back to `vanilla/Blends.txt`; reload reverts to disk.
### Preview tab
- The leftmost **Preview** tab shows a simple placeholder canvas you can disable to speed up the rest of the UI.
- Toggle **Enable preview** to render the diamond shape (default) or switch to a black screen when you just want to work on the data.
