from __future__ import annotations

from datetime import UTC, date, datetime, timedelta


def utcnow() -> datetime:
    return datetime.now(UTC)


def start_of_day(value: date | datetime) -> datetime:
    date_value = value.date() if isinstance(value, datetime) else value
    return datetime.combine(date_value, datetime.min.time(), tzinfo=UTC)


def end_of_day(value: date | datetime) -> datetime:
    return start_of_day(value) + timedelta(days=1) - timedelta(microseconds=1)


def isoformat(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def parse_range_label(label: str, reference: date | None = None) -> tuple[date, date]:
    reference_date = reference or utcnow().date()
    normalized = label.lower().strip()

    if normalized == "7d":
        return reference_date - timedelta(days=6), reference_date
    if normalized == "30d":
        return reference_date - timedelta(days=29), reference_date
    if normalized == "90d":
        return reference_date - timedelta(days=89), reference_date
    if normalized == "mtd":
        return reference_date.replace(day=1), reference_date
    if normalized == "ytd":
        return reference_date.replace(month=1, day=1), reference_date

    raise ValueError(f"Unsupported range label: {label}")
