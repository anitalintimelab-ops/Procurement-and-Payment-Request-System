"""Process-wide request I/O coordination, retained across Streamlit reruns."""
import hashlib
import threading


# A lock created in a page script is recreated on every rerun/session. Keep one
# shared, reentrant lock here because saves call the synchronizer under the lock.
DATABASE_IO_LOCK = threading.RLock()


def database_fingerprint(filepath):
    """Identify the actual local snapshot, not just whether this user logged in."""
    digest = hashlib.sha256()
    try:
        with open(filepath, "rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except FileNotFoundError:
        return None
    return digest.hexdigest()
