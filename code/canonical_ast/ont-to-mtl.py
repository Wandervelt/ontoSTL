"""Backward-compatible wrapper for renamed module `ont-to-stl.py`."""

import importlib.util
import runpy
import sys
from pathlib import Path


_TARGET = Path(__file__).with_name("ont-to-stl.py")
_CODE_DIR = str(Path(__file__).resolve().parents[1])
if _CODE_DIR not in sys.path:
    sys.path.insert(0, _CODE_DIR)
_SPEC = importlib.util.spec_from_file_location("canonical_ont_to_stl_impl", _TARGET)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

for _name in dir(_MODULE):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_MODULE, _name)

if __name__ == "__main__":
    runpy.run_path(str(_TARGET), run_name="__main__")
