"""
Lot placement helpers and prototype placement sandbox.

The production UI still hides the Lots tab, but this package provides enough
scaffolding to ingest `.tbx` building assets and sketch out auto-placement
strategies near the generated road network.
"""

from .catalog import BuildingAsset, scan_asset_catalog
from .prototype import LotPlacement, generate_prototype_layout

__all__ = [
    "BuildingAsset",
    "LotPlacement",
    "scan_asset_catalog",
    "generate_prototype_layout",
]
