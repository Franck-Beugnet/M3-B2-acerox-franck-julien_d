"""Ingestion IoT reusable pipeline: load, normalize, persist.

Usage:
    python -m src.ingest_iot
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from src.db import engine, get_session
from src.models import Base, MesureIoT

IOT_CSV: Path = Path(__file__).parent.parent / "data" / "capteurs_iot.csv"
REQUIRED_COLUMNS = (
    "timestamp",
    "site",
    "line_id",
    "sensor_id",
    "temperature_c",
    "vibration_mms",
    "debit_uh",
)

logger = logging.getLogger(__name__)


class NormalizationError(ValueError):
    """Raised when input data cannot be normalized to the expected schema."""


def init_db() -> None:
    """Create declared tables for local/dev usage."""
    Base.metadata.create_all(engine)


def load_iot_csv(csv_path: Path = IOT_CSV) -> pd.DataFrame:
    """Load raw IoT CSV as DataFrame."""
    return pd.read_csv(csv_path)


def normalize_iot_dataframe(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Normalize raw IoT data to contract-compliant schema.

    Applied rules:
    - enforce expected columns
    - parse and type columns
    - drop rows missing required fields
    - remove known faulty Roubaix line 3 records
    - deduplicate by (timestamp, sensor_id)
    """
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df_raw.columns]
    if missing_columns:
        raise NormalizationError(f"Missing required columns: {missing_columns}")

    df = df_raw.loc[:, REQUIRED_COLUMNS].copy()

    df["site"] = df["site"].astype("string").str.strip()
    df["sensor_id"] = df["sensor_id"].astype("string").str.strip()

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["line_id"] = pd.to_numeric(df["line_id"], errors="coerce").astype("Int64")
    df["temperature_c"] = pd.to_numeric(df["temperature_c"], errors="coerce")
    df["vibration_mms"] = pd.to_numeric(df["vibration_mms"], errors="coerce")
    df["debit_uh"] = pd.to_numeric(df["debit_uh"], errors="coerce")

    required_non_null = ["timestamp", "site", "line_id", "sensor_id", "temperature_c", "debit_uh"]
    df = df.dropna(subset=required_non_null)

    df = df[(df["site"] != "") & (df["sensor_id"] != "")]

    faulty_mask = (
        (df["site"].str.casefold() == "roubaix")
        & (df["line_id"] == 3)
        & (df["temperature_c"].between(140, 160, inclusive="both"))
        & (df["vibration_mms"] == 12.0)
    )
    df = df.loc[~faulty_mask].copy()

    # Keep latest value for duplicate keys expected to be unique in target table.
    df = df.sort_values("timestamp").drop_duplicates(subset=["timestamp", "sensor_id"], keep="last")

    df["line_id"] = df["line_id"].astype(int)

    return df.reset_index(drop=True)


def ingest_mesures_iot(csv_path: Path = IOT_CSV) -> int:
    """Ingest normalized IoT rows into DB, idempotently.

    Returns number of newly inserted rows.
    """
    df = normalize_iot_dataframe(load_iot_csv(csv_path))
    if df.empty:
        return 0

    session = get_session()
    inserted = 0
    try:
        existing_keys = {
            (row.timestamp, row.sensor_id)
            for row in session.query(MesureIoT.timestamp, MesureIoT.sensor_id).all()
        }

        for row in df.itertuples(index=False):
            key = (row.timestamp.to_pydatetime(), row.sensor_id)
            if key in existing_keys:
                continue

            session.add(
                MesureIoT(
                    timestamp=key[0],
                    site=row.site,
                    line_id=int(row.line_id),
                    sensor_id=row.sensor_id,
                    temperature_c=float(row.temperature_c),
                    vibration_mms=None if pd.isna(row.vibration_mms) else float(row.vibration_mms),
                    debit_uh=float(row.debit_uh),
                )
            )
            existing_keys.add(key)
            inserted += 1

        session.commit()
    finally:
        session.close()

    return inserted


def main() -> None:
    """CLI entrypoint for local ingestion runs."""
    init_db()
    inserted = ingest_mesures_iot()
    logger.info("Ingestion IoT: %s ligne(s) inseree(s) (idempotent).", inserted)


if __name__ == "__main__":
    main()
