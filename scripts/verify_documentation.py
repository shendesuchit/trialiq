"""Verify the maintained TrialIQ documentation package.

This checker is intentionally local/offline. It validates file presence, internal
Markdown links, diagram source sanity, draw.io XML, and the current README/docs
checkpoint wording. It does not validate external URLs or runtime behavior.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    ROOT / "README.md",
    ROOT / "TRIALIQ_STABILIZATION_HANDOFF.md",
    ROOT / "docs/00-index.md",
    ROOT / "docs/01-product-overview.md",
    ROOT / "docs/02-why-agentic-ai.md",
    ROOT / "docs/03-system-architecture.md",
    ROOT / "docs/04-agent-workflow.md",
    ROOT / "docs/05-investigator-ui.md",
    ROOT / "docs/06-data-lineage-and-graph-model.md",
    ROOT / "docs/07-api-and-mcp-contract.md",
    ROOT / "docs/08-setup-and-local-development.md",
    ROOT / "docs/09-rebuild-and-recovery.md",
    ROOT / "docs/10-verification-and-release-gate.md",
    ROOT / "docs/11-stable-demo-scenarios.md",
    ROOT / "docs/12-troubleshooting.md",
    ROOT / "docs/13-repository-hygiene-and-maintenance.md",
    ROOT / "docs/14-architecture-decisions-and-guardrails.md",
    ROOT / "docs/15-release-status-and-known-limitations.md",
    ROOT / "docs/16-reproducibility-checklist.md",
    ROOT / "docs/NOTION_IMPORT_GUIDE.md",
    ROOT / "docs/diagrams/README.md",
    ROOT / "docs/diagrams/trialiq-system-architecture.drawio",
]

DIAGRAMS = [
    ROOT / f"docs/diagrams/{name}.mmd"
    for name in (
        "01-system-architecture",
        "02-direct-vs-guided-routing",
        "03-agent-sequence",
        "04-hitl-workflow",
        "05-data-lineage",
        "06-graph-domain-model",
        "07-investigator-ui-flow",
        "08-runtime-readiness",
        "09-release-verification-flow",
        "10-use-case-map",
        "11-component-boundaries",
    )
]

NOTION_PAGES = sorted((ROOT / "docs/notion").glob("*.md"))

LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _markdown_files() -> list[Path]:
    return [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md"))]


def _check_links(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    for raw in LINK_RE.findall(text):
        target = raw.split("#", 1)[0].strip()
        if not target or target.startswith(("http://", "https://", "mailto:")):
            continue
        if target.startswith("<") and target.endswith(">"):
            target = target[1:-1]
        resolved = (path.parent / target).resolve()
        if not resolved.exists():
            errors.append(f"{path.relative_to(ROOT)} -> missing {target}")
    return errors


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    for path in [*REQUIRED, *DIAGRAMS]:
        if not path.exists():
            errors.append(f"missing required documentation file: {path.relative_to(ROOT)}")

    if len(NOTION_PAGES) < 13:
        errors.append(f"expected at least 13 Notion pages, found {len(NOTION_PAGES)}")

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    if "Batch 18 result-frame" in readme:
        errors.append("README still contains the obsolete Batch 18 checkpoint wording")
    if "Batch 21" not in readme or "Stable Demo" not in readme:
        errors.append("README does not identify the current stable-demo checkpoint")

    for diagram in DIAGRAMS:
        if not diagram.exists():
            continue
        text = diagram.read_text(encoding="utf-8")
        if not any(
            token in text
            for token in (
                "TrialIQ",
                "Investigator",
                "AACT",
                "Neo4j",
                "SupervisorAgent",
                "MCP",
                "HITL",
            )
        ):
            errors.append(
                f"diagram is not recognizably TrialIQ-specific: {diagram.relative_to(ROOT)}"
            )

    try:
        ET.parse(ROOT / "docs/diagrams/trialiq-system-architecture.drawio")
    except Exception as exc:  # pragma: no cover - command-line safety
        errors.append(f"draw.io XML is invalid: {exc}")

    for md in _markdown_files():
        errors.extend(_check_links(md))

    # Surface the known reproducibility risk without modifying runtime dependencies.
    package_json = ROOT / "frontend/package.json"
    package_lock = ROOT / "frontend/package-lock.json"
    if package_json.exists() and package_lock.exists():
        package = json.loads(package_json.read_text(encoding="utf-8"))
        lock = json.loads(package_lock.read_text(encoding="utf-8"))
        lock_root = lock.get("packages", {}).get("", {})
        if (
            package.get("dependencies") != lock_root.get("dependencies")
            or package.get("devDependencies") != lock_root.get("devDependencies")
        ):
            warnings.append(
                "frontend/package.json and frontend/package-lock.json root dependencies differ; "
                "resolve before the final reproducibility tag"
            )

    if warnings:
        for warning in warnings:
            print(f"[WARN] {warning}")

    if errors:
        for error in errors:
            print(f"[FAIL] {error}")
        print(f"[FAIL] TrialIQ documentation verification found {len(errors)} issue(s).")
        return 1

    print(f"[PASS] Required TrialIQ documentation files: {len(REQUIRED) + len(DIAGRAMS)}")
    print(f"[PASS] Notion-ready pages: {len(NOTION_PAGES)}")
    print("[PASS] Internal Markdown links resolve.")
    print("[PASS] TrialIQ Mermaid diagram sources and draw.io XML are valid at the structural level.")
    print("[SUCCESS] TrialIQ documentation package verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
