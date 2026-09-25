"""Batch 13 canonical GraphRAG load + reconciliation entry point."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from trialiq.etl.canonical_graphrag import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_VERIFICATION_LIMIT,
    MAX_BATCH_SIZE,
    load_canonical_core_graph,
)


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Load AACT Trial/Condition/Intervention/Sponsor data into the "
            "canonical TrialIQ graph and reconcile the loaded scope."
        )
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--verification-load",
        action="store_true",
        help=(
            "Load a bounded deterministic NCT-ID-ordered scope and reconcile it. "
            f"Default scope: {DEFAULT_VERIFICATION_LIMIT} trials."
        ),
    )
    mode.add_argument(
        "--full-load",
        action="store_true",
        help="Load and reconcile the complete ctgov studies population.",
    )
    parser.add_argument(
        "--limit",
        type=_positive_int,
        default=DEFAULT_VERIFICATION_LIMIT,
        help=(
            "Verification trial count. Ignored only when --full-load is used; "
            f"default: {DEFAULT_VERIFICATION_LIMIT}."
        ),
    )
    parser.add_argument(
        "--batch-size",
        type=_positive_int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Source/write batch size, 1..{MAX_BATCH_SIZE}; default: {DEFAULT_BATCH_SIZE}.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="JSON reconciliation report path.",
    )
    parser.add_argument(
        "--execution-batch",
        type=_positive_int,
        default=13,
        help="Batch number recorded in the reconciliation report; default: 13.",
    )
    args = parser.parse_args()
    if args.batch_size > MAX_BATCH_SIZE:
        parser.error(f"--batch-size must not exceed {MAX_BATCH_SIZE}")
    return args


def main() -> int:
    args = _args()
    if args.output is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        args.output = f"data/profiles/batch13_canonical_load_{stamp}.json"

    try:
        def progress(item: dict) -> None:
            scope = "full" if item.get("limit") is None else str(item.get("limit"))
            print(
                "[LOAD] batch={batch_count} trials={trials_loaded}/{scope} through={last_nct_id}".format(
                    scope=scope, **item
                ),
                flush=True,
            )

        report = load_canonical_core_graph(
            limit=None if args.full_load else args.limit,
            batch_size=args.batch_size,
            output_path=args.output,
            progress_callback=progress,
            execution_batch=args.execution_batch,
        )
    except Exception as exc:
        print(f"Canonical graph load failed: {exc.__class__.__name__}: {exc}")
        return 1

    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report.get("passed"):
        print("Canonical graph reconciliation FAILED.")
        return 2

    print(f"Canonical graph reconciliation passed. Report: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
