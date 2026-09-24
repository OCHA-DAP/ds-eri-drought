"""Assemble the GitHub Pages site into _site/.

Copies pages/ and writes each tagged figure from the executed notebook to
_site/season-2026/figs/<name>.png, so rendered images are never committed.
A cell tagged `fig-<name>` supplies `<name>.png` (its first PNG output).
"""

import base64
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks" / "01_jja_season_2026.ipynb"
PAGES = ROOT / "pages"
SITE = ROOT / "_site"
FIGS = SITE / "season-2026" / "figs"
EXPECTED = {"rainfall-heatmap", "rainfall-10day", "ndvi-10day", "cdi-timeline", "cdi-maps"}


def main() -> None:
    if SITE.exists():
        shutil.rmtree(SITE)
    shutil.copytree(PAGES, SITE)
    FIGS.mkdir(parents=True, exist_ok=True)

    nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    written = set()
    for cell in nb["cells"]:
        for tag in cell.get("metadata", {}).get("tags", []):
            if not tag.startswith("fig-"):
                continue
            name = tag.removeprefix("fig-")
            png = next(
                (o["data"]["image/png"] for o in cell.get("outputs", []) if "image/png" in o.get("data", {})),
                None,
            )
            if png is None:
                raise SystemExit(f"cell tagged {tag} has no PNG output; execute the notebook first")
            (FIGS / f"{name}.png").write_bytes(base64.b64decode(png))
            written.add(name)

    missing = EXPECTED - written
    if missing:
        raise SystemExit(f"figures missing from notebook: {sorted(missing)}")
    print(f"built {SITE} with {len(written)} figures")


if __name__ == "__main__":
    main()
