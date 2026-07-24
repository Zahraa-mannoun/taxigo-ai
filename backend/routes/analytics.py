"""
Weekly earnings analytics and schedule export.
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Booking, BookingOut, ExportRequest, WeeklyAnalyticsDay, WeeklyAnalyticsResponse
from timezone_utils import today_beirut

router = APIRouter()


@router.get("/analytics/weekly", response_model=WeeklyAnalyticsResponse)
async def get_weekly_analytics(db: AsyncSession = Depends(get_db)):
    """Earnings + trip counts for each of the last 7 days (oldest first)."""
    today = today_beirut()
    start = today - dt.timedelta(days=6)

    stmt = select(Booking).where(
        Booking.trip_date.between(start, today),
        Booking.status != "cancelled",
    )
    result = await db.execute(stmt)
    bookings = result.scalars().all()

    days: list[WeeklyAnalyticsDay] = []
    for offset in range(7):
        day = start + dt.timedelta(days=offset)
        day_bookings = [b for b in bookings if b.trip_date == day]
        earned = sum((b.fare for b in day_bookings if b.status == "completed"), Decimal("0"))
        projected = sum((b.fare for b in day_bookings), Decimal("0"))
        days.append(
            WeeklyAnalyticsDay(
                date=day,
                earned=earned,
                projected=projected,
                trip_count=len(day_bookings),
            )
        )

    return WeeklyAnalyticsResponse(
        days=days,
        total_earned=sum((d.earned for d in days), Decimal("0")),
        total_projected=sum((d.projected for d in days), Decimal("0")),
        total_trips=sum(d.trip_count for d in days),
    )


@router.post("/analytics/export")
async def export_schedule(payload: ExportRequest, db: AsyncSession = Depends(get_db)):
    """Export the schedule as JSON for the requested scope (today/week/all)."""
    today = today_beirut()
    stmt = select(Booking).where(Booking.status != "cancelled")

    if payload.scope == "today":
        stmt = stmt.where(Booking.trip_date == today)
    elif payload.scope == "week":
        stmt = stmt.where(Booking.trip_date.between(today, today + dt.timedelta(days=6)))

    stmt = stmt.order_by(Booking.trip_date, Booking.trip_time)
    result = await db.execute(stmt)
    bookings = result.scalars().all()

    return {
        "scope": payload.scope,
        "exported_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "trip_count": len(bookings),
        "trips": [BookingOut.model_validate(b).model_dump(mode="json") for b in bookings],
    }
