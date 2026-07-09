from __future__ import annotations

from hqe_ops_181_190_common import module_main, build_module_payload

MODULE_NUMBER = 186
MODULE_NAME = 'Live Paper Session Controller'
BASENAME = 'MODULE_186_LIVE_PAPER_SESSION_CONTROLLER_STATUS'
TITLE = 'Module 186 Live Paper Session Controller'


def build(args):
    return build_module_payload(MODULE_NUMBER, MODULE_NAME, BASENAME, TITLE, args)


def main():
    return module_main(MODULE_NUMBER, MODULE_NAME, BASENAME, TITLE)


if __name__ == "__main__":
    raise SystemExit(main())
