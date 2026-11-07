#!/usr/bin/env python3
"""Baut die Claude-Erweiterung: dist/safari-tabs.mcpb (ZIP mit manifest.json + Code)."""
import json
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "dist" / "safari-tabs.mcpb"

files = {
    "manifest.json": HERE / "manifest.json",
    "server.py": HERE / "server.py",
    "safari_tabs.py": HERE.parent / "safari_tabs.py",
}
json.loads(files["manifest.json"].read_text(encoding="utf-8"))  # Syntax prüfen
OUT.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    for name, src in files.items():
        info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
        info.external_attr = 0o644 << 16
        info.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(info, src.read_bytes())
print(f"{OUT} ({OUT.stat().st_size // 1024} KB)")
