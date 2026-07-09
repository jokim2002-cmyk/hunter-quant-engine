from __future__ import annotations

from hqe_ops_181_190_common import module_main, build_module_payload

MODULE_NUMBER = 187
MODULE_NAME = 'Visual Dashboard V3 Operator App'
BASENAME = 'MODULE_187_VISUAL_DASHBOARD_V3_STATUS'
TITLE = 'Module 187 Visual Dashboard V3'


def build(args):
    return build_module_payload(MODULE_NUMBER, MODULE_NAME, BASENAME, TITLE, args)


def main():
    return module_main(MODULE_NUMBER, MODULE_NAME, BASENAME, TITLE)


if __name__ == "__main__":
    raise SystemExit(main())
