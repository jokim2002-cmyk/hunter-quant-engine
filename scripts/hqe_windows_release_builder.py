from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()

def build_command(
    python_exe: Path, launcher: Path, icon: Path, dist_dir: Path, work_dir: Path
) -> list[str]:
    return [
        str(python_exe), '-m', 'PyInstaller',
        '--noconfirm', '--clean', '--onefile', '--windowed',
        '--name', 'HunterQuantEngine',
        '--icon', str(icon),
        '--distpath', str(dist_dir),
        '--workpath', str(work_dir / 'work'),
        '--specpath', str(work_dir / 'spec'),
        str(launcher),
    ]

def build_release(repo: Path, workspace: Path) -> dict:
    python_exe = repo / '.venv' / 'Scripts' / 'python.exe'
    launcher = repo / 'scripts' / 'hqe_desktop_exe_launcher.py'
    icon = repo / 'assets' / 'HQE_PRODUCT_APP.ico'
    dist_dir = repo / 'dist'
    work_dir = workspace / 'HQE_PYINSTALLER_WORK'
    exe = dist_dir / 'HunterQuantEngine.exe'
    for required in (python_exe, launcher, icon):
        if not required.exists():
            raise FileNotFoundError(required)
    work_dir.mkdir(parents=True, exist_ok=True)
    dist_dir.mkdir(parents=True, exist_ok=True)
    if exe.exists():
        exe.unlink()
    command = build_command(python_exe, launcher, icon, dist_dir, work_dir)
    result = subprocess.run(command, cwd=repo)
    if result.returncode != 0:
        raise RuntimeError('PyInstaller build failed.')
    if not exe.is_file() or exe.stat().st_size < 1_000_000:
        raise RuntimeError('Built HQE EXE is missing or unexpectedly small.')
    guard = subprocess.run([str(exe), '--guard-check'], cwd=repo, timeout=90)
    if guard.returncode != 0:
        raise RuntimeError('Built HQE EXE guard check failed.')
    report = {
        'status': 'PASS',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'exe_path': str(exe),
        'exe_size_bytes': exe.stat().st_size,
        'exe_sha256': sha256(exe),
        'guard_returncode': guard.returncode,
        'real_order_invoked': False,
        'broker_execution_invoked': False,
        'auto_trading_invoked': False,
    }
    report_dir = workspace / 'HQE_RELEASE_QA'
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / 'HQE_WINDOWS_BUILD_LATEST.json'
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding='utf-8')
    report['report_path'] = str(report_path)
    return report

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Build HQE Windows desktop launcher EXE')
    parser.add_argument('--repo-root', default=str(repo_root()))
    parser.add_argument(
        '--workspace',
        default=r'D:\HQE_BACKTEST_RUNS\HQE_FORWARD_PAPER_VALIDATION_ACTIVE_20260708_204722',
    )
    parser.add_argument('--json', action='store_true')
    return parser

def main() -> int:
    args = build_parser().parse_args()
    report = build_release(Path(args.repo_root), Path(args.workspace))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print('HQE WINDOWS RELEASE BUILD: PASS')
        print(f"EXE: {report['exe_path']}")
        print(f"SHA256: {report['exe_sha256']}")
        print(f"Report: {report['report_path']}")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
