import os
import sys
import ctypes
from pathlib import Path


def _prepend_path(path: str) -> None:
    if not path:
        return
    try:
        os.add_dll_directory(path)
    except Exception:
        pass
    os.environ["PATH"] = path + os.pathsep + os.environ.get("PATH", "")


def _init() -> None:
    exe_dir = Path(sys.executable).resolve().parent
    internal_dir = exe_dir / "_internal"

    if internal_dir.is_dir():
        _prepend_path(str(internal_dir))
        os.environ.setdefault("QT_OPENSSL_DIR", str(internal_dir))

        pyside_dir = internal_dir / "PySide6"
        if pyside_dir.is_dir():
            _prepend_path(str(pyside_dir))

        shiboken_dir = internal_dir / "shiboken6"
        if shiboken_dir.is_dir():
            _prepend_path(str(shiboken_dir))

        # Preload OpenSSL DLLs from the bundled directory to avoid picking up
        # incompatible versions from the target machine's PATH.
        for dll_name in (
            "libcrypto-3-x64.dll",
            "libssl-3-x64.dll",
            "libcrypto-3.dll",
            "libssl-3.dll",
        ):
            dll_path = internal_dir / dll_name
            if dll_path.is_file():
                try:
                    ctypes.WinDLL(str(dll_path))
                except OSError:
                    pass

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass and Path(meipass).is_dir():
        _prepend_path(str(meipass))


_init()
