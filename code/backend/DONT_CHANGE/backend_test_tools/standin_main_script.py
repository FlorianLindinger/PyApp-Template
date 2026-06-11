"""Trigger controlled failures for script_wrapper traceback testing.

Select the failure with PYAPP_TEMPLATE_TRACEBACK_TEST_MODE:
- valueerror
- syntaxerror
- keyboardinterrupt
- baseexception
- chained
"""

import os

from rich.traceback import install

install(show_locals=False)


def inner_failure():
    mode = os.environ.get("PYAPP_TEMPLATE_TRACEBACK_TEST_MODE", "valueerror").lower()

    if mode == "valueerror":
        raise ValueError("intentional ValueError from test_main_script.py")

    if mode == "syntaxerror":
        compile("def broken(:\n    pass\n", __file__, "exec")
        return

    if mode == "keyboardinterrupt":
        raise KeyboardInterrupt()

    if mode == "baseexception":
        raise BaseException("intentional BaseException from test_main_script.py")

    if mode == "chained":
        try:
            int("not-an-int")
        except ValueError as error:
            raise RuntimeError("intentional chained RuntimeError from test_main_script.py") from error

    raise ValueError("unknown traceback test mode: {}".format(mode))


def outer_failure():
    inner_failure()


outer_failure()
