from datetime import datetime, timezone, timedelta
from typing import List

def datetime_from_string(date: str | datetime, fmt: str) -> datetime:
    """Parse ``date`` with ``fmt`` and attach UTC; pass through if already a ``datetime``."""
    try:
        formated_date = datetime.strptime(date, fmt)
        formated_date = formated_date.replace(tzinfo=timezone.utc)
        return formated_date
    except Exception:
        if isinstance(date, datetime):
            return date
        else:
            raise

def string_from_datetime(date: datetime, fmt: str) -> str:
    """Format ``date`` with ``fmt`` and return the string."""
    try:
        formatted_str = date.strftime(fmt)
        return formatted_str
    except Exception:
        raise

def timestamp_from_datetime(date: datetime, units: str = "s") -> float | int:
    """Convert ``date`` to Unix timestamp in seconds or milliseconds.

    Args:
        date: Timezone-aware or naive datetime (``timestamp()`` semantics apply).
        units: ``"s"`` for seconds (float) or ``"ms"`` for integer milliseconds.

    Returns:
        Unix time in the requested units.

    Raises:
        ValueError: If ``units`` is not ``"s"`` or ``"ms"``.
    """
    try:
        ts_seconds = date.timestamp()
        if units == "s":
            return ts_seconds
        if units == "ms":
            return int(ts_seconds * 1000)
        raise ValueError(f"units must be 's' or 'ms', got {units!r}")
    except Exception:
        raise

def dates_generator(start: str, end: str, fmt: str) -> List[datetime]:
    """Yield each calendar day from ``start`` through ``end`` inclusive as UTC datetimes.

    Args:
        start: Start date string parsed with ``fmt``.
        end: End date string parsed with ``fmt``.

    Returns:
        List of ``datetime`` objects at midnight UTC for each day in the range.

    Raises:
        ValueError: If ``end`` is before ``start``.
    """
    
    start_date = datetime_from_string(start, fmt)
    end_date   = datetime_from_string(end, fmt)
    
    if end_date < start_date:
        raise ValueError(f"end date can not be lower than start date")

    days_range = (end_date - start_date).days + 1
    dates = [start_date + timedelta(days=days) for days in range(days_range)]
    
    return dates
