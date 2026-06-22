import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal


def _json_default(value):
    if isinstance(value, Decimal):
        return float(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


@dataclass
class CostSnapshot:
    report_for: str
    report_generated_on: str
    payload: dict
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    id: int | None = None

    def to_payload_json(self) -> str:
        return json.dumps(self.payload, default=_json_default)

    @classmethod
    def from_row(cls, row: tuple) -> "CostSnapshot":
        snapshot_id, report_for, report_generated_on, created_at, payload_json = row
        return cls(
            id=snapshot_id,
            report_for=report_for,
            report_generated_on=report_generated_on,
            created_at=created_at,
            payload=json.loads(payload_json),
        )

    @classmethod
    def from_report_data(cls, data: dict) -> "CostSnapshot":
        return cls(
            report_for=data.get("report_for", ""),
            report_generated_on=data.get("report_generated_on", ""),
            payload={k: v for k, v in data.items() if k != "diff"},
        )
