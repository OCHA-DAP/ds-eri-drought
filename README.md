# ds-eri-drought

Eritrea June to August (JJA) 2026 season compared with past seasons, by admin 1:

- **Rainfall**: CHIRPS dekadal totals, 1981 to 2026 (WFP subnational table).
- **NDVI**: MODIS dekadal NDVI and % of average, 2003 to 2026 (WFP subnational table).
- **CDI**: ICPAC East Africa Drought Watch monthly Combined Drought Indicator, 2020 to 2026
  ([HDX](https://data.humdata.org/dataset/igad-region-monthly-combined-drought-indicator-cdi-2026), CC BY 4.0).

The analysis is in [`notebooks/01_jja_season_2026.ipynb`](notebooks/01_jja_season_2026.ipynb)
(paired with a `py:percent` script via jupytext).

Report site: <https://ocha-dap.github.io/ds-eri-drought/>. `pages/` holds the landing page and
the report (`pages/season-2026/`); `scripts/build_pages.py` assembles `_site/`, writing each
notebook cell tagged `fig-<name>` to `season-2026/figs/<name>.png`, so rendered charts are never
committed. `.github/workflows/pages.yml` deploys on push to `main`. Re-execute the notebook and
commit it to update the charts.

## Data

Everything is on the dev blob, `projects` container:

| Blob | Contents |
|---|---|
| `ds-eri-drought/raw/eri-rainfall-subnat-full.csv` | WFP dekadal rainfall, admin 1 and 2 |
| `ds-eri-drought/raw/eri-ndvi-subnat-full.csv` | WFP dekadal NDVI, admin 1 and 2 |
| `ds-eri-drought/processed/cdi_adm1_jja_counts.parquet` | CDI pixel counts per admin 1, class value, Jun to Aug 2020 to 2026 |
| `ds-eri-drought/processed/icpac_cdi/eri_cdi_monthly_YYYY-MM.tif` | Monthly CDI COGs clipped to Eritrea, every month published on HDX from 2020 to 2026 |

The CDI COGs are the ICPAC regional GeoTIFFs cut to the Eritrea admin 1 bounding box plus
0.1°: a rectangle, not masked to the border, values unchanged (float32, NaN nodata).
`eri_drought.cdi.save_eritrea_cogs` builds them by reading only that window from HDX over
HTTP range requests; reruns skip months already on blob. Load one with
`stratus.open_blob_cog(cdi.cog_blob_name(2026, 8))`.

Admin 1 boundaries come from FieldMaps via `ocha-stratus`.

## Notes on the inputs

- ER3 has two `adm_id`s in the WFP tables: 1211 (mainland, 1141 pixels) and 1206 (37 pixels,
  matching the Red Sea islands by area). Only 1211 is used, so ER3 values are mainland only.
- June to August rainfall uses WFP's 3-month columns (`r3h`, `r3h_avg`, `r3q`) on the
  21 August dekad.
- CDI class values follow the EADW factsheet: 1 to 3 Watch, 4 to 6 Warning, 7 to 10 Alert,
  11 to 12 Partial recovery, 13 to 14 Full recovery. Values 0 and 15 are not in the factsheet
  table.

## Setup

```bash
uv sync
uv run jupyter lab
```

Blob access needs the usual `DSCI_AZ_BLOB_DEV_SAS` / `DSCI_AZ_BLOB_DEV_SAS_WRITE` env vars.
