"""
Single source of truth for "what time/date is it right now" across the
backend. Trip dates/times are entered and displayed as Lebanon wall-clock
time, but cloud containers (Railway included) typically run in UTC -- using
naive `datetime.now()`/`date.today()` directly would silently misalign
"today" filters and, worst of all, the reminder service's narrow 28-32
minute window by 2-3 hours.

now_beirut()/today_beirut() return NAIVE values that represent the current
Lebanon wall-clock moment, so they compare directly against the naive
trip_date/trip_time columns without tzinfo-mismatch errors.
"""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

LEBANON_TZ = ZoneInfo("Asia/Beirut")


def now_beirut() -> dt.datetime:
    """Current Lebanon wall-clock time, as a naive datetime."""
    return dt.datetime.now(LEBANON_TZ).replace(tzinfo=None)


def today_beirut() -> dt.date:
    """Current Lebanon calendar date."""
    return now_beirut().date()
