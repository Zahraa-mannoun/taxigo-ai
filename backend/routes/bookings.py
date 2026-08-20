"""
REST endpoints for booking CRUD, status transitions, cancellation,
force-booking past a conflict, and per-client trip history.
"""
from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import (
    Booking,
    BookingOut,
    ClientHistoryResponse,
    ForceBookRequest,
    StatusUpdate,
)
router = APIRouter()

NOT_FOUND_DETAIL = {
    "en": "That booking could not be found.",
    "ar": "ما تم إيجاد هالحجز.",
    "fr": "Cette réservation est introuvable.",
}

# Note: a raw invalid *status value* (e.g. "banana") never reaches our code --
# StatusUpdate.status is a Pydantic Literal, so FastAPI rejects it with its
# own 422 before this module runs. What we validate here is invalid
# *transitions* between otherwise-valid statuses (e.g. completed -> confirmed).
INVALID_TRANSITION_DETAIL = {
    "en": "That status change isn't allowed.",
    "ar": "ما فيك تعمل هيدا التغيير بالحالة.",
    "fr": "Ce changement de statut n'est pas autorisé.",
}

ALLOWED_TRANSITIONS = {
    "confirmed": ["in_progress", "cancelled"],
    "in_progress": ["completed", "cancelled"],
    "completed": [],  # terminal state
    "cancelled": [],  # terminal state
}


def _escape_like(value: str) -> str:
    """Escape SQL LIKE/ILIKE wildcards so a literal '%' or '_' in a client
    name can't be misinterpreted as a pattern wildcard."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def _get_booking_or_404(db: AsyncSession, booking_id: int) -> Booking:
    booking = await db.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail=NOT_FOUND_DETAIL)
    return booking


@router.get("/bookings", response_model=list[BookingOut])
async def get_active_bookings(db: AsyncSession = Depends(get_db)):
    """Active trips: confirmed + in_progress, soonest first."""
    stmt = (
        select(Booking)
        .where(Booking.status.in_(["confirmed", "in_progress"]))
        .order_by(Booking.trip_date, Booking.trip_time)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/bookings/completed", response_model=list[BookingOut])
async def get_completed_bookings(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Booking)
        .where(Booking.status == "completed")
        .order_by(Booking.trip_date.desc(), Booking.trip_time.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/bookings/history", response_model=list[BookingOut])
async def get_booking_history(db: AsyncSession = Depends(get_db)):
    """All non-cancelled bookings, most recent first."""
    stmt = (
        select(Booking)
        .where(Booking.status != "cancelled")
        .order_by(Booking.trip_date.desc(), Booking.trip_time.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.patch("/bookings/{booking_id}/status", response_model=BookingOut)
async def update_booking_status(
    booking_id: int,
    payload: StatusUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    booking = await _get_booking_or_404(db, booking_id)

    allowed = ALLOWED_TRANSITIONS.get(booking.status, [])
    if payload.status not in allowed:
        raise HTTPException(status_code=400, detail=INVALID_TRANSITION_DETAIL)

    booking.status = payload.status
    await db.commit()
    await db.refresh(booking)

    sio = getattr(request.app.state, "sio", None)
    if sio is not None:
        await sio.emit("booking_status_updated", BookingOut.model_validate(booking).model_dump(mode="json"))

    return booking


@router.delete("/bookings/{booking_id}", response_model=BookingOut)
async def cancel_booking(booking_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    """Soft-cancels a booking (sets status=cancelled) so history is preserved."""
    booking = await _get_booking_or_404(db, booking_id)
    booking.status = "cancelled"
    await db.commit()
    await db.refresh(booking)

    sio = getattr(request.app.state, "sio", None)
    if sio is not None:
        await sio.emit("booking_cancelled", BookingOut.model_validate(booking).model_dump(mode="json"))

    return booking


@router.post("/force-book", response_model=BookingOut, status_code=201)
async def force_book(payload: ForceBookRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Create a booking even though it conflicts with another trip.

    Used by the frontend's conflict card when the driver explicitly
    confirms they want to double-book a time slot.

    INVARIANT: pickup and dropoff MUST be stored in English. The frontend's
    translateLocation() only translates FROM English -- callers that bypass
    the AI agent (like this endpoint) are responsible for upholding this
    themselves, since there's no normalize_location() safety net here.
    """
    booking = Booking(
        client_name=payload.client_name,
        pickup=payload.pickup,
        dropoff=payload.dropoff,
        trip_date=payload.trip_date,
        trip_time=payload.trip_time,
        fare=payload.fare,
        notes=payload.notes,
        phone_number=payload.phone_number,
        status=payload.status,
    )
    db.add(booking)
    await db.commit()
    await db.refresh(booking)

    sio = getattr(request.app.state, "sio", None)
    if sio is not None:
        await sio.emit("booking_created", BookingOut.model_validate(booking).model_dump(mode="json"))

    return booking


@router.get("/clients/{name}/history", response_model=ClientHistoryResponse)
async def get_client_history(name: str, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Booking)
        .where(Booking.client_name.ilike(_escape_like(name), escape="\\"), Booking.status != "cancelled")
        .order_by(Booking.trip_date.desc(), Booking.trip_time.desc())
    )
    result = await db.execute(stmt)
    trips = result.scalars().all()

    total_earned = sum((b.fare for b in trips if b.status == "completed"), Decimal("0"))

    return ClientHistoryResponse(
        client_name=name,
        trips=trips,
        total_earned=total_earned,
        total_trips=len(trips),
    )
