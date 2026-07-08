from pathlib import Path

from src.project_hygiene.hqe_project_artifact_organization_pack import (
    build_and_write_artifact_organization_pack,
    build_artifact_organization_report,
)


def test_build_report_accepts_organized_runner_inventory(tmp_path: Path) -> None:
    script_dir = tmp_path / "scripts" / "paper_trading"
    script_dir.mkdir(parents=True)
    (script_dir / "hqe_demo_runner.bat").write_text("@echo off\n", encoding="utf-8")

    report = build_artifact_organization_report(
        repo_root=tmp_path,
        script_dir=Path("scripts/paper_trading"),
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.root_runner_count == 0
    assert report.organized_runner_count == 1
    assert report.root_runner_clutter_cleared is True
    assert report.accepted_for_phase9_continuation is True
    assert report.backtest_executed is False
    assert report.optimization_executed is False
    assert report.strategy_logic_changed is False
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False


def test_build_report_flags_root_runner_clutter_but_stays_safe(tmp_path: Path) -> None:
    (tmp_path / "hqe_root_runner.bat").write_text("@echo off\n", encoding="utf-8")

    report = build_artifact_organization_report(
        repo_root=tmp_path,
        script_dir=Path("scripts/paper_trading"),
        output_dir=tmp_path / "out",
    )

    assert report.status == "pass"
    assert report.root_runner_count == 1
    assert report.organized_runner_count == 0
    assert report.root_runner_clutter_cleared is False
    assert report.accepted_for_phase9_continuation is False
    assert report.ready_for_live_or_real_money is False
    assert report.profitability_claim_allowed is False
    assert {issue["code"] for issue in report.issues} >= {
        "root_runner_clutter_remaining",
        "organized_runner_inventory_empty",
    }


def test_write_pack_outputs_manifest_and_inventory(tmp_path: Path) -> None:
    script_dir = tmp_path / "scripts" / "paper_trading"
    script_dir.mkdir(parents=True)
    (script_dir / "hqe_demo_runner.bat").write_text("@echo off\n", encoding="utf-8")

    report, outputs = build_and_write_artifact_organization_pack(
        repo_root=tmp_path,
        script_dir=Path("scripts/paper_trading"),
        output_dir=tmp_path / "pack",
    )

    assert report.status == "pass"
    for key in ["report_json", "report_txt", "inventory_csv", "manifest_json"]:
        assert Path(outputs[key]).exists()
