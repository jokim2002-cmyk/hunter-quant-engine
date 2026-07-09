from __future__ import annotations

from hqe_ops_181_190_common import module_main, build_module_payload

MODULE_NUMBER = 183
MODULE_NAME = 'Fyers Data-Only Health Monitor'
BASENAME = 'MODULE_183_FYERS_DATA_ONLY_HEALTH_MONITOR_STATUS'
TITLE = 'Module 183 Fyers Data-Only Health'


def build(args):
    return build_module_payload(MODULE_NUMBER, MODULE_NAME, BASENAME, TITLE, args)


def main():
    return module_main(MODULE_NUMBER, MODULE_NAME, BASENAME, TITLE)


if __name__ == "__main__":
    raise SystemExit(main())
