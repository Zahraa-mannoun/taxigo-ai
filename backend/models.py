"""
ORM model and Pydantic (v2) schemas for the bookings domain.
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, Date, DateTime, Numeric, Text, Time, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base

BookingStatus = Literal["confirmed", "in_progress", "completed", "cancelled"]
Language = Literal["en", "ar", "fr"]

FRIENDLY_FIELD_NAMES: dict[str, dict[str, str]] = {
    "client_name": {"en": "client's name", "ar": "اسم الزبون", "fr": "le nom du client"},
    "pickup": {"en": "pickup location", "ar": "مكان الانطلاق", "fr": "le lieu de prise en charge"},
    "dropoff": {"en": "drop-off location", "ar": "مكان الوصول", "fr": "le lieu de destination"},
    "trip_date": {"en": "trip date", "ar": "تاريخ الرحلة", "fr": "la date du trajet"},
    "trip_time": {"en": "trip time", "ar": "وقت الرحلة", "fr": "l'heure du trajet"},
    "fare": {"en": "fare", "ar": "الأجرة", "fr": "le tarif"},
    "new_status": {"en": "new status", "ar": "الحالة الجديدة", "fr": "le nouveau statut"},
}


# --------------------------------------------------------------------------
# ORM model
# --------------------------------------------------------------------------
class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    client_name: Mapped[str] = mapped_column(Text, nullable=False)
    pickup: Mapped[str] = mapped_column(Text, nullable=False)
    dropoff: Mapped[str] = mapped_column(Text, nullable=False)
    trip_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    trip_time: Mapped[dt.time] = mapped_column(Time, nullable=False)
    fare: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="confirmed")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reminded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


# --------------------------------------------------------------------------
# Pydantic schemas
# --------------------------------------------------------------------------
class BookingCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    client_name: str
    pickup: str
    dropoff: str
    trip_date: dt.date
    trip_time: dt.time
    fare: Decimal = Field(default=Decimal("0"))
    notes: str = ""
    status: BookingStatus = "confirmed"


class BookingUpdate(BaseModel):
    client_name: Optional[str] = None
    pickup: Optional[str] = None
    dropoff: Optional[str] = None
    trip_date: Optional[dt.date] = None
    trip_time: Optional[dt.time] = None
    fare: Optional[Decimal] = None
    notes: Optional[str] = None
    status: Optional[BookingStatus] = None


class StatusUpdate(BaseModel):
    status: BookingStatus


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_name: str
    pickup: str
    dropoff: str
    trip_date: dt.date
    trip_time: dt.time
    fare: Decimal
    status: BookingStatus
    notes: str
    reminded: bool
    created_at: dt.datetime


class ChatRequest(BaseModel):
    message: str
    conversation_history: list[dict] = Field(default_factory=list)
    lang: Language = "en"


class ChatResponse(BaseModel):
    reply: str
    action: str = "chat"
    booking: Optional[BookingOut] = None
    bookings: Optional[list[BookingOut]] = None
    conflict: Optional[dict] = None
    summary: Optional[dict] = None
    refresh: bool = False


class ForceBookRequest(BookingCreate):
    pass


class ClientHistoryResponse(BaseModel):
    client_name: str
    trips: list[BookingOut]
    total_earned: Decimal
    total_trips: int


class WeeklyAnalyticsDay(BaseModel):
    date: dt.date
    earned: Decimal
    projected: Decimal
    trip_count: int


class WeeklyAnalyticsResponse(BaseModel):
    days: list[WeeklyAnalyticsDay]
    total_earned: Decimal
    total_projected: Decimal
    total_trips: int


class ExportRequest(BaseModel):
    scope: Literal["today", "week", "all"] = "today"
