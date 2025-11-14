# Prototype Lot Library

Drop your Project Zomboid `.tbx` building files in the folders below so the
auto-placement sandbox can discover them:

- `residential/`
- `commercial/`
- `industrial/`

Files can live in nested sub-folders; every `.tbx` file is indexed. The loader
attempts to read basic metadata (width, height, stories) from the XML so the
placement preview can scale the lot footprint. If a file cannot be parsed the
system falls back to the default size presets declared in `config.py`.

Additions/removals are picked up each time the generator runs; no rebuild is
required. This directory is intentionally kept under `zomboid_map_gen/assets`
so it ships with the prototype build while still allowing you to swap in a
custom root via `lots.prototype.asset_root` inside your config JSON.

## Quick test

Once you have a few `.tbx` files in place you can sketch the prototype layout
without opening the GUI:

```bash
python -m zomboid_map_gen.lots.proto_cli
```

This writes two artifacts to `output/`:

- `lots_prototype.json`: the placements, categorized with asset metadata.
- `lots_prototype_preview.png`: overlay visualizing the footprints and facing.
