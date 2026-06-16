"""
Run-lock acquisition and release for <output_root>/.runner.lock. See §5.6.

Best-effort single-machine safeguard against overlapping invocations.
Lock file contains PID and start timestamp. Implemented as a context manager
so release happens even on exception.
"""
from __future__ import annotations

from pathlib import Path
from types import TracebackType


LOCK_FILENAME = ".runner.lock"


class RunLock:
    """
    Context manager that acquires a lock file on enter and releases it on exit. See §5.6.

    Raises RuntimeError on enter if the lock file already exists (reports existing contents).
    """

    def __init__(self, output_root: Path) -> None:
        raise NotImplementedError("RunLock.__init__ not yet implemented")

    @property
    def lock_path(self) -> Path:
        """Return <output_root>/.runner.lock."""
        raise NotImplementedError("RunLock.lock_path not yet implemented")

    def acquire(self) -> None:
        """Create the lock file with PID and timestamp. Raise if it already exists."""
        raise NotImplementedError("RunLock.acquire not yet implemented")

    def release(self) -> None:
        """Remove the lock file."""
        raise NotImplementedError("RunLock.release not yet implemented")

    def __enter__(self) -> "RunLock":
        self.acquire()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.release()
