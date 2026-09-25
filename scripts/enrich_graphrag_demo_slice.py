"""Inspect or apply source-backed Trial enrichment for the GraphRAG demo slice."""

from __future__ import annotations

import argparse
import json

from trialiq.services.demo_slice_enrichment import (
    enrich_demo_slice_trial_data,
    inspect_demo_slice_trial_data,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compare the NCT03416088 GraphRAG demo Trial nodes with canonical AACT "
            "study data, or refresh them from that source."
        )
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Write the allowlisted Trial fields from AACT into the existing demo Trial nodes.",
    )
    mode.add_argument(
        "--assert-synchronized",
        action="store_true",
        help="Exit non-zero unless all demo Trial fields already match AACT.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.apply:
            result = enrich_demo_slice_trial_data()
        else:
            result = inspect_demo_slice_trial_data()
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1

    print(json.dumps(result, indent=2, default=str))
    if args.assert_synchronized and not result.get("synchronized", False):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
