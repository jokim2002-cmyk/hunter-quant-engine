from __future__ import annotations

from hqe_ops_181_190_common import module_main, build_module_payload

MODULE_NUMBER = 188
MODULE_NAME = 'Paper Live Daily Close Plan'
BASENAME = 'MODULE_188_PAPER_LIVE_DAILY_CLOSE_PLAN_STATUS'
TITLE = 'Module 188 Paper Live Daily Close Plan'


def build(args):
    return build_module_payload(MODULE_NUMBER, MODULE_NAME, BASENAME, TITLE, args)


def main():
    return module_main(MODULE_NUMBER, MODULE_NAME, BASENAME, TITLE)


if __name__ == "__main__":
    raise SystemExit(main())
