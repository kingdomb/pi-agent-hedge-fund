#!/usr/bin/env python3
"""
UI Coverage Audit v2.0
======================
Scans all ✅ COMPLETE REQs in the ledger and cross-references against the live
frontend component tree to identify backend capabilities with no corresponding
UI surface.

Evaluates gaps through the 5-perspective delivery surface matrix:
  1. Tenant Self-Service
  2. Org 0 Self-Management
  3. Org 0 → Global Policy
  4. Org 0 → Per-Tenant Override
  5. SDK Exposure

Usage: python3 .agent/scripts/ui_coverage_audit.py .
"""

import sys
import re
from pathlib import Path
from dataclasses import dataclass, field


# ──────────────────────────────────────────────────────────────────
# Data Models
# ──────────────────────────────────────────────────────────────────

@dataclass
class CompletedREQ:
    req_id: str
    name: str
    description: str
    category: str = ""


@dataclass
class Perspective:
    name: str
    applicable: bool
    reason: str


@dataclass
class UIGap:
    req_id: str
    name: str
    backend_surface: str
    missing_ui: str
    perspectives: list[Perspective] = field(default_factory=list)
    priority: str = ""
    applicable_count: int = 0


# ──────────────────────────────────────────────────────────────────
# Classification Signal Dictionaries
#
# These drive the heuristic. Edit these lists to tune classification
# instead of modifying logic.
# ──────────────────────────────────────────────────────────────────

# REQs that ARE UI features — they already have a frontend surface
UI_SIGNALS = [
    "ui ", "ui/ux", "frontend", "widget", "dashboard shell", "theme",
    "layout", "grid", "animation", "card aesthetics", "brand color",
    "density", "dropdown", "micro-animation", "skeleton", "chart container",
    "canvas", "sidecar", "sidebar", "topbar", "gamification visual",
    "badge render", "xp counter", "streak", "leaderboard", "avatar",
    "accent picker", "tooltip", "genui", "gen-ui", "interview wizard",
    "template gallery", "draggable", "glass widget", "recovery warning",
    "login page", "profile dropdown",
]

# Pure infrastructure CONFIG — zero human interaction at runtime.
# ONLY items that are truly invisible plumbing belong here.
# Operational/actionable infra (DR, monitoring, env sensors) must NOT
# be listed here — they need Org 0 observability UI.
INFRA_SIGNALS = [
    "docker", "containeriz", "ci/cd", "wal encrypt",
    "vllm", "startup orchestrat", "container orchestration",
    "schema baselining", "node-pg-migrate", "hybrid profiling", "jsonb",
    "provider factory", "async broker", "bullmq",
    "database layer", "pg16", "pgvector", "development environment",
    "gtx 1660", "dual-connection", "secret management", ".env",
    "email provider infrastructure",
]

# Keywords to EXCLUDE from frontend matching (too generic)
STOP_WORDS = {
    "with", "from", "this", "that", "have", "been", "will", "when",
    "must", "should", "each", "into", "also", "more", "than", "only",
    "complete", "implement", "hardening", "constraint", "architecture",
    "based", "level", "service", "system", "detect", "implement",
    "feature", "support", "ensure", "require", "enable", "provide",
    "update", "create", "manage", "verify", "check", "build", "allow",
    "handle", "process", "trigger", "include", "define", "extend",
    "response", "request", "endpoint", "runtime", "logic", "data",
    "abstract", "pattern", "strategy", "protocol", "spec", "config",
    "add", "remove", "full", "new", "see", "use", "via", "per",
    "validation", "split", "plug", "play", "direct",
}

# ── Perspective signal words ──

TENANT_SIGNALS = [
    "tenant", "user", "agent", "task", "chat", "profile", "workspace",
    "self-service", "personal", "per-user", "own agent", "my agent",
    "marketplace", "template fork", "nudge",
]

ORG0_SELF_SIGNALS = [
    "admin", "org 0", "org-0", "superadmin", "god mode", "observability",
    "platform operator", "cross-tenant", "system-wide health",
    "incident management", "sentinel", "simulation",
    # Operational infra that needs admin monitoring/execution UI
    "disaster recovery", "vram", "gpu memory", "env sensor", "saturation",
    "migration", "queue", "worker", "heartbeat", "resource limit",
    "deploy", "chaos", "saboteur", "forensic", "audit",
    "integrity", "health check", "monitor",
]

