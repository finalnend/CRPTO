from __future__ import annotations

import os


def fix_ssl_env() -> None:
    """Normalize SSL certificate env vars inside frozen apps.

    - If SSL_CERT_FILE/SSL_CERT_DIR point to invalid paths, adjust or unset.
    - Prefer certifi bundle when available.
    """
    try:
        file = os.environ.get("SSL_CERT_FILE")
        dir_ = os.environ.get("SSL_CERT_DIR")
        if file and not os.path.exists(file):
            try:
                import certifi  # type: ignore
                os.environ["SSL_CERT_FILE"] = certifi.where()
            except Exception:
                os.environ.pop("SSL_CERT_FILE", None)
        if dir_ and not os.path.isdir(dir_):
            os.environ.pop("SSL_CERT_DIR", None)
    except Exception:
        # Non-fatal; networking libs will fallback to defaults
        pass

