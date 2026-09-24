"""ICPAC East Africa Drought Watch monthly CDI, clipped to Eritrea admin 1.

Monthly GeoTIFFs are published on HDX per year
(`igad-region-monthly-combined-drought-indicator-cdi-<year>`). Only the Eritrea
window is read, over HTTP range requests, so the ~80 MB regional files are not
downloaded in full.
"""

import re

import geopandas as gpd
import numpy as np
import ocha_stratus as stratus
import pandas as pd
import rasterio
import rioxarray  # noqa: F401  (registers .rio)
import xarray as xr
from hdx.api.configuration import Configuration
from hdx.data.dataset import Dataset
from rasterio.features import rasterize
from rasterio.windows import from_bounds

from eri_drought.constants import PROJECT_PREFIX

MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
GDAL_ENV = {
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "GDAL_HTTP_MAX_RETRY": "3",
    "GDAL_HTTP_RETRY_DELAY": "5",
    "GDAL_HTTP_TIMEOUT": "60",
}


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


def cog_blob_name(year: int, month: int) -> str:
    return f"{PROJECT_PREFIX}/processed/icpac_cdi/eri_cdi_monthly_{year}-{month:02d}.tif"


def save_eritrea_cogs(
    years: list[int], adm1: gpd.GeoDataFrame, buffer_deg: float = 0.1
) -> list[str]:
    """Clip every published monthly CDI to the Eritrea bounding box and save as COGs.

    The clip is a rectangle (admin 1 bounds + `buffer_deg`), not masked to the
    border. Values are unchanged; stored as float32 with NaN nodata.
    """
    minx, miny, maxx, maxy = adm1.total_bounds
    bounds = (minx - buffer_deg, miny - buffer_deg, maxx + buffer_deg, maxy + buffer_deg)
    existing = {
        b.name
        for b in stratus.get_container_client(stage="dev").list_blobs(
            name_starts_with=f"{PROJECT_PREFIX}/processed/icpac_cdi/"
        )
    }
    saved = []
    for year in years:
        for month, url in list_monthly_files(year).items():
            name = cog_blob_name(year, month)
            if name in existing:
                saved.append(name)
                continue
            arr, transform = read_window(url, bounds)
            ny, nx = arr.shape
            x = transform.c + transform.a * (np.arange(nx) + 0.5)
            y = transform.f + transform.e * (np.arange(ny) + 0.5)
            da = xr.DataArray(arr.astype("float32"), coords={"y": y, "x": x}, dims=("y", "x"))
            da = da.rio.write_crs("EPSG:4326").rio.write_nodata(np.nan)
            da.attrs.update({"source": "ICPAC East Africa Drought Watch CDI", "source_url": url})
            stratus.upload_cog_to_blob(da, name, stage="dev")
            saved.append(name)
            print(f"saved {name}", flush=True)
    return saved


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
