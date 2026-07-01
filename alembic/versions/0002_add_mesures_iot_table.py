"""add mesures iot table

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-01 10:32:33.794416

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS mesures_iot (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            site VARCHAR(50) NOT NULL,
            line_id INTEGER NOT NULL,
            sensor_id VARCHAR(50) NOT NULL,
            temperature_c FLOAT NOT NULL,
            vibration_mms FLOAT,
            debit_uh FLOAT NOT NULL,
            CONSTRAINT uq_mesures_iot_timestamp_sensor UNIQUE (timestamp, sensor_id)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_mesures_iot_timestamp ON mesures_iot (timestamp)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_mesures_iot_sensor_id ON mesures_iot (sensor_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_mesures_iot_sensor_id")
    op.execute("DROP INDEX IF EXISTS ix_mesures_iot_timestamp")
    op.execute("DROP TABLE IF EXISTS mesures_iot")
