from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reconai_benchmark.generator import DEFAULT_SEED, generate_dataset
from reconai_benchmark.validate_dataset import validate_dataset


def main() -> None:
    root = Path(__file__).resolve().parents[3]
    build = generate_dataset(root, DEFAULT_SEED)
    result = validate_dataset(root, DEFAULT_SEED)
    if not result["valid"]:
        print(json.dumps(result, indent=2))
        raise SystemExit(1)
    print(
        json.dumps(
            {
                "generated": True,
                "seed": DEFAULT_SEED,
                "scenario_count": len(build.scenarios),
                "manifest": build.manifest,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
