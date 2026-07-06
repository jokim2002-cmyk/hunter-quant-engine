"""
Paper MVP Release Gate

Checks whether the local Paper MVP v0.1 release checklist is ready.

This module does not create a release tag.
This module does not place orders.
This module does not use broker APIs.
This module does not use live market data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_RELEASE_FILES = (
    "README.md",
    "ROADMAP.md",
    "README_SHORTCUTS.md",
    "docs/PAPER_MVP_V0_1_SCOPE.md",
    "docs/PAPER_MVP_RELEASE_CHECKLIST.md",
    "docs/DEFERRED_POLISH_BACKLOG.md",
    "docs/PAPER_OPERATOR_GUIDE.md",
    "hqe_quick_check.bat",
    "hqe_paper_mvp_operator_demo.bat",
    "hqe_paper_replay_journal_all.bat",
    "src/paper_trading/strategy_to_paper_bridge.py",
    "src/paper_trading/paper_backtest_evidence_runner.py",
    "src/paper_trading/paper_mvp_operator_demo_cli.py",
)

REQUIRED_RELEASE_TEXT = {
    "docs/PAPER_MVP_V0_1_SCOPE.md": (
        "Paper MVP v0.1 is a paper-only release target.",
        "It does not place broker orders.",
        "It does not use real money.",
        "It does not claim profitability.",
        "Live trading starts only after Paper MVP v0.1 and evidence gates are complete.",
    ),
    "docs/PAPER_MVP_RELEASE_CHECKLIST.md": (
        "No broker order placement in paper workflow.",
        "Paper PnL labelled as simulation only.",
        "Do not create the release tag until all checklist items above are complete.",
    ),
    "docs/PAPER_OPERATOR_GUIDE.md": (
        ".\\hqe_paper_mvp_operator_demo.bat",
        ".\\hqe_paper_replay_journal_all.bat",
        "Passing evidence gates is not a profitability claim.",
    ),
    "ROADMAP.md": (
        "Paper MVP v0.1 scope is frozen.",
        "Paper MVP operator workflow completed.",
    ),
}

PAPER_RELEASE_SOURCE_FILES = (
    "src/paper_trading/strategy_to_paper_bridge.py",
    "src/paper_trading/paper_backtest_evidence_runner.py",
    "src/paper_trading/paper_mvp_operator_demo_cli.py",
    "src/paper_trading/paper_trading_replay_journal.py",
    "src/paper_trading/paper_trading_journal_store.py",
)

FORBIDDEN_RELEASE_SOURCE_TOKENS = (
    "import " + "fy" + "ers",
    "from " + "fy" + "ers",
    "place" + "_order",
    "send" + "_order",
    "execute" + "_order",
)


@dataclass(frozen=True)
class PaperMvpReleaseGateCheck:
    """
    Single release gate check result.
    """

    name: str
    passed: bool
    message: str


@dataclass(frozen=True)
class PaperMvpReleaseGateReport:
    """
    Full Paper MVP release gate report.
    """

    generated_at: str
    gate_version: int
    release_name: str
    paper_only: bool
    no_broker_orders: bool
    no_live_market_data: bool
    no_real_orders: bool
    not_a_profitability_claim: bool
    checks: tuple[PaperMvpReleaseGateCheck, ...]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    @property
    def blocking_reasons(self) -> tuple[str, ...]:
        return tuple(check.message for check in self.checks if not check.passed)


def run_paper_mvp_release_gate(
    project_root: str | Path = ".",
    *,
    generated_at: datetime | None = None,
) -> PaperMvpReleaseGateReport:
    """
    Run local Paper MVP release readiness checks.
    """
    root = Path(project_root)
    generated = generated_at or datetime.now(timezone.utc)

    checks: list[PaperMvpReleaseGateCheck] = []
    checks.extend(_check_required_files(root))
    checks.extend(_check_required_text(root))
    checks.extend(_check_release_sources_are_paper_only(root))

    return PaperMvpReleaseGateReport(
        generated_at=generated.isoformat(),
        gate_version=1,
        release_name="v0.1-paper-mvp",
        paper_only=True,
        no_broker_orders=True,
        no_live_market_data=True,
        no_real_orders=True,
        not_a_profitability_claim=True,
        checks=tuple(checks),
    )


def format_paper_mvp_release_gate_report(
    report: PaperMvpReleaseGateReport,
) -> str:
    """
    Format release gate results for terminal output.
    """
    lines = [
        "Hunter Quant Engine - Paper MVP Release Gate",
        "paper-only release readiness check",
        "no broker",
        "no live market data",
        "no real orders",
        "not a profitability claim",
        "",
        f"release name: {report.release_name}",
        f"generated at: {report.generated_at}",
        f"passed gates: {report.passed}",
        "",
        "Checks",
    ]

    for check in report.checks:
        status = "PASS" if check.passed else "FAIL"
        lines.append(f"- {status}: {check.name} - {check.message}")

    if report.blocking_reasons:
        lines.append("")
        lines.append("Blocking Reasons")
        lines.extend(f"- {reason}" for reason in report.blocking_reasons)

    return "\n".join(lines) + "\n"


def main() -> int:
    """
    CLI entrypoint.
    """
    report = run_paper_mvp_release_gate()
    print(format_paper_mvp_release_gate_report(report), end="")
    return 0 if report.passed else 1


def _check_required_files(root: Path) -> tuple[PaperMvpReleaseGateCheck, ...]:
    checks: list[PaperMvpReleaseGateCheck] = []

    for relative_path in REQUIRED_RELEASE_FILES:
        path = root / relative_path
        exists = path.exists()
        checks.append(
            PaperMvpReleaseGateCheck(
                name=f"required file: {relative_path}",
                passed=exists,
                message="exists" if exists else f"missing: {relative_path}",
            )
        )

    return tuple(checks)


def _check_required_text(root: Path) -> tuple[PaperMvpReleaseGateCheck, ...]:
    checks: list[PaperMvpReleaseGateCheck] = []

    for relative_path, required_items in REQUIRED_RELEASE_TEXT.items():
        path = root / relative_path
        if not path.exists():
            checks.append(
                PaperMvpReleaseGateCheck(
                    name=f"required text: {relative_path}",
                    passed=False,
                    message=f"cannot inspect missing file: {relative_path}",
                )
            )
            continue

        text = path.read_text(encoding="utf-8")
        missing_items = [item for item in required_items if item not in text]
        checks.append(
            PaperMvpReleaseGateCheck(
                name=f"required text: {relative_path}",
                passed=not missing_items,
                message=(
                    "required text present"
                    if not missing_items
                    else "missing text: " + ", ".join(missing_items)
                ),
            )
        )

    return tuple(checks)


def _check_release_sources_are_paper_only(
    root: Path,
) -> tuple[PaperMvpReleaseGateCheck, ...]:
    checks: list[PaperMvpReleaseGateCheck] = []

    for relative_path in PAPER_RELEASE_SOURCE_FILES:
        path = root / relative_path
        if not path.exists():
            checks.append(
                PaperMvpReleaseGateCheck(
                    name=f"paper-only source: {relative_path}",
                    passed=False,
                    message=f"cannot inspect missing file: {relative_path}",
                )
            )
            continue

        source = path.read_text(encoding="utf-8").lower()
        found = [token for token in FORBIDDEN_RELEASE_SOURCE_TOKENS if token in source]
        checks.append(
            PaperMvpReleaseGateCheck(
                name=f"paper-only source: {relative_path}",
                passed=not found,
                message=(
                    "no broker execution tokens found"
                    if not found
                    else "forbidden broker execution tokens found"
                ),
            )
        )

    return tuple(checks)


if __name__ == "__main__":
    raise SystemExit(main())
