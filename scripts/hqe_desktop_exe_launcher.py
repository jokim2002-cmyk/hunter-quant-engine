from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

CREATE_NO_WINDOW = 0x08000000 if os.name == 'nt' else 0
DIAGNOSTIC_FLAGS = {'--guard-check', '--status', '--write-status'}

def candidate_roots() -> list[Path]:
    candidates: list[Path] = []
    env_hint = os.environ.get('HQE_REPO_HINT', '').strip()
    if env_hint:
        candidates.append(Path(env_hint))
    executable = Path(sys.executable).resolve()
    candidates.extend([executable.parent, *executable.parents])
    if not getattr(sys, 'frozen', False):
        source = Path(__file__).resolve()
        candidates.extend([source.parent, *source.parents])
    candidates.extend([Path.cwd(), Path(r'D:\Hunter_Quant_Engine_PC_TRANSFER')])
    unique: list[Path] = []
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved not in unique:
            unique.append(resolved)
    return unique

def resolve_repo_root() -> Path:
    for candidate in candidate_roots():
        app = candidate / 'scripts' / 'hqe_product_app_v2.py'
        pythonw = candidate / '.venv' / 'Scripts' / 'pythonw.exe'
        if app.is_file() and pythonw.is_file():
            return candidate
    raise FileNotFoundError(
        'HQE installation was not found. Reinstall the desktop shortcut or set HQE_REPO_HINT.'
    )

def launch(args: list[str]) -> int:
    repo = resolve_repo_root()
    app = repo / 'scripts' / 'hqe_product_app_v2.py'
    pythonw = repo / '.venv' / 'Scripts' / 'pythonw.exe'
    python = repo / '.venv' / 'Scripts' / 'python.exe'
    diagnostic = any(argument in DIAGNOSTIC_FLAGS for argument in args)
    executable = python if diagnostic else pythonw
    environment = os.environ.copy()
    environment['HQE_REPO_HINT'] = str(repo)
    command = [str(executable), str(app), *args]
    if diagnostic:
        return subprocess.run(
            command, cwd=repo, env=environment, creationflags=CREATE_NO_WINDOW
        ).returncode
    subprocess.Popen(
        command,
        cwd=repo,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=CREATE_NO_WINDOW,
    )
    return 0

def main() -> int:
    try:
        return launch(sys.argv[1:])
    except Exception as exc:
        if os.name == 'nt':
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(
                    None, str(exc), 'Hunter Quant Engine', 0x10
                )
            except Exception:
                pass
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
