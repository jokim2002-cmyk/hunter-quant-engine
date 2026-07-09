from __future__ import annotations

from hqe_ops_181_190_common import module_main, build_module_payload

MODULE_NUMBER = 181
MODULE_NAME = 'Fyers Token Refresh Helper Permanent Dashboard Integration'
BASENAME = 'MODULE_181_FYERS_TOKEN_REFRESH_HELPER_STATUS'
TITLE = 'Module 181 Fyers Token Refresh Helper'


def build(args):
    return build_module_payload(MODULE_NUMBER, MODULE_NAME, BASENAME, TITLE, args)


def main():
    return module_main(MODULE_NUMBER, MODULE_NAME, BASENAME, TITLE)


if __name__ == "__main__":
    raise SystemExit(main())
