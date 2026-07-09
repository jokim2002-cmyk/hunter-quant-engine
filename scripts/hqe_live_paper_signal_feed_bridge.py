from __future__ import annotations

from hqe_ops_181_190_common import module_main, build_module_payload

MODULE_NUMBER = 185
MODULE_NAME = 'Live Paper Signal Feed Bridge'
BASENAME = 'MODULE_185_LIVE_PAPER_SIGNAL_FEED_BRIDGE_STATUS'
TITLE = 'Module 185 Live Paper Signal Feed Bridge'


def build(args):
    return build_module_payload(MODULE_NUMBER, MODULE_NAME, BASENAME, TITLE, args)


def main():
    return module_main(MODULE_NUMBER, MODULE_NAME, BASENAME, TITLE)


if __name__ == "__main__":
    raise SystemExit(main())
