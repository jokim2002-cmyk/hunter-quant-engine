"""
Real dataset backtest input pack.

Module LLL starts the post-v1.0 Real Backtest Usage Sprint.

This module discovers saved/recorded market data files and writes an operator
input pack for the first real recorded-data paper backtest run.

It does not connect to brokers, request live market data, place real orders,
use real money, or prove profitability.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


SUPPORTED_EXTENSIONS = {".csv", ".json", ".jsonl", ".parquet"}


@dataclass(frozen=True)
class RealDatasetFile:
    path: str
    extension: str
    size_bytes: int


@dataclass(frozen=True)
class RealDatasetInputPackIssue:
    severity: str
    code: str
    count: int
    message: str


@dataclass(frozen=True)
class RealDatasetInputPackReport:
    generated_at_utc: str
    input_directories: list[str]
    output_directory: str
    status: str
    ready_for_future_first_real_backtest_run: bool
    supported_extensions: list[str]
    discovered_file_count: int
    total_size_bytes: int
    selected_dataset_path: str
    safety_notice: str
    suggested_commands: list[str]
    issues: list[RealDatasetInputPackIssue]
    files: list[RealDatasetFile]


def safety_notice() -> str:
    return (
        "Paper/simulation real dataset backtest input pack only. This pack "
        "discovers saved recorded-data files for a future paper backtest run. "
        "It does not connect to brokers, request live market data, place real "
        "orders, use real money, or prove profitability."
    )


def _issue(
    severity: str,
    code: str,
    count: int,
    message: str,
) -> RealDatasetInputPackIssue:
    return RealDatasetInputPackIssue(
        severity=severity,
        code=code,
        count=count,
        message=message,
    )


def _status(issues: Sequence[RealDatasetInputPackIssue]) -> str:
    if any(issue.severity == "fail" for issue in issues):
        return "fail"
    if any(issue.severity == "warn" for issue in issues):
        return "warn"
    return "pass"


def _discover_files(input_directories: Sequence[Path]) -> tuple[list[RealDatasetFile], list[RealDatasetInputPackIssue]]:
    files: list[RealDatasetFile] = []
    issues: list[RealDatasetInputPackIssue] = []

    missing_dirs: list[str] = []

    for directory in input_directories:
        if not directory.exists():
            missing_dirs.append(str(directory))
            continue

        if not directory.is_dir():
            issues.append(
                _issue(
                    "fail",
                    "input_path_not_directory",
                    1,
                    f"Input path is not a directory: {directory}",
                )
            )
            continue

        for path in sorted(directory.rglob("*")):
            if not path.is_file():
                continue

            extension = path.suffix.lower()
            if extension not in SUPPORTED_EXTENSIONS:
                continue

            try:
                size_bytes = path.stat().st_size
            except OSError:
                size_bytes = 0

            files.append(
                RealDatasetFile(
                    path=str(path),
                    extension=extension,
                    size_bytes=max(size_bytes, 0),
                )
            )

    if missing_dirs:
        issues.append(
            _issue(
                "warn",
                "input_directories_missing",
                len(missing_dirs),
                "Some input directories do not exist yet.",
            )
        )

    return files, issues


def _suggested_commands(selected_dataset_path: str) -> list[str]:
    dataset_hint = selected_dataset_path or "<put recorded files under data\\recorded>"

    return [
        ".\\hqe_recorded_data_inventory.bat",
        ".\\hqe_recorded_data_replay_dataset.bat",
        ".\\hqe_recorded_data_replay_quality_gate.bat",
        ".\\hqe_recorded_data_backtest_readiness_gate.bat",
        ".\\hqe_v1_testing_release_gate.bat",
        ".\\hqe_v1_testing_operator_handoff_pack.bat",
        f"Selected dataset reference: {dataset_hint}",
    ]


def build_real_dataset_input_pack_report(
    *,
    input_directories: Sequence[Path],
    output_dir: Path,
    min_files: int = 1,
    allow_empty: bool = False,
) -> RealDatasetInputPackReport:
    min_files = max(min_files, 0)

    files, issues = _discover_files(input_directories)
    discovered_file_count = len(files)
    total_size_bytes = sum(file.size_bytes for file in files)

    if discovered_file_count < min_files:
        severity = "warn" if allow_empty else "fail"
        issues.append(
            _issue(
                severity,
                "insufficient_recorded_dataset_files",
                min_files - discovered_file_count,
                (
                    "Recorded dataset file count below minimum. "
                    f"Required={min_files}, actual={discovered_file_count}."
                ),
            )
        )

    if discovered_file_count == 0:
        severity = "warn" if allow_empty else "fail"
        issues.append(
            _issue(
                severity,
                "no_supported_recorded_dataset_files",
                1,
                "No supported recorded dataset files were found.",
            )
        )

    status = _status(issues)
    selected_dataset_path = files[0].path if files else ""

    return RealDatasetInputPackReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        input_directories=[str(path) for path in input_directories],
        output_directory=str(output_dir),
        status=status,
        ready_for_future_first_real_backtest_run=status == "pass",
        supported_extensions=sorted(SUPPORTED_EXTENSIONS),
        discovered_file_count=discovered_file_count,
        total_size_bytes=total_size_bytes,
        selected_dataset_path=selected_dataset_path,
        safety_notice=safety_notice(),
        suggested_commands=_suggested_commands(selected_dataset_path),
        issues=issues,
        files=files,
    )


def write_real_dataset_input_pack_report(
    report: RealDatasetInputPackReport,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    pack_json = output_dir / "real_dataset_backtest_input_pack.json"
    pack_txt = output_dir / "real_dataset_backtest_input_pack.txt"
    commands_txt = output_dir / "real_dataset_backtest_commands.txt"
    manifest_json = output_dir / "manifest.json"

    data = asdict(report)
    data["issues"] = [asdict(issue) for issue in report.issues]
    data["files"] = [asdict(file) for file in report.files]

    pack_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")

    commands_txt.write_text(
        "\n".join(report.suggested_commands) + "\n",
        encoding="utf-8",
    )

    lines = [
        "HQE Real Dataset Backtest Input Pack",
        "",
        report.safety_notice,
        "",
        f"Status: {report.status}",
        f"Ready for future first real backtest run: {report.ready_for_future_first_real_backtest_run}",
        f"Discovered files: {report.discovered_file_count}",
        f"Total size bytes: {report.total_size_bytes}",
        f"Selected dataset path: {report.selected_dataset_path}",
        "",
        "Input directories:",
    ]

    for directory in report.input_directories:
        lines.append(f"- {directory}")

    lines.extend(["", "Suggested commands:"])
    for command in report.suggested_commands:
        lines.append(f"- {command}")

    lines.extend(
        [
            "",
            "Safety:",
            "- LONG = CE BUY paper plan only.",
            "- SHORT = PE BUY paper plan only.",
            "- NEUTRAL = no trade.",
            "- No option selling.",
            "- No broker orders.",
            "- No live market data.",
            "- No real money.",
            "- This report is not a profitability claim.",
            "",
            "Discovered dataset files:",
        ]
    )

    if not report.files:
        lines.append("- No supported recorded dataset files found.")
    else:
        for file in report.files:
            lines.append(f"- {file.path} ({file.extension}, {file.size_bytes} bytes)")

    lines.extend(["", "Issues:"])
    if not report.issues:
        lines.append("- PASS: Real dataset input pack is ready for future first real backtest run.")
    else:
        for issue in report.issues:
            lines.append(
                f"- {issue.severity.upper()} {issue.code}: {issue.message} Count={issue.count}"
            )

    lines.extend(
        [
            "",
            "Outputs:",
            f"- {pack_json}",
            f"- {pack_txt}",
            f"- {commands_txt}",
            f"- {manifest_json}",
        ]
    )
    pack_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "report_type": "real_dataset_backtest_input_pack",
        "generated_at_utc": report.generated_at_utc,
        "status": report.status,
        "ready_for_future_first_real_backtest_run": report.ready_for_future_first_real_backtest_run,
        "discovered_file_count": report.discovered_file_count,
        "total_size_bytes": report.total_size_bytes,
        "selected_dataset_path": report.selected_dataset_path,
        "safety_notice": report.safety_notice,
        "outputs": {
            "real_dataset_backtest_input_pack_json": str(pack_json),
            "real_dataset_backtest_input_pack_txt": str(pack_txt),
            "real_dataset_backtest_commands_txt": str(commands_txt),
            "manifest_json": str(manifest_json),
        },
    }
    manifest_json.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "real_dataset_backtest_input_pack_json": pack_json,
        "real_dataset_backtest_input_pack_txt": pack_txt,
        "real_dataset_backtest_commands_txt": commands_txt,
        "manifest_json": manifest_json,
    }


def build_and_write_real_dataset_input_pack_report(
    *,
    input_directories: Sequence[Path],
    output_dir: Path,
    min_files: int = 1,
    allow_empty: bool = False,
) -> tuple[RealDatasetInputPackReport, dict[str, Path]]:
    report = build_real_dataset_input_pack_report(
        input_directories=input_directories,
        output_dir=output_dir,
        min_files=min_files,
        allow_empty=allow_empty,
    )
    outputs = write_real_dataset_input_pack_report(report, output_dir)
    return report, outputs


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build real dataset backtest input pack."
    )
    parser.add_argument(
        "--input-dir",
        action="append",
        default=None,
        help="Recorded dataset directory. Can be passed multiple times.",
    )
    parser.add_argument(
        "--output-dir",
        default="reports/paper_trading/real_dataset_backtest_input_pack",
    )
    parser.add_argument("--min-files", type=int, default=1)
    parser.add_argument("--allow-empty", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    input_dirs = args.input_dir or ["data/recorded", "data/live_recording"]

    report, outputs = build_and_write_real_dataset_input_pack_report(
        input_directories=[Path(path) for path in input_dirs],
        output_dir=Path(args.output_dir),
        min_files=args.min_files,
        allow_empty=args.allow_empty,
    )

    print("HQE real dataset backtest input pack completed.")
    print(report.safety_notice)
    print(f"Status: {report.status}")
    print(f"Ready for future first real backtest run: {report.ready_for_future_first_real_backtest_run}")
    print(f"Discovered files: {report.discovered_file_count}")
    print(f"Input pack: {outputs['real_dataset_backtest_input_pack_txt']}")
    print("This is not a profitability claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
