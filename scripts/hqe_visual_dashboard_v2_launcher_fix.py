from __future__ import annotations

from hqe_ops_181_190_common import module_main, build_module_payload

MODULE_NUMBER = 182
MODULE_NAME = 'Visual Dashboard V2 Launcher Fix'
BASENAME = 'MODULE_182_VISUAL_DASHBOARD_V2_LAUNCHER_FIX_STATUS'
TITLE = 'Module 182 Dashboard V2 Launcher Fix'


def build(args):
    return build_module_payload(MODULE_NUMBER, MODULE_NAME, BASENAME, TITLE, args)


def main():
    return module_main(MODULE_NUMBER, MODULE_NAME, BASENAME, TITLE)


if __name__ == "__main__":
    raise SystemExit(main())
