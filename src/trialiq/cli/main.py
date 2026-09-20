"""TrialIQ command-line interface."""

import argparse
import json
import sys
from trialiq.etl.aact_extract import extract_aact_dataset
from trialiq.etl.neo4j_load import load_transformed_artifact
from trialiq.services.answer_service import answer_trial_overview_by_nct_id


def _positive_int(value: str) -> int:
    """Validate that a CLI integer argument is strictly positive."""
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc

    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")

    return parsed


def build_parser() -> argparse.ArgumentParser:
    """Build and configure the TrialIQ argument parser."""
    parser = argparse.ArgumentParser(description="TrialIQ CLI")

    parser.add_argument(
        "--limit",
        type=_positive_int,
        default=100,
        help="Number of trials to extract; must be greater than zero.",
    )
    parser.add_argument(
        "--output",
        default="data/extracted/aact_100_trials.json",
        help="Output path for the extracted artifact.",
    )

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--load",
        action="store_true",
        help="Load a transformed artifact into Neo4j.",
    )
    mode_group.add_argument(
        "--query-nct-id",
        help="Return a validated, evidence-grounded overview for an NCT ID.",
    )

    parser.add_argument(
        "--transformed-artifact",
        help="Path to the transformed artifact for Neo4j loading.",
    )

    return parser


def _print_error(message: str) -> None:
    """Print a concise user-facing error to stderr."""
    print(f"Error: {message}", file=sys.stderr)


def _run(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    """Execute the selected CLI operation."""
    if args.query_nct_id is not None:
        result = answer_trial_overview_by_nct_id(args.query_nct_id)
        print(result.model_dump_json(indent=2))
        return

    if args.load:
        if not args.transformed_artifact:
            parser.error(
                "--transformed-artifact is required when --load is used."
            )

        result = load_transformed_artifact(args.transformed_artifact)
        print(f"Neo4j loading completed: {result}")
        return

    if args.transformed_artifact:
        parser.error(
            "--transformed-artifact can only be used together with --load."
        )

    output_path = extract_aact_dataset(
        limit=args.limit,
        output_path=args.output,
    )
    print(f"Extraction completed: {output_path}")


def main() -> int:
    """Run the TrialIQ command-line interface and return an exit code."""
    parser = build_parser()
    args = parser.parse_args()

    try:
        _run(args, parser)
    except FileNotFoundError as exc:
        _print_error(str(exc))
        return 1
    except json.JSONDecodeError as exc:
        _print_error(
            f"Invalid JSON in artifact '{exc.doc[:40]}...': "
            f"line {exc.lineno}, column {exc.colno}."
        )
        return 1
    except (OSError, ValueError) as exc:
        _print_error(str(exc) or exc.__class__.__name__)
        return 1
    except Exception as exc:  # pragma: no cover - final CLI safety boundary
        _print_error(
            f"Operation failed: {exc.__class__.__name__}: {exc}"
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
