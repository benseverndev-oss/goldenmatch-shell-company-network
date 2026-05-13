"""List members of a ZIP file. One-off diagnostic."""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

path = Path(sys.argv[1])
with zipfile.ZipFile(path) as zf:
    members = sorted(zf.namelist())
print(f"{path}: {len(members)} members")
for name in members[:80]:
    info = zf.getinfo(name) if False else None
    print(f"  {name}")
if len(members) > 80:
    print(f"  ... {len(members) - 80} more")
