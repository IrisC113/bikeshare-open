"""Stage 1: fetch the raw dataset and assert its shape.

Run: python -m src.ingest
"""
import hashlib
import sys
import urllib.request

import pandas as pd

from src.config import DATA_URL, RAW, RAW_SHA256

EXPECTED_MIN_ROWS = 700
REQUIRED_COLS = {"dteday", "cnt", "casual", "registered", "temp", "hum", "windspeed"}


def verify_raw_integrity() -> None:
    """Reject changed bytes, including shell writes outside Edit/Write hooks."""
    actual = hashlib.sha256(RAW.read_bytes()).hexdigest()
    if actual != RAW_SHA256:
        raise ValueError(
            f"raw data checksum mismatch: expected {RAW_SHA256}, got {actual}; "
            "restore the checked-in bike_daily.csv"
        )


def download(force: bool = False) -> None:
    if RAW.exists() and not force:
        verify_raw_integrity()
        return
    RAW.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(DATA_URL, RAW)
    verify_raw_integrity()


def load_raw() -> pd.DataFrame:
    verify_raw_integrity()
    df = pd.read_csv(RAW, parse_dates=["dteday"])
    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"raw data is missing required columns: {sorted(missing)}")
    if len(df) < EXPECTED_MIN_ROWS:
        raise ValueError(f"raw data has only {len(df)} rows; expected >= {EXPECTED_MIN_ROWS}")
    return df


if __name__ == "__main__":
    download(force="--force" in sys.argv)
    df = load_raw()
    print(f"OK ingest: {len(df)} rows, {df.dteday.min().date()} -> {df.dteday.max().date()}")