GLOBAL_POLICY_SIGNALS = [
    "policy", "global", "default", "system-wide", "all tenant",
    "enforcement", "compliance", "regulatory", "mandate", "rule",
    "subscription tier", "disclosure", "turing", "censor",
    "risk-tiered", "fallback", "degradation",
]

PER_TENANT_SIGNALS = [
    "per-tenant", "override", "individual tenant", "specific tenant",
    "custom threshold", "feature flag", "exception", "sandbox",
    "tenant config", "force-activate", "tenant adjustment",
]

SDK_SIGNALS = [
    "sdk", "@pi-agent", "package hook", "embed", "webhook",
    "a2a", "mcp server", "external developer", "third-party",
    "price discovery", "negotiation protocol",
]


# ──────────────────────────────────────────────────────────────────
# Parsing
# ──────────────────────────────────────────────────────────────────

def parse_ledger(project_root: Path) -> list[CompletedREQ]:
    """Parse all ✅ COMPLETE REQs from REQ-LEDGER.md."""
    ledger = project_root / "docs" / "requirements" / "REQ-LEDGER.md"
    content = ledger.read_text()

    reqs = []
    for line in content.split("\n"):
        if "✅ COMPLETE" not in line:
            continue
        # Skip legend lines like "[✅ COMPLETE]: Features built in..."
        stripped = line.strip()
        if stripped.startswith("[") or stripped.startswith("-"):
            continue

        parts = [p.strip() for p in line.split("|") if p.strip()]
        if len(parts) < 3:
            continue

        req_id = re.sub(r'\*{1,2}', '', parts[0]).strip()
        name = re.sub(r'\*{1,2}', '', parts[1]).strip()
        name = re.sub(r'\[.*?\]', '', name).strip()
        desc = re.sub(r'\*{1,2}', '', parts[3]).strip() if len(parts) > 3 else ""

        if not req_id.startswith("REQ-"):
            continue

        reqs.append(CompletedREQ(req_id=req_id, name=name, description=desc))

    return reqs


# ──────────────────────────────────────────────────────────────────
# Codebase Indexing
# ──────────────────────────────────────────────────────────────────

def build_frontend_index(project_root: Path) -> dict[str, list[str]]:
    """Build a keyword → file-paths index of frontend components."""
    frontend_dir = project_root / "frontend" / "src"
    if not frontend_dir.exists():
        return {}

    index: dict[str, list[str]] = {}

    for f in frontend_dir.rglob("*.tsx"):
        if "__tests__" in str(f) or ".test." in f.name:
            continue

        rel = str(f.relative_to(frontend_dir))

        # Index by lowercase stem
        index.setdefault(f.stem.lower(), []).append(rel)

        # Split PascalCase/camelCase into words and index each
        words = re.findall(r'[A-Z][a-z]+|[a-z]+', f.stem)
        for word in words:
            w = word.lower()
            if len(w) > 3 and w not in STOP_WORDS:
                index.setdefault(w, []).append(rel)

        # Index by parent directory name
        parent = f.parent.name.lower()
        if parent not in ("src", "__tests__", "app"):
            index.setdefault(parent, []).append(rel)

    return index


def build_backend_index(project_root: Path) -> dict[str, list[str]]:
    """Build a keyword → file-paths index of backend surfaces."""
    index: dict[str, list[str]] = {}

    routes_dir = project_root / "backend" / "src" / "routes"
    core_dir = project_root / "backend" / "src" / "core"

    if routes_dir.exists():
        for f in routes_dir.glob("*.ts"):
            index.setdefault(f.stem.lower(), []).append(f"routes/{f.name}")

    if core_dir.exists():
        for d in core_dir.iterdir():
            if d.is_dir():
                index.setdefault(d.name.lower(), []).append(f"core/{d.name}/")
                for f in d.rglob("*.ts"):
                    if ".test." not in f.name:
                        words = re.findall(r'[A-Z][a-z]+|[a-z]+', f.stem)
                        for w in words:
                            wl = w.lower()
                            if len(wl) > 3 and wl not in STOP_WORDS:
                                index.setdefault(wl, []).append(
                                    f"core/{d.name}/{f.name}"
                                )

    return index


