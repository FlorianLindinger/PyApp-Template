"""Exceptions for problems the user can fix; they are shown as a short message without a traceback.

Standard library only, so scripts/entrypoint.py can import them before anything else loads.
"""


class SettingsError(Exception):
    """A developer_settings.py value cannot be used."""


class SetupError(RuntimeError):
    """The environment cannot be prepared; the message says what to do."""


class LaunchCancelled(Exception):
    """The user chose to cancel this launch."""
