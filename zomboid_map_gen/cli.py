# zomboid_map_gen/cli.py
"""
Command-line entry point.
Run with:
    python -m zomboid_map_gen.cli
"""

import argparse
import sys
import traceback
from . import config as cfg
from . import core


def main():
    print("[ZOMBOID-MAP-GEN] CLI starting...")

    parser = argparse.ArgumentParser(description="Project Zomboid map generator")
    parser.add_argument("--config", type=str, help="Path to config file (JSON).")
    args = parser.parse_args()

    try:
        if args.config:
            print(f"[ZOMBOID-MAP-GEN] Loading config from {args.config}")
            conf = cfg.load_config(args.config)
        else:
            print("[ZOMBOID-MAP-GEN] Using default config")
            conf = cfg.default_config()

        print("[ZOMBOID-MAP-GEN] Calling core.generate_from_config(...)")
        core.generate_from_config(conf)
        print("[ZOMBOID-MAP-GEN] Generation complete.")
    except Exception as e:
        print("[ZOMBOID-MAP-GEN] ERROR during generation:")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
