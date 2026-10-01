"""Minimal fcntl shim so Home Assistant's POSIX-only test harness imports on Windows.

Enable by adding this directory to PYTHONPATH when running pytest on Windows:

    $env:PYTHONPATH = "<repo>\\tools\\win_test_shims"

The HA test harness is POSIX-only (it imports ``fcntl``/``resource``); this only
allows the suite to start on Windows for local development. CI runs on Linux.
"""

LOCK_SH = 1
LOCK_EX = 2
LOCK_NB = 4
LOCK_UN = 8

F_GETFL = 3
F_SETFL = 4
F_GETFD = 1
F_SETFD = 2
FD_CLOEXEC = 1


def flock(fd, operation):  # noqa: ANN001
    """No-op flock."""
    return None


def lockf(fd, cmd, len=0, start=0, whence=0):  # noqa: ANN001, A002
    """No-op lockf."""
    return None


def fcntl(fd, cmd, arg=0):  # noqa: ANN001
    """No-op fcntl."""
    return 0


def ioctl(fd, request, arg=0, mutate_flag=True):  # noqa: ANN001
    """No-op ioctl."""
    return 0