# ──────────────────────────────────────────────────────────────────
# Classification
# ──────────────────────────────────────────────────────────────────

def has_signal(text: str, signals: list[str]) -> bool:
    """Check if text contains any of the signal phrases."""
    text_lower = text.lower()
    return any(s in text_lower for s in signals)


def classify_req(req: CompletedREQ) -> str:
    """Classify a REQ to determine if it needs UI gap analysis.

    SAFETY NET: Before excluding ANY category, we check if the REQ
    has admin/operational signals that would need an Org 0 UI surface.
    If it does, it goes to 'needs-review' regardless of category.

    Returns:
        'already-ui'      — this REQ IS a UI feature
        'infra'           — pure config plumbing, no UI needed
        'sdk'             — SDK-only package (no admin surface)
        'one-off'         — debug/fix ticket
        'ops-cli'         — CLI ops tool (no web equivalent needed)
        'needs-review'    — check for UI gap
    """
    combined = f"{req.name} {req.description}"

    # 1. Is it already a UI feature? (safe to skip — it HAS frontend)
    if has_signal(combined, UI_SIGNALS):
        return "already-ui"

    # 2. SAFETY NET: Does this REQ have admin/operational signals?
    #    If yes, it MUST be reviewed regardless of infra/sdk/cli category.
    needs_admin_ui = (
        has_signal(combined, ORG0_SELF_SIGNALS)
        or has_signal(combined, GLOBAL_POLICY_SIGNALS)
        or has_signal(combined, TENANT_SIGNALS)
        or has_signal(combined, PER_TENANT_SIGNALS)
    )

    # 3. Type-based exclusions — ONLY if no admin UI is needed
    if req.req_id.startswith("REQ-SDK") and not needs_admin_ui:
        return "sdk"

    if req.req_id.startswith(("REQ-DEBUG", "REQ-FIX")) and not needs_admin_ui:
        return "one-off"

    if "cli" in combined.lower() and not needs_admin_ui:
        return "ops-cli"

    if has_signal(combined, INFRA_SIGNALS) and not needs_admin_ui:
        return "infra"

    return "needs-review"


# ──────────────────────────────────────────────────────────────────
# Frontend Coverage Detection
# ──────────────────────────────────────────────────────────────────

def extract_domain_keywords(req: CompletedREQ) -> set[str]:
    """Extract meaningful domain keywords from a REQ for matching."""
    combined = f"{req.name} {req.description}"
    raw = re.findall(r'[a-zA-Z]+', combined)
    keywords = {w.lower() for w in raw if len(w) > 3}
    keywords -= STOP_WORDS
    return keywords


# Minimum number of distinct keyword matches required to consider a REQ
# "covered" by frontend. A single generic word (e.g., "enforcement")
# matching an unrelated component is NOT evidence of coverage.
MIN_COVERAGE_CONFIDENCE = 2


def find_frontend_coverage(
    req: CompletedREQ,
    frontend_index: dict[str, list[str]],
) -> tuple[list[str], int]:
    """Find frontend components that appear to cover this REQ.

    Returns:
        (matched_files, match_count): files and how many distinct keywords
        matched. Caller should check match_count >= MIN_COVERAGE_CONFIDENCE
        before treating as covered.
    """
    keywords = extract_domain_keywords(req)
    matched_keywords: dict[str, list[str]] = {}

    for kw in keywords:
        if kw in frontend_index:
            matched_keywords[kw] = frontend_index[kw]

    all_files: set[str] = set()
    for files in matched_keywords.values():
        all_files.update(files)

    return sorted(all_files), len(matched_keywords)


def find_backend_surface(
    req: CompletedREQ,
    backend_index: dict[str, list[str]],
) -> list[str]:
    """Find backend services/routes related to this REQ."""
    keywords = extract_domain_keywords(req)
    matches: set[str] = set()

    for kw in keywords:
        if kw in backend_index:
            for path in backend_index[kw]:
                matches.add(path)

    return sorted(matches)


