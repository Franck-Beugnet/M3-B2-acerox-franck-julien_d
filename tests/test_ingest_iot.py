from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import select

from src.ingest_iot import ingest_mesures_iot, normalize_iot_dataframe
from src.models import MesureIoT


def test_normalize_iot_dataframe_types_dedup_and_missing() -> None:
    raw = pd.DataFrame(
        [
            {
                "timestamp": "2026-04-01T10:00:00",
                "site": "Roubaix",
                "line_id": "3",
                "sensor_id": "SROU-L3-T01",
                "temperature_c": "145.2",
                "vibration_mms": "12.0",
                "debit_uh": "101.2",
            },
            {
                "timestamp": "2026-04-01T10:00:00",
                "site": "Lyon",
                "line_id": "1",
                "sensor_id": "SLYO-L1-T01",
                "temperature_c": "50.0",
                "vibration_mms": "3.0",
                "debit_uh": "100.0",
            },
            {
                "timestamp": "2026-04-01T10:00:00",
                "site": "Lyon",
                "line_id": "1",
                "sensor_id": "SLYO-L1-T01",
                "temperature_c": "52.0",
                "vibration_mms": "4.0",
                "debit_uh": "100.5",
            },
            {
                "timestamp": "2026-04-01T11:00:00",
                "site": "Saint-Etienne",
                "line_id": "2",
                "sensor_id": "SSAI-L2-T01",
                "temperature_c": "61.0",
                "vibration_mms": "",
                "debit_uh": "98.0",
            },
            {
                "timestamp": "2026-04-01T11:30:00",
                "site": "Saint-Etienne",
                "line_id": "2",
                "sensor_id": "SSAI-L2-T01",
                "temperature_c": "",
                "vibration_mms": "3.0",
                "debit_uh": "98.0",
            },
        ]
    )

    clean = normalize_iot_dataframe(raw)

    assert len(clean) == 2
    assert pd.api.types.is_datetime64_any_dtype(clean["timestamp"])
    assert pd.api.types.is_integer_dtype(clean["line_id"])

    kept = clean.loc[clean["sensor_id"] == "SLYO-L1-T01"].iloc[0]
    assert kept["temperature_c"] == 52.0

    missing_vibration = clean.loc[clean["sensor_id"] == "SSAI-L2-T01"].iloc[0]
    assert pd.isna(missing_vibration["vibration_mms"])


def test_ingest_mesures_iot_is_idempotent(tmp_engine, tmp_session, tmp_path: Path, monkeypatch) -> None:
    csv_path = tmp_path / "capteurs.csv"
    csv_path.write_text(
        "\n".join(
            [
                "timestamp,site,line_id,sensor_id,temperature_c,vibration_mms,debit_uh",
                "2026-04-02T10:00:00,Lyon,1,SLYO-L1-T01,70.5,4.2,101.0",
                "2026-04-02T11:00:00,Saint-Etienne,2,SSAI-L2-T01,66.0,,99.0",
                "2026-04-02T11:00:00,Saint-Etienne,2,SSAI-L2-T01,67.0,,99.1",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr("src.ingest_iot.get_session", lambda: tmp_session)

    inserted_first = ingest_mesures_iot(csv_path)
    inserted_second = ingest_mesures_iot(csv_path)

    assert inserted_first == 2
    assert inserted_second == 0

    rows = tmp_session.execute(select(MesureIoT).order_by(MesureIoT.timestamp)).scalars().all()
    assert len(rows) == 2
    assert rows[1].vibration_mms is None
