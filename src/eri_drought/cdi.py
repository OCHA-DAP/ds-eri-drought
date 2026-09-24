"""ICPAC East Africa Drought Watch monthly CDI, clipped to Eritrea admin 1.

Monthly GeoTIFFs are published on HDX per year
(`igad-region-monthly-combined-drought-indicator-cdi-<year>`). Only the Eritrea
window is read, over HTTP range requests, so the ~80 MB regional files are not
downloaded in full.
"""

import re

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from hdx.api.configuration import Configuration
from hdx.data.dataset import Dataset
from rasterio.features import rasterize
from rasterio.windows import from_bounds

MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
GDAL_ENV = {"GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR", "GDAL_HTTP_MAX_RETRY": "3"}


def _hdx_config() -> None:
    try:
        Configuration.create(
            hdx_site="prod", user_agent="ds-eri-drought", hdx_read_only=True
        )
    except Exception as e:  # already created in this session
        if "already" not in str(e).lower():
            raise


def list_monthly_files(year: int) -> dict[int, str]:
    """Month number -> download URL for one year's monthly CDI dataset."""
    _hdx_config()
    ds = Dataset.read_from_hdx(f"igad-region-monthly-combined-drought-indicator-cdi-{year}")
    out = {}
    for res in ds.get_resources():
        m = re.search(r"(?:-|_)(" + "|".join(MONTHS) + r")\.tif$", res["name"].lower())
        if m:
            out[MONTHS.index(m.group(1)) + 1] = res["url"]
    return dict(sorted(out.items()))


def read_window(url: str, bounds: tuple[float, float, float, float]):
    with rasterio.Env(**GDAL_ENV), rasterio.open(f"/vsicurl/{url}") as src:
        window = from_bounds(*bounds, src.transform).round_offsets().round_lengths()
        arr = src.read(1, window=window)
        transform = src.window_transform(window)
    return arr, transform


def class_counts_by_adm1(
    arr: np.ndarray, transform, adm1: gpd.GeoDataFrame
) -> pd.DataFrame:
    """Pixel counts of each CDI value inside each admin 1 (pixel-centre rule)."""
    rows = []
    for _, row in adm1.iterrows():
        mask = rasterize(
            [(row.geometry, 1)], out_shape=arr.shape, transform=transform, fill=0
        ).astype(bool)
        vals = arr[mask]
        vals = vals[~np.isnan(vals)]
        u, c = np.unique(vals, return_counts=True)
        for v, n in zip(u, c):
            rows.append({"PCODE": row.PCODE, "cdi": int(v), "n": int(n)})
    return pd.DataFrame(rows)


def cdi_adm1(years: list[int], months: list[int], adm1: gpd.GeoDataFrame) -> pd.DataFrame:
    """Long table: year, month, PCODE, cdi value, pixel count."""
    bounds = tuple(adm1.total_bounds)
    frames = []
    for year in years:
        files = list_monthly_files(year)
        for month in months:
            if month not in files:
                print(f"CDI {year}-{month:02d}: not published")
                continue
            arr, transform = read_window(files[month], bounds)
            df = class_counts_by_adm1(arr, transform, adm1)
            df["year"], df["month"] = year, month
            frames.append(df)
    return pd.concat(frames, ignore_index=True)
