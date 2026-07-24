"""
Background reminder service.

Every 60 seconds, scans upcoming (confirmed/in_progress, not-yet-reminded)
trips and fires a Socket.IO "reminder" event for any trip that is between
28 and 32 minutes away. Each trip is only ever reminded once (`reminded`
flag flips to True immediately after firing).

Also keeps a small in-memory ring buffer of recently fired reminders so
the frontend notification bell can populate itself on page load, since
Socket.IO only delivers events to clients connected at the moment they fire.

NOTE: `recent_notifications` lives only in this process's memory -- it
resets on every restart/redeploy and is NOT shared across instances. That's
fine for the current single-instance deployment target; if this is ever
scaled horizontally, this needs to move to a shared store (DB table, Redis).
"""
from __future__ import annotations

import asyncio
import datetime as dt
from collections import deque
from typing import Deque

from sqlalchemy import select

from database import db_session
from models import Booking
from timezone_utils import now_beirut

POLL_INTERVAL_SECONDS = 60
REMINDER_WINDOW_MIN = 28
REMINDER_WINDOW_MAX = 32
NOTIFICATION_HISTORY_SIZE = 50

recent_notifications: Deque[dict] = deque(maxlen=NOTIFICATION_HISTORY_SIZE)

_task: asyncio.Task | None = None


async def _reminder_loop(sio) -> None:
    while True:
        try:
            await _check_reminders(sio)
        except Exception as exc:  # pragma: no cover - defensive background loop
            print(f"[reminder_service] error while checking reminders: {exc}")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def _check_reminders(sio) -> None:
    now = now_beirut()
    async with db_session() as db:
        stmt = select(Booking).where(
            Booking.status.in_(["confirmed", "in_progress"]),
            Booking.reminded.is_(False),
        )
        result = await db.execute(stmt)
        candidates = result.scalars().all()

        for booking in candidates:
            trip_dt = dt.datetime.combine(booking.trip_date, booking.trip_time)
            minutes_until = (trip_dt - now).total_seconds() / 60.0

            if REMINDER_WINDOW_MIN <= minutes_until <= REMINDER_WINDOW_MAX:
                booking.reminded = True
                await db.commit()

                payload = {
                    "booking_id": booking.id,
                    "client_name": booking.client_name,
                    "pickup": booking.pickup,
                    "dropoff": booking.dropoff,
                    "trip_date": booking.trip_date.isoformat(),
                    "trip_time": booking.trip_time.isoformat(),
                    "minutes_until": round(minutes_until),
                    "message_en": (
                        f"Reminder: {booking.client_name}'s trip ({booking.pickup} -> "
                        f"{booking.dropoff}) is in about {round(minutes_until)} minutes."
                    ),
                    "message_ar": (
                        f"تذكير: رحلة {booking.client_name} (من {booking.pickup} إلى "
                        f"{booking.dropoff}) بعد حوالي {round(minutes_until)} دقيقة."
                    ),
                    "message_fr": (
                        f"Rappel : le trajet de {booking.client_name} ({booking.pickup} -> "
                        f"{booking.dropoff}) est dans environ {round(minutes_until)} minutes."
                    ),
                    "fired_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                }
                recent_notifications.appendleft(payload)

                if sio is not None:
                    await sio.emit("reminder", payload)


def start(sio) -> None:
    """Start the background polling task. Call once on app startup."""
    global _task
    if _task is None or _task.done():
        _task = asyncio.create_task(_reminder_loop(sio))


def stop() -> None:
    """Cancel the background polling task. Call on app shutdown."""
    global _task
    if _task is not None:
        _task.cancel()
        _task = None
