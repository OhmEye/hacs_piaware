"""Minimal resource shim so Home Assistant's POSIX-only imports work on Windows.

See ``fcntl.py`` in this directory for usage.
"""

RLIMIT_CPU = 0
RLIMIT_FSIZE = 1
RLIMIT_DATA = 2
RLIMIT_STACK = 3
RLIMIT_CORE = 4
RLIMIT_NOFILE = 7
RLIMIT_AS = 9

RLIM_INFINITY = -1


def getrlimit(resource):  # noqa: ANN001, A002
    """Return a dummy soft/hard limit."""
    return (1024, 1024)


def setrlimit(resource, limits):  # noqa: ANN001, A002
    """No-op setrlimit."""
    return None
