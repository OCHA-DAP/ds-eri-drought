"""Load WFP subnational rainfall/NDVI tables and Eritrea admin 1 boundaries."""

import geopandas as gpd
import ocha_stratus as stratus
import pandas as pd

from eri_drought.constants import PROJECT_PREFIX

RAW_RAINFALL = f"{PROJECT_PREFIX}/raw/eri-rainfall-subnat-full.csv"
RAW_NDVI = f"{PROJECT_PREFIX}/raw/eri-ndvi-subnat-full.csv"

# COD-AB admin 1 names (FieldMaps `adm1_src` -> `adm1_name`)
ADM1_NAMES = {
    "ER1": "Debubawi Keih Bahri",
    "ER2": "Maekel",
    "ER3": "Semienawi Keih Bahri",
    "ER4": "Anseba",
    "ER5": "Gash Barka",
    "ER6": "Debub",
}


def _load_wfp_table(blob_name: str) -> pd.DataFrame:
    df = stratus.load_csv_from_blob(blob_name, stage="dev", parse_dates=["date"])
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    return df


def _aggregate_adm1(df: pd.DataFrame, value_cols: list[str]) -> pd.DataFrame:
    """Pixel-weighted admin 1 values.

    ER3 appears under two `adm_id`s (two polygons sharing the PCODE), so rows
    are combined by PCODE with `n_pixels` as the weight.
    """
    adm1 = df[df["adm_level"] == 1].copy()
    for col in value_cols:
        adm1[col] = adm1[col] * adm1["n_pixels"]
    keys = ["date", "year", "month", "PCODE"]
    out = adm1.groupby(keys, as_index=False)[value_cols + ["n_pixels"]].sum()
    for col in value_cols:
        out[col] = out[col] / out["n_pixels"]
    out["adm1_name"] = out["PCODE"].map(ADM1_NAMES)
    return out


def load_rainfall_adm1() -> pd.DataFrame:
    """Dekadal CHIRPS rainfall (mm), 3-month rolling totals and WFP's 3-month anomaly
    (`r3q`, % of average) by admin 1."""
    df = _load_wfp_table(RAW_RAINFALL)
    out = _aggregate_adm1(df, ["rfh", "rfh_avg", "r3h", "r3h_avg", "r3q"])
    status = df[df["adm_level"] == 1].groupby("date")["version"].first()
    out["version"] = out["date"].map(status)
    return out


def load_ndvi_adm1() -> pd.DataFrame:
    """Dekadal NDVI (`vim`), its long-term average and % of average by admin 1."""
    out = _aggregate_adm1(_load_wfp_table(RAW_NDVI), ["vim", "vim_avg"])
    out["viq"] = 100 * out["vim"] / out["vim_avg"]
    return out


def load_adm1() -> gpd.GeoDataFrame:
    gdf = stratus.codab.load_codab_from_fieldmaps("ERI", admin_level=1)
    return gdf.rename(columns={"adm1_src": "PCODE"})[["PCODE", "adm1_name", "geometry"]]
