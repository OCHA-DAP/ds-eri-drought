# ds-eri-drought

Eritrea June to August (JJA) 2026 season compared with past seasons, by admin 1:

- **Rainfall**: CHIRPS dekadal totals, 1981 to 2026 (WFP subnational table).
- **NDVI**: MODIS dekadal NDVI and % of average, 2003 to 2026 (WFP subnational table).
- **CDI**: ICPAC East Africa Drought Watch monthly Combined Drought Indicator, 2020 to 2026
  ([HDX](https://data.humdata.org/dataset/igad-region-monthly-combined-drought-indicator-cdi-2026), CC BY 4.0).

The analysis is in [`notebooks/01_jja_season_2026.ipynb`](notebooks/01_jja_season_2026.ipynb)
(paired with a `py:percent` script via jupytext).

## Data

Everything is on the dev blob, `projects` container:

| Blob | Contents |
|---|---|
| `ds-eri-drought/raw/eri-rainfall-subnat-full.csv` | WFP dekadal rainfall, admin 1 and 2 |
| `ds-eri-drought/raw/eri-ndvi-subnat-full.csv` | WFP dekadal NDVI, admin 1 and 2 |
| `ds-eri-drought/processed/cdi_adm1_jja_counts.parquet` | CDI pixel counts per admin 1, class value, Jun to Aug 2020 to 2026 |

CDI GeoTIFFs are not stored: `eri_drought.cdi` reads only the Eritrea window from HDX over
HTTP range requests. Admin 1 boundaries come from FieldMaps via `ocha-stratus`.

## Notes on the inputs

- ER3 has two `adm_id`s (1206 and 1211) in the WFP tables; admin 1 values combine them
  weighted by `n_pixels`.
- CDI class values follow the EADW factsheet: 1 to 3 Watch, 4 to 6 Warning, 7 to 10 Alert,
  11 to 12 Partial recovery, 13 to 14 Full recovery. Values 0 and 15 are not in the factsheet
  table.

## Setup

```bash
uv sync
uv run jupyter lab
```

Blob access needs the usual `DSCI_AZ_BLOB_DEV_SAS` / `DSCI_AZ_BLOB_DEV_SAS_WRITE` env vars.
