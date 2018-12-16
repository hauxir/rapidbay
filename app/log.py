import traceback

import settings


def debug(msg):
    with open(settings.LOGFILE, "a+") as f:
        f.write(msg + "\n")


def write_log():
    with open(settings.LOGFILE, "a+") as f:
        f.write(traceback.format_exc() + "\n")


def catch_and_log_exceptions(fn):
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception:
            write_log()

    return wrapper
