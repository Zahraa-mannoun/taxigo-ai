"""
Notification history endpoint.

Live reminders are pushed over Socket.IO as they fire, but a page that
just (re)loaded has missed anything emitted before it connected. This
endpoint backfills the bell dropdown with the recent in-memory history
kept by the reminder service.
"""
from __future__ import annotations

from fastapi import APIRouter

from services.reminder_service import recent_notifications

router = APIRouter()


@router.get("/notifications/recent")
async def get_recent_notifications():
    return {"notifications": list(recent_notifications)}
