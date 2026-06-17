"""Best-effort run lock to prevent overlapping invocations.

``RunLock`` creates ``<output_root>/.runner.lock`` (containing PID and start
timestamp) on acquire and removes it on release. If the file already exists,
acquisition refuses and reports the existing contents. Implemented as a context
manager so release happens even on exception. Single-machine, best-effort only
— not distributed locking (§5.6, §9).
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from types import TracebackType


LOCK_FILENAME = ".runner.lock"
"""Name of the lock file created under ``output_root``. See §5.6."""


class RunLock:
    """Acquire/release ``<output_root>/.runner.lock`` as a context manager. See §5.6.

    Parameters
    ----------
    output_root : Path
        The run's output root, under which the lock file lives.
    """

    def __init__(self, output_root: Path) -> None:
        """Bind the output root and derive the lock path.

        Parameters
        ----------
        output_root : Path
            The run's output root.
        """
        self._output_root = Path(output_root)

    @property
    def lock_path(self) -> Path:
        """Return the lock file path ``<output_root>/.runner.lock``.

        Returns
        -------
        Path
            Absolute-or-relative path to the lock file, under ``output_root``.
        """
        return self._output_root / LOCK_FILENAME

    def acquire(self) -> None:
        """Create the lock file with PID and timestamp, failing if it exists. See §5.6.

        The lock file is created atomically (``O_CREAT | O_EXCL``) so a
        concurrent invocation cannot slip in between the existence check and the
        write. ``output_root`` is created if it does not yet exist.

        Raises
        ------
        RuntimeError
            If the lock file already exists; the message reports its contents
            (the holding PID and start timestamp).
        """
        self._output_root.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            {"pid": os.getpid(), "started_at": datetime.now().isoformat()},
            indent=2,
        )
        try:
            fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            existing = self.lock_path.read_text()
            raise RuntimeError(
                f"run lock already held at {self.lock_path}; "
                f"another run appears to be in progress:\n{existing}"
            ) from None
        with os.fdopen(fd, "w") as handle:
            handle.write(payload)

    def release(self) -> None:
        """Remove the lock file if present. See §5.6.

        Idempotent: releasing an already-released (or never-acquired) lock is a
        no-op rather than an error, so it is safe to call from ``__exit__``.
        """
        self.lock_path.unlink(missing_ok=True)

    def __enter__(self) -> RunLock:
        self.acquire()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.release()
