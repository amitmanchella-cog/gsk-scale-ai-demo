"""Execute a notebook's code cells top-to-bottom (used to regenerate expected_output/).

Usage: cd notebooks && python run_notebook.py territory_kpis.ipynb
"""
import sys
from pathlib import Path

import nbformat

nb = nbformat.read(sys.argv[1], as_version=4)
ns: dict = {}
for cell in nb.cells:
    if cell.cell_type == "code":
        exec(compile(cell.source, Path(sys.argv[1]).name, "exec"), ns)
print(f"executed {sys.argv[1]}")
