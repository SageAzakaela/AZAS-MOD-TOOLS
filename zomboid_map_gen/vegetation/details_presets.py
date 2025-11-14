"""Presets for details bitmap using Rules.txt labels.

Each preset returns a dict with a 'layers' list compatible with
vegetation/detail_generator.generate(). Colors are resolved at runtime
from Rules.txt via rule_label; rule_color is a fallback if label not found.
"""

def _L(label, fallback_color, **kw):
    d = {"rule_label": label, "rule_color": fallback_color}
    d.update(kw)
    return d


def get_preset(name: str):
    name = (name or "").lower()

    if name in ("pretty", "pleasant", "default"):
        return {
            "density_multiplier": 1.0,
            "layers": [
                # Flowers on light/med grass
                _L("Flowers – Small", (240, 200, 160), density=0.03, scale=55, terrain_in=["light_grass", "med_grass"], group_size_min=1, group_size_max=2, cluster_radius=2, stride=3, jitter=1),
                # Fallen leaves near trees
                _L("Fallen Leaves (Medium)", (205, 95, 35), density=0.05, scale=70, veg_in=["trees_grass", "dense_trees_grass", "dense_forest", "fir_trees_grass"], near_radius=3, group_size_min=2, group_size_max=4, cluster_radius=2, stride=3, jitter=1),
                # Papers on asphalt
                _L("Street Trash – Papers (Sparse)", (145, 110, 75), density=0.02, scale=42, road_mode="asphalt_only", group_size_min=1, group_size_max=2, cluster_radius=1, stride=4, jitter=2),
            ],
        }

    if name in ("apocalyptic",):
        return {
            "density_multiplier": 1.2,
            "layers": [
                _L("Street Trash – Bulk (Medium)", (155, 125, 90), density=0.05, scale=40, road_mode="asphalt_only", group_size_min=2, group_size_max=4, cluster_radius=2, stride=3, jitter=2),
                _L("Street Trash – Small Scatter (Medium)", (160,130,95), density=0.05, scale=42, road_mode="asphalt_only", group_size_min=2, group_size_max=4, cluster_radius=2, stride=3, jitter=2),
                _L("Blood – Medium", (150,0,0), density=0.03, scale=38, near_road_radius=2, group_size_min=1, group_size_max=3, cluster_radius=2, stride=3, jitter=1),
                _L("Street Cracks – Medium (Sparse)", (115, 115, 115), density=0.03, scale=46, road_mode="asphalt_only", group_size_min=1, group_size_max=1, cluster_radius=1, stride=2, jitter=0),
            ],
        }

    if name in ("very apocalyptic", "very-apocalyptic"):        
        base = get_preset("apocalyptic")
        base["density_multiplier"] = 1.5
        base["layers"].append(_L("Blood – Heavy", (140,0,0), density=0.05, scale=36, near_road_radius=3, group_size_min=2, group_size_max=5, cluster_radius=2, stride=3, jitter=2))
        return base

    if name in ("overgrown world", "overgrown"):        
        return {
            "density_multiplier": 1.0,
            "layers": [
                _L("Fallen Leaves (Dense)", (200,80,20), density=0.08, scale=70, veg_in=["dense_trees_grass", "dense_forest"], near_radius=4, group_size_min=2, group_size_max=5, cluster_radius=3, stride=3, jitter=2),
                _L("Forest Twigs", (110, 85, 60), density=0.06, scale=55, veg_in=["dense_forest"], near_radius=2, group_size_min=1, group_size_max=3, cluster_radius=2, stride=3, jitter=1),
                _L("Forest Stones", (120,120,120), density=0.03, scale=55, veg_in=["dense_forest"], near_radius=2, group_size_min=1, group_size_max=2, cluster_radius=1, stride=4, jitter=1),
                _L("Sprouts", (80, 180, 80), density=0.03, scale=50, veg_in=["trees_grass","dense_trees_grass"], near_radius=2, group_size_min=1, group_size_max=2, cluster_radius=1, stride=3, jitter=1),
            ],
        }

    if name in ("autumn",):
        return {
            "density_multiplier": 1.0,
            "layers": [
                _L("Fallen Leaves (Dense)", (200,80,20), density=0.10, scale=70, veg_in=["trees_grass","dense_trees_grass","dense_forest"], near_radius=4, group_size_min=2, group_size_max=6, cluster_radius=3, stride=3, jitter=2),
                _L("Fallen Leaves (Medium)", (205,95,35), density=0.05, scale=70, veg_in=["trees_grass","dense_trees_grass","dense_forest"], near_radius=3, group_size_min=1, group_size_max=3, cluster_radius=2, stride=3, jitter=1),
                _L("Street Trash – Papers (Sparse)", (145,110,75), density=0.015, scale=42, road_mode="asphalt_only", group_size_min=1, group_size_max=2, cluster_radius=1, stride=4, jitter=1),
            ],
        }

    # Fallback: empty preset
    return {"density_multiplier": 1.0, "layers": []}

