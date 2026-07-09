from __future__ import annotations

from hqe_ops_181_190_common import module_main, build_module_payload

MODULE_NUMBER = 184
MODULE_NAME = 'Live 5m Normalized Data Bridge'
BASENAME = 'MODULE_184_LIVE_5M_NORMALIZED_DATA_BRIDGE_STATUS'
TITLE = 'Module 184 Live 5m Normalized Data Bridge'


def build(args):
    return build_module_payload(MODULE_NUMBER, MODULE_NAME, BASENAME, TITLE, args)


def main():
    return module_main(MODULE_NUMBER, MODULE_NAME, BASENAME, TITLE)


if __name__ == "__main__":
    raise SystemExit(main())
