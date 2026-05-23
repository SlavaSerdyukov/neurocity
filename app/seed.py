from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.simulation.engine import SimulationEngine
from app.simulation.procedural import create_world


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a deterministic NEUROCITY seed snapshot.")
    parser.add_argument("--seed", type=int, default=2049)
    parser.add_argument("--population", type=int, default=5000)
    parser.add_argument("--ticks", type=int, default=24)
    parser.add_argument("--out", type=Path, default=Path("app/data/seed_snapshot.json"))
    args = parser.parse_args()

    engine = SimulationEngine(create_world(seed=args.seed, population=args.population))
    engine.step(args.ticks)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(engine.state.to_dict(), indent=2), encoding="utf-8")
    print(f"Wrote {args.out} at tick {engine.state.tick}")


if __name__ == "__main__":
    main()

