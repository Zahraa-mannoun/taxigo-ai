"""
Conflict detection for overlapping trips.

Two trips on the same date are considered conflicting if their pickup
times fall within 60 minutes of each other. Cancelled trips are ignored,
and a booking never conflicts with itself (used during updates).
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Booking

CONFLICT_WINDOW_MINUTES = 60


def _minutes_between(date_a: dt.date, time_a: dt.time, date_b: dt.date, time_b: dt.time) -> float:
    dt_a = dt.datetime.combine(date_a, time_a)
    dt_b = dt.datetime.combine(date_b, time_b)
    return abs((dt_a - dt_b).total_seconds()) / 60.0


async def find_conflict(
    db: AsyncSession,
    trip_date: dt.date,
    trip_time: dt.time,
    exclude_booking_id: int | None = None,
) -> Booking | None:
    """Return the first conflicting booking, if any, else None.

    Queries a window of adjacent calendar dates (not just an exact date
    match) so a trip near midnight is correctly compared against trips on
    the neighboring day too -- e.g. 11:50pm and 12:10am the next day are 20
    minutes apart and must be flagged, even though they fall on different
    `trip_date` values.
    """
    window = dt.timedelta(minutes=CONFLICT_WINDOW_MINUTES)
    trip_dt = dt.datetime.combine(trip_date, trip_time)
    range_start = (trip_dt - window).date()
    range_end = (trip_dt + window).date()

    stmt = select(Booking).where(
        Booking.trip_date.between(range_start, range_end),
        Booking.status != "cancelled",
    )
    if exclude_booking_id is not None:
        stmt = stmt.where(Booking.id != exclude_booking_id)

    result = await db.execute(stmt)
    candidates = result.scalars().all()

    for candidate in candidates:
        diff = _minutes_between(trip_date, trip_time, candidate.trip_date, candidate.trip_time)
        if diff < CONFLICT_WINDOW_MINUTES:
            return candidate

    return None
