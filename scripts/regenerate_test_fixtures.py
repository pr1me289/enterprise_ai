"""Regenerate on-disk bundle fixtures under tests/fixtures/bundles/.

The fixtures are small derivative artifacts of the bundle builder — running
this script captures the current bundle shape so tests can load JSON directly
without re-running the mock pipeline on every invocation. Commit the output.

Usage:
    PYTHONPATH=src uv run python scripts/regenerate_test_fixtures.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from tests.support.bundle_builder import build_bundles  # noqa: E402

OUTPUT_DIR = REPO_ROOT / "tests" / "fixtures" / "bundles"

AGENT_FILENAMES = {
    "it_security_agent": "step_02_{scenario}.json",
    "legal_agent": "step_03_{scenario}.json",
    "procurement_agent": "step_04_{scenario}.json",
    "checklist_assembler": "step_05_{scenario}.json",
    "checkoff_agent": "step_06_{scenario}.json",
}


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for scenario in ("scenario_1", "scenario_2"):
        bundles = build_bundles(scenario)
        for agent, template in AGENT_FILENAMES.items():
            bundle = bundles.get(agent)
            if bundle is None:
                continue
            filename = template.format(scenario=scenario)
            out_path = OUTPUT_DIR / filename
            out_path.write_text(
                json.dumps(
                    {
                        "scenario": scenario,
                        "agent": agent,
                        "bundle": bundle,
                        "pipeline_run_id": bundles.get("_pipeline_run_id"),
                    },
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
            )
            written.append(out_path)
    for p in written:
        print(p.relative_to(REPO_ROOT))
    print(f"\nWrote {len(written)} fixtures.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
