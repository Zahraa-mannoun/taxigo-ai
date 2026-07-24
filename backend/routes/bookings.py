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

INVALID_STATUS_DETAIL = {
    "en": "That status is not valid.",
    "ar": "هاي الحالة مش صحيحة.",
    "fr": "Ce statut n'est pas valide.",
}


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
    """
    booking = Booking(
        client_name=payload.client_name,
        pickup=payload.pickup,
        dropoff=payload.dropoff,
        trip_date=payload.trip_date,
        trip_time=payload.trip_time,
        fare=payload.fare,
        notes=payload.notes,
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
        .where(Booking.client_name.ilike(name), Booking.status != "cancelled")
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
