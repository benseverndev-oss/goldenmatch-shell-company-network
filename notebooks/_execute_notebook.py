"""Execute the case-study notebook in-process and write back with outputs.

KNOWN GOTCHA (2026-05): on Windows + Python 3.13 + uv-managed venvs,
nbclient/jupyter_client hangs at kernel startup ("Kernel didn't respond
in 60 seconds"). This is a jupyter_client / asyncio incompatibility
specific to the Python 3.13 build that uv ships on Windows. Workarounds:

  * Run on Linux / macOS / WSL — kernel starts cleanly.
  * Run on the Railway shellnet-job container — kernel starts cleanly
    there too (Linux + Python 3.12).
  * Pin Python to 3.12 in pyproject.toml: `requires-python = "==3.12.*"`.

The notebook is committed without executed outputs; readers can run it
themselves under any of the working environments above. GitHub renders
the .ipynb source cells natively even without outputs.
"""
from __future__ import annotations

import os
from pathlib import Path

import nbformat
from nbclient import NotebookClient

# Set DATABASE_URL via env if not already set
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://golden:Qgl7Y6bNiRTI__Rr-OJy_a0dr1iVf8A9@metro.proxy.rlwy.net:38076/golden_showcase",
)

NB_PATH = Path("notebooks/01_case_study.ipynb")
nb = nbformat.read(NB_PATH, as_version=4)
client = NotebookClient(nb, timeout=180, allow_errors=True, kernel_name="python3")
client.execute()
nbformat.write(nb, NB_PATH)

n_code = sum(1 for c in nb.cells if c.cell_type == "code")
n_with_output = sum(1 for c in nb.cells if c.cell_type == "code" and c.outputs)
print(f"executed: {n_with_output}/{n_code} code cells have output")
for i, c in enumerate(nb.cells):
    if c.cell_type == "code":
        for out in c.outputs:
            if out.get("output_type") == "error":
                print(f"  cell {i} ERROR: {out.get('ename')}: {out.get('evalue')}")
                break
