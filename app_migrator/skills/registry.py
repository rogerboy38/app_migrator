"""app_migrator skills registry — atomic-write + SHA256 (L169).

Implements the create_skill primitive for the v0.5 skills layer.

L169 doctrine: write-then-rename via os.replace() on a tmp file in the same
directory as the target. SHA256 of the file content is computed before the
swap so callers can detect change-detection drift.

Crash-mid-write safety:
  - tmp file is created in the same directory as target (same filesystem)
  - os.replace() is atomic on POSIX (and Windows since Python 3.3)
  - on any exception, the tmp file is removed; the target is never observed
    in a partial state
  - if the target already exists and the new content matches (same sha256),
    the swap is skipped (idempotent)

Public surface:
  - create_skill(target, content) -> sha256 str
  - compute_sha256(content: bytes) -> str
"""
from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from typing import Union

PathLike = Union[str, os.PathLike]


def compute_sha256(content: bytes) -> str:
    """SHA256 hex digest of content (per L169 doctrine)."""
    return hashlib.sha256(content).hexdigest()


def create_skill(target: PathLike, content: bytes) -> str:
    """Atomically write content to target. Returns the SHA256 of content.

    Crash-safe: on any exception, the tmp file is removed and target is
    never observed in a partial state. Idempotent: if target already has
    the same SHA256, no swap is performed.
    """
    target_path = Path(target)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    sha = compute_sha256(content)

    # Idempotency: target already has this content -> no work to do.
    if target_path.exists():
        existing = target_path.read_bytes()
        if compute_sha256(existing) == sha:
            return sha

    # Write to a tmp file in the SAME directory (same filesystem, atomic
    # rename possible). Use NamedTemporaryFile with delete=False so we
    # control the name and can rename reliably. Clean up on any error.
    fd, tmp_path = tempfile.mkstemp(
        prefix=f".{target_path.name}.",
        suffix=".tmp",
        dir=str(target_path.parent),
    )
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        # Atomic swap. os.replace() is atomic on POSIX and Windows
        # (Python 3.3+). On any exception during the swap, the tmp file
        # is removed and target is unchanged.
        os.replace(tmp_path, target_path)
    except BaseException:
        # On ANY error (including KeyboardInterrupt), remove the tmp file.
        # Use a broad catch deliberately: L169 says the target must never
        # be observed in a partial state.
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    return sha


__all__ = ["create_skill", "compute_sha256"]
