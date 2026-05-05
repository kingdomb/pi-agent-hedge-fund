#!/usr/bin/env python3
"""
Batch inject Board Conditions sections into spec files.

Reads APPROVE_WITH_CONDITIONS votes from Phase 3 checkpoints and
injects a '## Board Conditions' section into the corresponding
spec file (docs/requirements/{REQ-ID}.md).

Skips specs that already have a Conditions section.
Skips REQs without a spec file (already implemented and deleted).
"""

import json
import re
import sys
from pathlib import Path

def main():
    project_root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(".")
    checkpoint_dir = project_root / ".agent" / "checkpoints"
    specs_dir = project_root / "docs" / "requirements"

    injected = []
    skipped_has_section = []
    skipped_no_spec = []
    errors = []

    for req_dir in sorted(checkpoint_dir.iterdir()):
        phase3 = req_dir / "phase3_board_review.json"
        if not phase3.exists():
            continue

        data = json.loads(phase3.read_text())
        req_id = data.get("req_id", req_dir.name)
        votes = data.get("board_votes", {})

        # Collect all conditional votes for this REQ
        conditional = []
        for member, vote in votes.items():
            if vote.get("decision") == "APPROVE_WITH_CONDITIONS":
                conditional.append({
                    "member": member,
                    "notes": vote.get("notes", "No notes provided")
                })

        if not conditional:
            continue

        # Check spec file
        spec_path = specs_dir / f"{req_id}.md"
        if not spec_path.exists():
            skipped_no_spec.append(req_id)
            continue

        content = spec_path.read_text()

        # Skip if already has conditions section
        if re.search(r'^##\s+.*[Cc]onditions?', content, re.MULTILINE):
            skipped_has_section.append(req_id)
            continue

        # Build the conditions section
        section_lines = [
            "",
            "## Board Conditions (Phase 3 — APPROVE_WITH_CONDITIONS)",
            "",
            "> **These conditions were raised during the board review and MUST be verified during `/implement-req`.**",
            "",
        ]

        for i, cond in enumerate(conditional, 1):
            member_display = cond["member"].replace("board_", "").replace("_", " ").title()
            section_lines.append(f"### Condition Set {i}: {member_display}")
            section_lines.append(f"{cond['notes']}")
            section_lines.append("")

        section_text = "\n".join(section_lines)

        # Find insertion point: before ## Testability, or before ## Delivery Surfaces, or at end
        insertion_patterns = [
            r'^## Testability',
            r'^## Delivery Surface',
            r'^## Doc Update Manifest',
        ]

        inserted = False
        for pattern in insertion_patterns:
            match = re.search(pattern, content, re.MULTILINE)
            if match:
                insert_pos = match.start()
                new_content = content[:insert_pos] + section_text + "\n" + content[insert_pos:]
                spec_path.write_text(new_content)
                inserted = True
                break

        if not inserted:
            # Append to end
            if not content.endswith("\n"):
                content += "\n"
            spec_path.write_text(content + section_text + "\n")
            inserted = True

        injected.append(req_id)

    # Report
    print(f"\n{'='*60}")
    print(f"BOARD CONDITIONS INJECTION REPORT")
    print(f"{'='*60}\n")
    print(f"✅ Injected: {len(injected)}")
    for r in injected:
        print(f"   {r}")
    print(f"\n⏭️  Already has section: {len(skipped_has_section)}")
    for r in skipped_has_section:
        print(f"   {r}")
    print(f"\n📄 No spec file: {len(skipped_no_spec)}")
    for r in skipped_no_spec:
        print(f"   {r}")
    if errors:
        print(f"\n❌ Errors: {len(errors)}")
        for e in errors:
            print(f"   {e}")

    print(f"\n{'='*60}")
    return 0 if not errors else 1

if __name__ == "__main__":
    sys.exit(main())
