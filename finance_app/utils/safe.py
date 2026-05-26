from __future__ import annotations

import functools
import logging
from collections.abc import Callable
from tkinter import messagebox


LOGGER = logging.getLogger(__name__)


def safe_call(default=None, alert: bool = False):
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001 - desktop apps must fail closed, not crash.
                LOGGER.exception("Recovered from %s", func.__name__)
                if alert:
                    try:
                        messagebox.showerror("TrackMint recovered", f"Action could not be completed safely:\n{exc}")
                    except Exception:
                        LOGGER.exception("Unable to show error dialog")
                return default

        return wrapper

    return decorator
