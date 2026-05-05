#!/usr/bin/env python3
"""
GAP-to-Execution-Plan Cross-Reference Verifier

Extracts every GAP item number from MISSING-FEATURES-GAP-ANALYSIS.md and verifies
that each one appears in EXECUTION-PLAN.md (or is listed in the Resolved section).

Exit codes:
  0 = All GAP items accounted for
  1 = Missing items detected

Usage:
  python3 .agent/scripts/gap_sync_verifier.py .
  python3 .agent/scripts/gap_sync_verifier.py . --update  # Mark resolved items in GAP analysis
"""

import re
import sys
import os
from pathlib import Path


def extract_gap_items(gap_file: str) -> dict[str, dict[str, str]]:
    """Extract all GAP item numbers and their feature names from the GAP analysis."""
    items: dict[str, dict[str, str]] = {}
    with open(gap_file, "r", encoding="utf-8") as f:
        for line in f:
            # Match table rows: | 50a | Feature Name | ...
            match = re.match(
                r"^\|\s*(\d+[a-z]?)\s*\|\s*(?:~~)?(.+?)(?:~~)?\s*\|", line
            )
            if match:
                gap_id = match.group(1).strip()
                feature = match.group(2).strip()
                # Check if it's marked as resolved (strikethrough)
                is_resolved_in_gap = "~~" in line
                entry: dict[str, str] = {
                    "feature": feature,
                    "resolved_in_gap": str(is_resolved_in_gap),
                }
                items[gap_id] = entry
    return items


def extract_execution_plan_refs(exec_file: str) -> dict[str, str]:
    """Extract all (#N) references from the execution plan."""
    refs: dict[str, str] = {}
    with open(exec_file, "r", encoding="utf-8") as f:
        for line in f:
            # Match all #N references inside parentheses: (#18), (#18, #53a), (#58, #113)
            paren_match = re.search(r"\(([^)]*#\d+[^)]*)\)", line)
            if paren_match:
                inner = paren_match.group(1)
                for m in re.finditer(r"#(\d+[a-z]?)", inner):
                    gap_id = m.group(1)
                    is_done = "[x]" in line.lower()
                    refs[gap_id] = "done" if is_done else "pending"

            # Also match cross-reference table rows with #N-#M ranges
            if line.strip().startswith("|"):
                # Check for "resolved" or "Resolved" indicators
                if "resolved" in line.lower():
                    for m in re.finditer(r"#(\d+[a-z]?)", line):
                        gap_id = m.group(1)
                        if gap_id not in refs:
                            refs[gap_id] = "resolved"
    return refs


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python3 gap_sync_verifier.py <project_root>")
        return 1

    root = Path(sys.argv[1]).resolve()
    gap_file = root / "docs" / "MISSING-FEATURES-GAP-ANALYSIS.md"
    exec_file = root / "docs" / "EXECUTION-PLAN.md"

    if not gap_file.exists():
        print(f"❌ GAP analysis not found: {gap_file}")
        return 1
    if not exec_file.exists():
        print(f"❌ Execution plan not found: {exec_file}")
        return 1

    # Extract data
    gap_items = extract_gap_items(str(gap_file))
    exec_refs = extract_execution_plan_refs(str(exec_file))

    print(f"📊 GAP Analysis: {len(gap_items)} items found")
    print(f"📋 Execution Plan: {len(exec_refs)} references found")
    print()

    # Cross-reference
    missing: list[tuple[str, str]] = []
    resolved_in_gap_not_exec: list[tuple[str, str]] = []
    accounted: list[tuple[str, str, str]] = []

    for gap_id, info in sorted(
        gap_items.items(), key=lambda x: _sort_key(x[0])
    ):
        feature = info["feature"]
        is_resolved_in_gap = info["resolved_in_gap"] == "True"

        if gap_id in exec_refs:
            status = exec_refs[gap_id]
            accounted.append((gap_id, feature, status))
        elif is_resolved_in_gap:
            # Resolved via strikethrough in GAP analysis (e.g., #33, #34)
            accounted.append((gap_id, feature, "resolved-in-gap"))
        else:
            missing.append((gap_id, feature))

    # Check for exec refs that don't map to any GAP item (orphans)
    orphan_refs: list[str] = []
    for ref_id in exec_refs:
        if ref_id not in gap_items:
            orphan_refs.append(ref_id)

    # Report
    print("=" * 70)
    print("CROSS-REFERENCE REPORT")
    print("=" * 70)

    if missing:
        print(f"\n❌ MISSING FROM EXECUTION PLAN ({len(missing)} items):")
        print("-" * 50)
        for gap_id, feature in missing:
            print(f"  #{gap_id}: {feature}")
    else:
        print("\n✅ All GAP items are accounted for in the Execution Plan.")

    if orphan_refs:
        print(f"\n⚠️  ORPHAN REFERENCES ({len(orphan_refs)} items):")
        print("  (Referenced in Execution Plan but not in GAP Analysis)")
        print("-" * 50)
        for ref_id in sorted(orphan_refs, key=_sort_key):
            print(f"  #{ref_id}")

    # Summary table
    done_count = sum(1 for _, _, s in accounted if s in ("done", "resolved-in-gap"))
    pending_count = sum(1 for _, _, s in accounted if s == "pending")
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")
    print(f"  Total GAP items:    {len(gap_items)}")
    print(f"  ✅ Accounted for:   {len(accounted)}")
    print(f"     - Done/Resolved: {done_count}")
    print(f"     - Pending:       {pending_count}")
    print(f"  ❌ Missing:         {len(missing)}")
    print(f"  ⚠️  Orphan refs:     {len(orphan_refs)}")
    print()

    if missing:
        print("❌ FAILED: Not all GAP items are in the Execution Plan.")
        return 1
    else:
        print("✅ PASSED: 100% coverage verified.")
        return 0


def _sort_key(gap_id: str) -> tuple[int, str]:
    """Sort gap IDs numerically, with sub-items (50a, 50b) after their parent."""
    match = re.match(r"(\d+)([a-z]?)", gap_id)
    if match:
        return (int(match.group(1)), match.group(2))
    return (999, gap_id)


if __name__ == "__main__":
    sys.exit(main())