# ──────────────────────────────────────────────────────────────────
# 5-Perspective Evaluation
# ──────────────────────────────────────────────────────────────────

PERSPECTIVES = [
    ("Tenant Self-Service", TENANT_SIGNALS),
    ("Org 0 Self-Management", ORG0_SELF_SIGNALS),
    ("Org 0 → Global Policy", GLOBAL_POLICY_SIGNALS),
    ("Org 0 → Per-Tenant Override", PER_TENANT_SIGNALS),
    ("SDK Exposure", SDK_SIGNALS),
]


def evaluate_perspectives(req: CompletedREQ) -> list[Perspective]:
    """Evaluate all 5 delivery surface perspectives for a REQ."""
    combined = f"{req.name} {req.description}"
    results = []
    for name, signals in PERSPECTIVES:
        applicable = has_signal(combined, signals)
        results.append(Perspective(
            name=name,
            applicable=applicable,
            reason=f"Signal matched in '{req.name}'" if applicable else "No signals",
        ))
    return results


def determine_priority(applicable_count: int) -> str:
    """Priority based on how many of 5 perspectives need a UI surface."""
    if applicable_count >= 4:
        return "CRITICAL"
    if applicable_count >= 3:
        return "HIGH"
    if applicable_count >= 2:
        return "MEDIUM"
    if applicable_count >= 1:
        return "LOW"
    return "INFO"


# ──────────────────────────────────────────────────────────────────
# Report Rendering
# ──────────────────────────────────────────────────────────────────

PRIORITY_ICONS = {
    "CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡",
    "LOW": "🟢", "INFO": "⚪",
}
PRIORITY_ORDER = {
    "CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4,
}
CATEGORY_ICONS = {
    "already-ui": "🎨", "infra": "🏗️", "sdk": "📦",
    "one-off": "🔧", "ops-cli": "💻", "needs-review": "🔎",
}


def print_classification(categories: dict[str, list[CompletedREQ]]) -> None:
    for cat in sorted(categories):
        icon = CATEGORY_ICONS.get(cat, "❓")
        print(f"   {icon} {cat}: {len(categories[cat])} REQs")


def print_covered(covered: list[tuple[CompletedREQ, list[str]]]) -> None:
    if not covered:
        return
    print(f"\n{'=' * 70}")
    print(f"✅ COVERED: {len(covered)} backend REQs with frontend surfaces detected")
    print(f"{'=' * 70}")
    for req, matches in covered:
        display = ", ".join(matches[:3])
        extra = f" (+{len(matches) - 3} more)" if len(matches) > 3 else ""
        print(f"  {req.req_id}: {req.name}")
        print(f"    → Frontend: {display}{extra}")


# Map perspectives to the actual dashboard targets in the frontend
DASHBOARD_TARGETS = {
    "Tenant Self-Service": "Tenant Dashboard",
    "Org 0 Self-Management": "Org 0 Admin Dashboard",
    "Org 0 → Global Policy": "Org 0 Admin Dashboard",
    "Org 0 → Per-Tenant Override": "Org 0 Admin Dashboard",
    "SDK Exposure": "SDK Package (@pi-agent/*)",
}


def print_gaps(gaps: list[UIGap]) -> None:
    print(f"\n{'=' * 70}")
    print(f"🚨 UI GAPS: {len(gaps)} completed REQs with no detected frontend surface")
    print(f"{'=' * 70}")

    for prio in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
        prio_gaps = [g for g in gaps if g.priority == prio]
        if not prio_gaps:
            continue

        icon = PRIORITY_ICONS.get(prio, "❓")
        print(f"\n{icon} {prio} ({len(prio_gaps)} gaps)")
        print("-" * 60)

        for g in prio_gaps:
            print(f"\n  {g.req_id}: {g.name}")
            if g.backend_surface:
                print(f"  Backend:  {g.backend_surface}")

            # Map applicable perspectives to actionable dashboard targets
            targets: set[str] = set()
            for p in g.perspectives:
                if p.applicable and p.name in DASHBOARD_TARGETS:
                    targets.add(DASHBOARD_TARGETS[p.name])
            if targets:
                print(f"  🎯 Target: {' & '.join(sorted(targets))}")

            print(f"  Perspectives ({g.applicable_count}/5):")
            for p in g.perspectives:
                if p.applicable:
                    print(f"    ✅ {p.name}")
                else:
                    print(f"    —  {p.name}")


