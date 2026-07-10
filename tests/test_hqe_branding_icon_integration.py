from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_branding_icon_assets_exist_and_are_wired():
    branded = REPO / "assets" / "branding" / "hqe_app_icon" / "HQE.ico"
    runtime = REPO / "assets" / "HQE_PRODUCT_APP.ico"
    app = (REPO / "scripts" / "hqe_product_app_v2.py").read_text(encoding="utf-8-sig")
    installer = (REPO / "scripts" / "INSTALL_HQE_PRODUCT_APP_LOCAL.ps1").read_text(encoding="utf-8-sig")
    launcher = (REPO / "OPEN_HQE_APP_V2.cmd").read_text(encoding="utf-8-sig")

    assert branded.exists()
    assert branded.stat().st_size > 1000
    assert runtime.exists()
    assert runtime.read_bytes() == branded.read_bytes()
    assert 'assets" / "HQE_PRODUCT_APP.ico"' in app
    assert r"assets\branding\hqe_app_icon\HQE.ico" in installer
    assert "hqe_product_app_v2.py" in launcher
    assert "pytest-of-Admin" not in launcher
    assert "HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722" in launcher
