from __future__ import annotations


def import_torch():
    """Import torch while skipping one invalid DLL path seen in this Windows env."""
    import os

    original = os.add_dll_directory

    def patched(path):
        if path == "E:bin":
            class DummyHandle:
                def close(self):
                    return None
            return DummyHandle()
        return original(path)

    os.add_dll_directory = patched
    try:
        import torch
        return torch
    finally:
        os.add_dll_directory = original
