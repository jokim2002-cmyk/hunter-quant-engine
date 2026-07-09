from __future__ import annotations

from hqe_ops_181_190_common import module_main, build_module_payload

MODULE_NUMBER = 190
MODULE_NAME = 'Live Paper Operation Final Close Pack'
BASENAME = 'MODULE_190_LIVE_PAPER_OPERATION_FINAL_CLOSE_STATUS'
TITLE = 'Module 190 Live Paper Operation Final Close'


def build(args):
    return build_module_payload(MODULE_NUMBER, MODULE_NAME, BASENAME, TITLE, args)


def main():
    return module_main(MODULE_NUMBER, MODULE_NAME, BASENAME, TITLE)


if __name__ == "__main__":
    raise SystemExit(main())