def print_summary(
    reqs: list[CompletedREQ],
    categories: dict[str, list[CompletedREQ]],
    review_reqs: list[CompletedREQ],
    covered: list[tuple[CompletedREQ, list[str]]],
    gaps: list[UIGap],
) -> None:
    excluded = sum(len(v) for k, v in categories.items() if k != "needs-review")
    counts: dict[str, int] = {}
    for g in gaps:
        counts[g.priority] = counts.get(g.priority, 0) + 1

    print(f"\n{'=' * 70}")
    print("📊 SUMMARY")
    print(f"{'=' * 70}")
    print(f"  Total ✅ COMPLETE REQs:   {len(reqs)}")
    print(f"  Excluded (no UI needed):  {excluded}")
    print(f"  Reviewed for UI gaps:     {len(review_reqs)}")
    print(f"  ├─ Covered (UI found):    {len(covered)}")
    print(f"  └─ Gaps (no UI found):    {len(gaps)}")

    if counts:
        print(f"\n  Gap breakdown:")
        for prio in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
            if prio in counts:
                icon = PRIORITY_ICONS[prio]
                print(f"    {icon} {prio}: {counts[prio]}")

    print(f"\n  📐 5-Perspective Delivery Surface Model:")
    print(f"    1. Tenant Self-Service")
    print(f"    2. Org 0 Self-Management")
    print(f"    3. Org 0 → Global Policy")
    print(f"    4. Org 0 → Per-Tenant Override")
    print(f"    5. SDK Exposure")
    print(f"\n  💡 Create sub-REQs for CRITICAL/HIGH gaps first.")
    print(f"     Batch related gaps into composite dashboard REQs.")
    print()


# ──────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────

def run_audit(project_root: Path) -> None:
    print("\n" + "=" * 70)
    print("🔍 UI COVERAGE AUDIT v2.0 — Completed REQs vs Frontend Surfaces")
    print("=" * 70)

    # Parse inputs
    reqs = parse_ledger(project_root)
    frontend_index = build_frontend_index(project_root)
    backend_index = build_backend_index(project_root)

    print(f"\n📊 Codebase Stats:")
    print(f"   ✅ Complete REQs in ledger: {len(reqs)}")
    print(f"   🖥️  Frontend keywords indexed: {len(frontend_index)}")
    print(f"   ⚙️  Backend keywords indexed:  {len(backend_index)}")

    # Phase 1: Classify
    categories: dict[str, list[CompletedREQ]] = {}
    for req in reqs:
        cat = classify_req(req)
        req.category = cat
        categories.setdefault(cat, []).append(req)

    print(f"\n📋 Classification:")
    print_classification(categories)

    # Phase 2: Cross-reference needs-review REQs against frontend tree
    review_reqs = categories.get("needs-review", [])
    gaps: list[UIGap] = []
    covered: list[tuple[CompletedREQ, list[str]]] = []

    for req in review_reqs:
        frontend_matches, match_count = find_frontend_coverage(req, frontend_index)
        backend_matches = find_backend_surface(req, backend_index)

        if frontend_matches and match_count >= MIN_COVERAGE_CONFIDENCE:
            covered.append((req, frontend_matches))
        else:
            perspectives = evaluate_perspectives(req)
            applicable_count = sum(1 for p in perspectives if p.applicable)
            priority = determine_priority(applicable_count)

            gaps.append(UIGap(
                req_id=req.req_id,
                name=req.name,
                backend_surface=", ".join(backend_matches[:5]) or "—",
                missing_ui=f"No frontend component matches '{req.name}'",
                perspectives=perspectives,
                priority=priority,
                applicable_count=applicable_count,
            ))

    gaps.sort(key=lambda g: PRIORITY_ORDER.get(g.priority, 5))

    # Phase 3: Report
    print_covered(covered)
    print_gaps(gaps)
    print_summary(reqs, categories, review_reqs, covered, gaps)


if __name__ == "__main__":
    project_root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    run_audit(project_root)
