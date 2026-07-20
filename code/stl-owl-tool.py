#!/usr/bin/env python3
"""STL CLI entrypoint kept separate from legacy script naming."""

import importlib.util
import sys
from pathlib import Path


if __name__ == "__main__":
    target = Path(__file__).with_name("mtl-owl-tool.py")
    spec = importlib.util.spec_from_file_location("stl_cli_target", target)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.argv[0] = Path(__file__).name
    module.main()
