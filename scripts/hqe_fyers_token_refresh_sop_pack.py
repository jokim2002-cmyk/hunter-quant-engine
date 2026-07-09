from __future__ import annotations

from hqe_ops_181_190_common import module_main, build_module_payload

MODULE_NUMBER = 189
MODULE_NAME = 'Fyers Token Refresh SOP Pack'
BASENAME = 'MODULE_189_FYERS_TOKEN_REFRESH_SOP_STATUS'
TITLE = 'Module 189 Fyers Token Refresh SOP'


def build(args):
    return build_module_payload(MODULE_NUMBER, MODULE_NAME, BASENAME, TITLE, args)


def main():
    return module_main(MODULE_NUMBER, MODULE_NAME, BASENAME, TITLE)


if __name__ == "__main__":
    raise SystemExit(main())
