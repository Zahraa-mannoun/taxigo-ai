"""
AI dispatch agent built on Groq (llama-3.3-70b-versatile).

The model's only job is CLASSIFICATION + EXTRACTION: given a free-text
message (English, Lebanese Arabic, French or a mix), decide which of the
8 tools applies and pull out structured arguments (resolving relative
dates/times against "today"). All business logic -- validation, conflict
detection, database writes, and the actual confirmation wording shown to
the user -- is handled deterministically in Python via the TEMPLATES
below. This keeps user-facing text reliable/bilingual and prevents the
model from inventing prices, times or confirmations.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from groq import AsyncGroq, BadRequestError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Booking, BookingOut, FRIENDLY_FIELD_NAMES
from services.conflict_detector import CONFLICT_WINDOW_MINUTES, find_conflict
from timezone_utils import now_beirut, today_beirut

logger = logging.getLogger("taxigo.ai_agent")

# --------------------------------------------------------------------------
# Location normalization (Fix 7 safety net)
#
# The system prompt instructs the model to always extract pickup/dropoff in
# English, but this is a plain instruction-following task (not tool
# selection), and testing showed llama-3.3-70b-versatile does not reliably
# obey it -- it will happily store "بيروت" verbatim when the driver typed
# Arabic. Rather than depend on prompt compliance alone, canonicalize
# whatever the model extracts against the same Lebanese place-name
# dictionary the frontend uses (mirrored here), so the stored value is
# deterministically English regardless of what the model actually returned.
# --------------------------------------------------------------------------
LOCATION_EN_CANONICAL: dict[str, str] = {
    "beirut": "Beirut", "tripoli": "Tripoli", "saida": "Saida", "sidon": "Saida",
    "tyre": "Tyre", "sour": "Tyre", "jounieh": "Jounieh", "zahle": "Zahle",
    "baalbek": "Baalbek", "nabatieh": "Nabatieh", "aley": "Aley", "byblos": "Byblos",
    "jbeil": "Byblos", "batroun": "Batroun", "chouf": "Chouf", "metn": "Metn",
    "kesrouan": "Kesrouan", "akkar": "Akkar", "hamra": "Hamra", "downtown": "Downtown",
    "verdun": "Verdun", "achrafieh": "Achrafieh", "ashrafieh": "Achrafieh",
    "mar mikhael": "Mar Mikhael", "gemmayzeh": "Gemmayzeh", "raouche": "Raouche",
    "corniche": "Corniche", "sodeco": "Sodeco", "badaro": "Badaro", "sanayeh": "Sanayeh",
    "ras beirut": "Ras Beirut", "dekwaneh": "Dekwaneh", "sin el fil": "Sin El Fil",
    "bourj hammoud": "Bourj Hammoud", "jdeideh": "Jdeideh", "cola": "Cola",
    "tayouneh": "Tayouneh", "chiyah": "Chiyah", "ghobeiry": "Ghobeiry",
    "haret hreik": "Haret Hreik", "dahiyeh": "Dahiyeh", "airport": "Airport",
    "rafic hariri airport": "Rafic Hariri Airport", "port": "Port",
    "port of beirut": "Port of Beirut", "hospital": "Hospital", "aub": "AUB",
    "lau": "LAU", "usj": "USJ", "lebanese university": "Lebanese University",
    "mall": "Mall", "city centre": "City Centre", "dbayeh": "Dbayeh",
    "antelias": "Antelias", "zalka": "Zalka", "naccache": "Naccache", "annar": "Annar",
}

_LOCATIONS_FOREIGN: dict[str, dict[str, str]] = {
    "beirut": {"ar": "بيروت", "fr": "Beyrouth"},
    "tripoli": {"ar": "طرابلس", "fr": "Tripoli"},
    "saida": {"ar": "صيدا", "fr": "Saïda"},
    "sidon": {"ar": "صيدا", "fr": "Saïda"},
    "tyre": {"ar": "صور", "fr": "Tyr"},
    "sour": {"ar": "صور", "fr": "Tyr"},
    "jounieh": {"ar": "جونيه", "fr": "Jounieh"},
    "zahle": {"ar": "زحلة", "fr": "Zahlé"},
    "baalbek": {"ar": "بعلبك", "fr": "Baalbek"},
    "nabatieh": {"ar": "النبطية", "fr": "Nabatieh"},
    "aley": {"ar": "عاليه", "fr": "Aley"},
    "byblos": {"ar": "جبيل", "fr": "Byblos"},
    "jbeil": {"ar": "جبيل", "fr": "Byblos"},
    "batroun": {"ar": "البترون", "fr": "Batroun"},
    "chouf": {"ar": "الشوف", "fr": "Chouf"},
    "metn": {"ar": "المتن", "fr": "Metn"},
    "kesrouan": {"ar": "كسروان", "fr": "Kesrouan"},
    "akkar": {"ar": "عكار", "fr": "Akkar"},
    "hamra": {"ar": "الحمرا", "fr": "Hamra"},
    "downtown": {"ar": "وسط بيروت", "fr": "Centre-ville"},
    "verdun": {"ar": "فردان", "fr": "Verdun"},
    "achrafieh": {"ar": "الأشرفية", "fr": "Achrafieh"},
    "ashrafieh": {"ar": "الأشرفية", "fr": "Achrafieh"},
    "mar mikhael": {"ar": "مار مخايل", "fr": "Mar Mikhael"},
    "gemmayzeh": {"ar": "الجميزة", "fr": "Gemmayzeh"},
    "raouche": {"ar": "الروشة", "fr": "Raouché"},
    "corniche": {"ar": "الكورنيش", "fr": "Corniche"},
    "sodeco": {"ar": "سوديكو", "fr": "Sodeco"},
    "badaro": {"ar": "بدارو", "fr": "Badaro"},
    "sanayeh": {"ar": "الصنايع", "fr": "Sanayeh"},
    "ras beirut": {"ar": "رأس بيروت", "fr": "Ras Beyrouth"},
    "dekwaneh": {"ar": "الدكوانة", "fr": "Dekwaneh"},
    "sin el fil": {"ar": "سن الفيل", "fr": "Sin el Fil"},
    "bourj hammoud": {"ar": "برج حمود", "fr": "Bourj Hammoud"},
    "jdeideh": {"ar": "الجديدة", "fr": "Jdeideh"},
    "cola": {"ar": "كولا", "fr": "Cola"},
    "tayouneh": {"ar": "الطيونة", "fr": "Tayouneh"},
    "chiyah": {"ar": "الشياح", "fr": "Chiyah"},
    "ghobeiry": {"ar": "الغبيري", "fr": "Ghobeiry"},
    "haret hreik": {"ar": "حارة حريك", "fr": "Haret Hreik"},
    "dahiyeh": {"ar": "الضاحية", "fr": "Dahiyeh"},
    "airport": {"ar": "المطار", "fr": "Aéroport"},
    "rafic hariri airport": {"ar": "مطار رفيق الحريري", "fr": "Aéroport Rafic Hariri"},
    "port": {"ar": "المرفأ", "fr": "Port"},
    "port of beirut": {"ar": "مرفأ بيروت", "fr": "Port de Beyrouth"},
    "hospital": {"ar": "المستشفى", "fr": "Hôpital"},
    "aub": {"ar": "الجامعة الأمريكية", "fr": "AUB"},
    "lau": {"ar": "الجامعة اللبنانية الأمريكية", "fr": "LAU"},
    "usj": {"ar": "جامعة القديس يوسف", "fr": "USJ"},
    "lebanese university": {"ar": "الجامعة اللبنانية", "fr": "Université Libanaise"},
    "mall": {"ar": "المول", "fr": "Centre commercial"},
    "city centre": {"ar": "سيتي سنتر", "fr": "City Centre"},
    "dbayeh": {"ar": "ضبيه", "fr": "Dbayeh"},
    "antelias": {"ar": "أنطلياس", "fr": "Antelias"},
    "zalka": {"ar": "الزلقا", "fr": "Zalka"},
    "naccache": {"ar": "النقاش", "fr": "Naccache"},
    "annar": {"ar": "النار", "fr": "Annar"},
}

_FOREIGN_TO_KEY: dict[str, str] = {}
for _key, _translations in _LOCATIONS_FOREIGN.items():
    for _foreign_name in _translations.values():
        _FOREIGN_TO_KEY.setdefault(_foreign_name.lower(), _key)

_ARABIC_SCRIPT_RE = re.compile(r"[؀-ۿ]")


def normalize_location(text: Optional[str]) -> Optional[str]:
    """Best-effort canonicalization of a pickup/dropoff string to English.
    English input (or anything not in the dictionary) passes through
    unchanged -- this only rewrites recognized Arabic/French place names.

    Many French entries are spelled identically to their English key (e.g.
    "port" -> fr "Port", "hamra" -> fr "Hamra"). The substring fallback below
    is only meant to catch an Arabic place name embedded in a longer string
    the model returned -- it must NOT run on plain Latin/English text, or it
    would wrongly match "port" inside "Port of Beirut" (already-correct
    English) and mangle it down to just "Port".
    """
    if not text:
        return text
    lower = text.strip().lower()
    key = _FOREIGN_TO_KEY.get(lower)
    if key:
        return LOCATION_EN_CANONICAL[key]
    if _ARABIC_SCRIPT_RE.search(text):
        for foreign_name, matched_key in _FOREIGN_TO_KEY.items():
            if re.search(rf"\b{re.escape(foreign_name)}\b", lower):
                return LOCATION_EN_CANONICAL[matched_key]
    return text

# --------------------------------------------------------------------------
# Simple-greeting short-circuit
#
# llama-3.3-70b-versatile is unreliable at tool calling for trivial
# conversational input -- a bare "صباح النور" (or "hi"/"bonjour") makes it
# emit its own native <function=chat>...</function> tag syntax instead of a
# clean structured tool call, which fails validation on both the initial
# request AND the temperature-nudged retry below, surfacing an error to the
# driver for something as simple as a greeting. Since these messages never
# need tool selection anyway, skip the Groq call entirely and answer from
# TEMPLATES -- this also avoids burning API quota on a non-task message.
# --------------------------------------------------------------------------
SIMPLE_GREETINGS = [
    "صباح الخير", "صباح النور", "مساء الخير", "مساء النور", "هلا", "مرحبا",
    "hi", "hello", "hey", "good morning", "good evening",
    "bonjour", "salut", "bonsoir",
]


def is_simple_greeting(message: str) -> bool:
    normalized = message.strip().lower()
    return len(normalized) < 20 and any(g in normalized for g in SIMPLE_GREETINGS)


# --------------------------------------------------------------------------
# Fallback parser for Groq's native <function=...> tag syntax
#
# The greeting pre-check above only catches short literal greetings on the
# way IN. It can't help when the model itself decides mid-conversation to
# "call" the `chat` pseudo-tool -- `chat` is deliberately NOT a real entry in
# TOOLS (see system prompt item 8: "Do NOT call a tool; just reply naturally
# in your message content"), so there is no valid structured call the model
# could ever produce for it. When it tries anyway, Groq rejects the
# malformed call with a "tool_use_failed" BadRequestError whose
# `failed_generation` field holds the model's raw, unparsed output, e.g.
# '<function=chat>Good morning, have a great day</function>'. Retrying (as
# done for genuine extraction mistakes on real tools) just reproduces the
# same mistake, so instead recover the human-readable text directly from
# that field and treat it as a normal chat reply.
# --------------------------------------------------------------------------
_FALLBACK_CHAT_TAG_RE = re.compile(r"<function=chat>(.*?)</function>", re.DOTALL)


def extract_fallback_chat_text(error_body: Any) -> Optional[str]:
    """Recover the reply text from a Groq tool_use_failed error caused by the
    model emitting its native <function=chat>text</function> syntax.

    Returns None if `error_body` doesn't match this specific failure shape
    (e.g. a genuine tool_use_failed on a real tool like extract_booking,
    which should still go through the normal retry path instead).
    """
    if isinstance(error_body, dict):
        failed_generation = error_body.get("error", {}).get("failed_generation")
    else:
        failed_generation = error_body
    if not isinstance(failed_generation, str):
        return None
    match = _FALLBACK_CHAT_TAG_RE.search(failed_generation)
    if not match:
        return None
    return match.group(1).strip()


GROQ_MODEL = "llama-3.3-70b-versatile"

_client: Optional[AsyncGroq] = None


def get_client() -> AsyncGroq:
    """Lazily construct the Groq async client so import never fails without a key."""
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not configured")
        _client = AsyncGroq(api_key=api_key)
    return _client


_AI_HEALTH_CACHE_SECONDS = 300
_ai_health_cache: dict[str, Any] = {"result": None, "checked_at": None}


async def check_ai_connectivity() -> bool:
    """Lightweight check used by /health -- confirms the API key works.

    Cached for 5 minutes: this makes a REAL Groq API call, and /health may be
    polled frequently by uptime monitors / Railway's own healthcheck. Without
    caching, health checks alone can burn through the free-tier daily quota
    (this happened repeatedly during development).
    """
    now = now_beirut()
    cached_at = _ai_health_cache["checked_at"]
    if cached_at is not None and (now - cached_at).total_seconds() < _AI_HEALTH_CACHE_SECONDS:
        return _ai_health_cache["result"]

    try:
        client = get_client()
        await client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
        )
        result = True
    except Exception:
        result = False

    _ai_health_cache["result"] = result
    _ai_health_cache["checked_at"] = now
    return result


# --------------------------------------------------------------------------
# Tool (function) schemas exposed to the model
# --------------------------------------------------------------------------
TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "extract_booking",
            "description": "Create a brand new trip/booking for a client.",
            "parameters": {
                "type": "object",
                "properties": {
                    "client_name": {"type": "string", "description": "Name of the client/passenger."},
                    "pickup": {"type": "string", "description": "Pickup location."},
                    "dropoff": {"type": "string", "description": "Drop-off / destination location."},
                    "trip_date": {"type": "string", "description": "Trip date resolved to YYYY-MM-DD."},
                    "trip_time": {"type": "string", "description": "Trip time resolved to 24h HH:MM."},
                    "fare": {
                        "type": ["number", "string"],
                        "description": "Agreed fare/fee amount, if mentioned. Plain number, e.g. 20 -- but a numeric string is also accepted and coerced.",
                    },
                    "notes": {"type": "string", "description": "Any extra notes about the trip."},
                },
                "required": ["client_name", "pickup", "dropoff", "trip_date", "trip_time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_booking",
            "description": "Edit an existing trip's details (pickup, dropoff, date, time, fare or notes).",
            "parameters": {
                "type": "object",
                "properties": {
                    "client_name": {"type": "string", "description": "Name of the client whose trip is being edited."},
                    "existing_trip_date": {"type": "string", "description": "Date (YYYY-MM-DD) of the trip to edit, if known, to disambiguate multiple trips."},
                    "pickup": {"type": "string", "description": "New pickup location."},
                    "dropoff": {"type": "string", "description": "New drop-off location."},
                    "trip_date": {"type": "string", "description": "New trip date (YYYY-MM-DD)."},
                    "trip_time": {"type": "string", "description": "New trip time (24h HH:MM)."},
                    "fare": {
                        "type": ["number", "string"],
                        "description": "New fare/fee amount. Plain number, e.g. 20 -- but a numeric string is also accepted and coerced.",
                    },
                    "notes": {"type": "string", "description": "New notes."},
                },
                "required": ["client_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_booking",
            "description": "Cancel an existing trip for a client.",
            "parameters": {
                "type": "object",
                "properties": {
                    "client_name": {"type": "string", "description": "Name of the client whose trip is being cancelled."},
                    "trip_date": {"type": "string", "description": "Date (YYYY-MM-DD) of the trip to cancel, if known."},
                },
                "required": ["client_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_status",
            "description": "Change the status of a trip (confirmed, in_progress or completed).",
            "parameters": {
                "type": "object",
                "properties": {
                    "client_name": {"type": "string", "description": "Name of the client."},
                    "new_status": {"type": "string", "enum": ["confirmed", "in_progress", "completed"]},
                    "trip_date": {"type": "string", "description": "Date (YYYY-MM-DD) of the trip, if known."},
                },
                "required": ["client_name", "new_status"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "repeat_booking",
            "description": "Clone the client's most recent trip onto a new date/time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "client_name": {"type": "string", "description": "Name of the client."},
                    "new_date": {"type": "string", "description": "New trip date resolved to YYYY-MM-DD."},
                    "new_time": {"type": "string", "description": "New trip time resolved to 24h HH:MM, if mentioned."},
                },
                "required": ["client_name", "new_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_bookings",
            "description": "Show the upcoming schedule / trip list.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filter": {
                        "type": "string",
                        "enum": ["today", "tomorrow", "week", "all"],
                        "description": "Always include this. Use 'all' if the driver didn't specify a date range.",
                    },
                    "client_name": {"type": "string", "description": "Only trips for this client, if mentioned."},
                },
                "required": ["filter"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_summary",
            "description": "Give the driver a summary of trips and earnings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "enum": ["today", "week", "all"],
                        "description": "Always include this. Use 'today' if the driver didn't specify a period.",
                    },
                },
                "required": ["period"],
            },
        },
    },
]


# --------------------------------------------------------------------------
# System prompt
# --------------------------------------------------------------------------
def build_system_prompt(lang: str) -> str:
    today = today_beirut()
    tomorrow = today + dt.timedelta(days=1)
    weekday = today.strftime("%A")

    return f"""You are the dispatch assistant inside TaxiGo AI, a scheduling app used by a
single taxi driver in Lebanon. You read messages from the driver -- written in
English, Lebanese Arabic (script or Arabizi/romanized), French, or a mix of
these -- and decide which ONE tool to call to carry out the driver's intent.

TODAY'S DATE IS: {today.isoformat()} ({weekday}). Tomorrow is {tomorrow.isoformat()}.
Always resolve relative dates/times against this fixed "today" -- never ask
the driver what today's date is.

## The 8 things you can recognize
1. extract_booking -- add a brand new trip.
   Lebanese trigger words/phrases: "بدي احجز", "احجزلي", "زبون جديد", "ضيفلي حجز",
   "في عندي طلعة", "بدي زبط رحلة لـ", "عندي كليان جديد", "خدني احجز" and Arabizi like
   "biddi ehjez", "3andi trip jdid", "zbotli booking". French: "réserver", "ajouter",
   "nouveau trajet", "prendre", "conduire" (combined with "demain"/"aujourd'hui").
2. update_booking -- change details of an existing trip (pickup/dropoff/date/time/fare/notes).
   Triggers: "بدل الموعد", "غيرلي الوقت", "عدلّي الحجز", "بدي بدل مكان التحميل",
   "بدلّي الأجرة", "ghayerli el waet", "3adelli el booking". French: "modifier",
   "changer", "mettre à jour", "corriger".
3. cancel_booking -- cancel a trip entirely.
   Triggers: "الغي الحجز", "بطل الرحلة", "ما عاد في داعي للحجز", "cancel el trip",
   "شطبلي الرحلة". French: "annuler", "supprimer", "effacer".
4. update_status -- mark a trip in_progress/completed (never used for cancelling).
   Triggers: "الزبون طلع", "عم روح عالزبون", "وصلت", "خلصت الرحلة", "خلص التوصيلة",
   "sar b tari2", "khalasit el trip", "picked up the client". French: "commencé",
   "démarré", "terminé", "livré", "en route".
5. repeat_booking -- clone the client's last trip onto a new date.
   Triggers: "نفس الرحلة يلي فاتت", "كرر الحجز", "زي المرة اللي فاتت بس بكرا",
   "same trip as last time", "rep33tili nafs el booking". French: "répéter",
   "même trajet", "encore", "de nouveau".
6. list_bookings -- show the schedule.
   Triggers: "شو في اليوم", "وريني الحجوزات", "شو عندي رحلات بكرا", "shu 3andi l youm",
   "warrini el schedule". French: "voir", "afficher", "planning", "horaire",
   "mes réservations".
7. get_summary -- daily/weekly earnings summary.
   Triggers: "قديش ربحت اليوم", "كم كسبت", "ملخص اليوم", "addeh rbe7et",
   "how much did I make". French: "résumé", "combien", "gains", "aujourd'hui",
   "bilan".
8. chat -- anything else (greetings, small talk, questions, in any of the three
   languages including French). Do NOT call a tool; just reply naturally in your
   message content.

## Synonyms you must understand
- "fee", "fare", "fees", "أجرة", "التسعيرة", "السعر", "cost" all refer to the `fare` field.
- The `fare` field must always be a plain number without currency symbols or
  quotes, e.g. 20 -- not "20" or "$20".
- "بكرا", "baacher", "bukra", "tomorrow" -> next calendar day.
- "هلق", "today", "aujourd'hui" -> today's date above.
- Specific dates (e.g. "August 3rd", "3/8") should be resolved to YYYY-MM-DD
  using today's date to infer the correct year.

## Time parsing
- Accept both 12h ("3pm", "3:30 pm") and 24h ("15:00", "15:30") formats.
- Always output `trip_time` / `new_time` as 24-hour "HH:MM" in tool arguments.

## Location storage rule
- Always save pickup and dropoff locations in English in the database, even if
  the driver speaks in Arabic or French. The frontend will translate them for
  display. Common mappings: الحمرا=Hamra, المطار=Airport, بيروت=Beirut,
  طرابلس=Tripoli, صيدا=Saida, جونيه=Jounieh, الأشرفية=Achrafieh,
  وسط بيروت=Downtown, المرفأ=Port

## Conflict detection (handled automatically, not by you)
- The backend automatically checks whether a new or changed trip falls within
  {CONFLICT_WINDOW_MINUTES} minutes of another trip on the same date. You do NOT
  need to ask about conflicts or check schedules yourself -- just extract the
  fields the driver gave you and call the right tool. The system will warn the
  driver itself if there is a clash.

## Missing information
- If a required field for the tool is missing from the message (e.g. no pickup
  location was given), do NOT call the tool -- instead reply in your message
  content asking ONLY for what's missing, in friendly plain language. NEVER
  mention internal field names like "client_name" or "trip_date" -- say things
  like "what's the client's name?" or "when is the trip?" instead.

## Language rule
- You MUST respond (any free-text `chat` reply) in this language: {lang}
  ("en" = English, "ar" = Lebanese-flavoured Modern Standard Arabic, "fr" = French).
- Keep replies short, warm, and professional -- this is a working tool for a
  busy driver, not a chatbot to impress.
"""


# --------------------------------------------------------------------------
# Bilingual/trilingual response templates (deterministic, not model-generated)
# --------------------------------------------------------------------------
TEMPLATES: dict[str, dict[str, str]] = {
    "greeting": {
        "en": "Hello! How can I help you today?",
        "ar": "أهلاً وسهلاً! كيف فيني ساعدك اليوم؟",
        "fr": "Bonjour ! Comment puis-je vous aider aujourd'hui ?",
    },
    "ai_error": {
        "en": "Sorry, I'm having trouble reaching the AI service right now. Please try again in a moment.",
        "ar": "عذرًا، في مشكلة بالوصول لخدمة الذكاء الاصطناعي حاليًا. جرب كمان شوي.",
        "fr": "Désolé, je n'arrive pas à contacter le service d'IA pour le moment. Réessayez dans un instant.",
    },
    "generic_error": {
        "en": "Something went wrong on my end. Please try again.",
        "ar": "صار في خطأ من عندي. جرب مرة تانية.",
        "fr": "Une erreur s'est produite. Merci de réessayer.",
    },
    "invalid_datetime": {
        "en": "I couldn't understand that date or time -- could you rephrase it?",
        "ar": "ما فهمت التاريخ أو الوقت منيح -- فيك تعيدها بطريقة تانية؟",
        "fr": "Je n'ai pas compris cette date ou cette heure -- pouvez-vous reformuler ?",
    },
    "missing_info": {
        "en": "Just need a bit more info -- can you tell me {fields}?",
        "ar": "بس ناقصني معلومة بسيطة -- فيك تقلّي {fields}؟",
        "fr": "Il me manque juste quelques informations -- pouvez-vous me donner {fields} ?",
    },
    "no_booking_found": {
        "en": "I couldn't find a trip for {client_name} to work with.",
        "ar": "ما لقيت رحلة لـ {client_name} لأشتغل عليها.",
        "fr": "Je n'ai trouvé aucun trajet pour {client_name}.",
    },
    "booking_created": {
        "en": "Booked! {client_name}: {pickup} → {dropoff} on {date} at {time}.",
        "ar": "تم الحجز! {client_name}: من {pickup} إلى {dropoff} بتاريخ {date} الساعة {time}.",
        "fr": "Réservé ! {client_name} : {pickup} → {dropoff} le {date} à {time}.",
    },
    "booking_updated": {
        "en": "Updated {client_name}'s trip: {pickup} → {dropoff} on {date} at {time}.",
        "ar": "تم تعديل رحلة {client_name}: من {pickup} إلى {dropoff} بتاريخ {date} الساعة {time}.",
        "fr": "Trajet de {client_name} mis à jour : {pickup} → {dropoff} le {date} à {time}.",
    },
    "booking_cancelled": {
        "en": "Cancelled {client_name}'s trip on {date} at {time}.",
        "ar": "تم إلغاء رحلة {client_name} بتاريخ {date} الساعة {time}.",
        "fr": "Trajet de {client_name} annulé le {date} à {time}.",
    },
    "status_updated": {
        "en": "{client_name}'s trip is now marked as {status}.",
        "ar": "تم تحديث حالة رحلة {client_name} إلى {status}.",
        "fr": "Le trajet de {client_name} est maintenant marqué comme {status}.",
    },
    "booking_repeated": {
        "en": "Repeated! {client_name}: {pickup} → {dropoff} on {date} at {time}.",
        "ar": "تم تكرار الحجز! {client_name}: من {pickup} إلى {dropoff} بتاريخ {date} الساعة {time}.",
        "fr": "Trajet dupliqué ! {client_name} : {pickup} → {dropoff} le {date} à {time}.",
    },
    "conflict_warning": {
        "en": "⚠️ That clashes with {other_client}'s trip at {other_time} on {date} (within {window} min). Force-book anyway, or pick another time.",
        "ar": "⚠️ في تعارض مع رحلة {other_client} الساعة {other_time} بتاريخ {date} (أقل من {window} دقيقة). فيك تأكد الحجز رغم هيك أو تختار وقت تاني.",
        "fr": "⚠️ Cela chevauche le trajet de {other_client} à {other_time} le {date} (moins de {window} min d'écart). Forcez la réservation ou choisissez un autre horaire.",
    },
    "list_bookings_summary": {
        "en": "You have {count} trip(s) scheduled.",
        "ar": "عندك {count} رحلة/رحلات مجدولة.",
        "fr": "Vous avez {count} trajet(s) programmé(s).",
    },
    "summary_result": {
        "en": "{period}: earned {earned} from completed trips, projected {projected} across {count} trip(s).",
        "ar": "{period}: ربحت {earned} من الرحلات المكتملة، والمتوقع {projected} من أصل {count} رحلة.",
        "fr": "{period} : {earned} gagnés sur les trajets terminés, {projected} prévus sur {count} trajet(s).",
    },
}

# Must match frontend/js/translations.js's statusInProgress/statusCancelled
# exactly -- these words appear in both chat replies and UI badges, and
# previously drifted out of sync (ar "قيد التنفيذ"/"ملغاة" vs frontend's
# "جارية"/"ملغية").
STATUS_LABELS = {
    "confirmed": {"en": "confirmed", "ar": "مؤكدة", "fr": "confirmé"},
    "in_progress": {"en": "in progress", "ar": "جارية", "fr": "en cours"},
    "completed": {"en": "completed", "ar": "مكتملة", "fr": "terminé"},
    "cancelled": {"en": "cancelled", "ar": "ملغية", "fr": "annulé"},
}

PERIOD_LABELS = {
    "today": {"en": "Today", "ar": "اليوم", "fr": "Aujourd'hui"},
    "week": {"en": "This week", "ar": "هالأسبوع", "fr": "Cette semaine"},
    "all": {"en": "All time", "ar": "من البداية", "fr": "Depuis le début"},
}

_FIELD_JOINERS = {"en": " and ", "ar": " و", "fr": " et "}


def t(key: str, lang: str, **kwargs: Any) -> str:
    text = TEMPLATES[key].get(lang, TEMPLATES[key]["en"])
    return text.format(**kwargs)


def format_time_12h(value: dt.time) -> str:
    return value.strftime("%I:%M %p").lstrip("0")


# Mirrors frontend/js/translations.js's formatDate/formatTime/formatMoney so
# chat replies read naturally in AR/FR instead of embedding a raw ISO date
# and English AM/PM inside an otherwise-Arabic/French sentence. EN output is
# unchanged from before (still ISO date + format_time_12h).
_AR_MONTHS = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
_FR_MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
_AR_PERIOD = {"AM": "ص", "PM": "م"}


def format_date_localized(value: dt.date, lang: str) -> str:
    if lang == "ar":
        return f"{value.day} {_AR_MONTHS[value.month - 1]} {value.year}"
    if lang == "fr":
        return f"{value.day} {_FR_MONTHS[value.month - 1]} {value.year}"
    return value.isoformat()  # en: unchanged


def format_time_localized(value: dt.time, lang: str) -> str:
    if lang == "fr":
        return value.strftime("%H:%M")
    if lang == "ar":
        period = _AR_PERIOD["PM"] if value.hour >= 12 else _AR_PERIOD["AM"]
        hour12 = value.hour % 12 or 12
        return f"{hour12}:{value.minute:02d} {period}"
    return format_time_12h(value)  # en: unchanged


def format_money_localized(value: Decimal, lang: str) -> str:
    fixed = f"{value:.2f}"
    if lang == "fr":
        return f"{fixed.replace('.', ',')} $"
    if lang == "ar":
        return f"{fixed}$"
    return f"${fixed}"  # en: unchanged


def missing_fields_message(missing: list[str], lang: str) -> str:
    names = [FRIENDLY_FIELD_NAMES.get(f, {}).get(lang, f) for f in missing]
    joiner = _FIELD_JOINERS.get(lang, " and ")
    fields = joiner.join(names) if len(names) < 3 else ", ".join(names[:-1]) + joiner + names[-1]
    return t("missing_info", lang, fields=fields)


def _parse_date(value: Any) -> Optional[dt.date]:
    if not value:
        return None
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _parse_time(value: Any) -> Optional[dt.time]:
    if not value:
        return None
    try:
        return dt.time.fromisoformat(str(value)[:8])
    except ValueError:
        return None


def _parse_fare(value: Any) -> Decimal:
    """Coerce a fare value to Decimal.

    Safety net for extract_booking/update_booking: even with the schema now
    accepting both number and string, the model may still hand back a fare
    string with currency symbols/commas (e.g. "$20", "20,000") rather than a
    bare number, so strip those before parsing instead of just trusting the
    prompt instruction.
    """
    if value is None or value == "":
        return Decimal("0")
    if isinstance(value, str):
        value = value.replace("$", "").replace(",", "").strip()
        if not value:
            return Decimal("0")
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return Decimal("0")


def _escape_like(value: str) -> str:
    """Escape SQL LIKE/ILIKE wildcards so a literal '%' or '_' in user input
    (e.g. a client name) can't be misinterpreted as a pattern wildcard."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def _find_client_booking(
    db: AsyncSession, client_name: str, trip_date: Optional[dt.date] = None
) -> Optional[Booking]:
    stmt = select(Booking).where(
        Booking.client_name.ilike(_escape_like(client_name.strip()), escape="\\"),
        Booking.status != "cancelled",
    )
    if trip_date is not None:
        stmt = stmt.where(Booking.trip_date == trip_date)
    stmt = stmt.order_by(Booking.trip_date.desc(), Booking.trip_time.desc())

    result = await db.execute(stmt)
    return result.scalars().first()


async def _emit(sio, event: str, data: dict) -> None:
    if sio is not None:
        await sio.emit(event, data)


# --------------------------------------------------------------------------
# Tool handlers
# --------------------------------------------------------------------------
async def _handle_extract_booking(db: AsyncSession, sio, args: dict, lang: str) -> dict:
    required = ["client_name", "pickup", "dropoff", "trip_date", "trip_time"]
    missing = [f for f in required if not args.get(f)]
    if missing:
        return {"reply": missing_fields_message(missing, lang), "action": "missing_info"}

    # Canonicalize to English regardless of what the model actually returned
    # (see normalize_location() docstring -- prompt compliance alone isn't reliable here).
    args["pickup"] = normalize_location(args["pickup"])
    args["dropoff"] = normalize_location(args["dropoff"])

    trip_date = _parse_date(args.get("trip_date"))
    trip_time = _parse_time(args.get("trip_time"))
    if trip_date is None or trip_time is None:
        return {"reply": t("invalid_datetime", lang), "action": "error"}

    conflict = await find_conflict(db, trip_date, trip_time)
    if conflict is not None:
        pending = {
            "client_name": args["client_name"],
            "pickup": args["pickup"],
            "dropoff": args["dropoff"],
            "trip_date": trip_date.isoformat(),
            "trip_time": trip_time.isoformat(),
            "fare": str(_parse_fare(args.get("fare"))),
            "notes": args.get("notes") or "",
        }
        reply = t(
            "conflict_warning",
            lang,
            other_client=conflict.client_name,
            other_time=format_time_localized(conflict.trip_time, lang),
            date=format_date_localized(trip_date, lang),
            window=CONFLICT_WINDOW_MINUTES,
        )
        return {
            "reply": reply,
            "action": "conflict",
            "conflict": {
                "conflicting_booking": BookingOut.model_validate(conflict).model_dump(mode="json"),
                "pending_booking": pending,
            },
        }

    booking = Booking(
        client_name=args["client_name"],
        pickup=args["pickup"],
        dropoff=args["dropoff"],
        trip_date=trip_date,
        trip_time=trip_time,
        fare=_parse_fare(args.get("fare")),
        notes=args.get("notes") or "",
        status="confirmed",
    )
    db.add(booking)
    await db.commit()
    await db.refresh(booking)

    booking_out = BookingOut.model_validate(booking).model_dump(mode="json")
    await _emit(sio, "booking_created", booking_out)

    reply = t(
        "booking_created",
        lang,
        client_name=booking.client_name,
        pickup=booking.pickup,
        dropoff=booking.dropoff,
        date=format_date_localized(booking.trip_date, lang),
        time=format_time_localized(booking.trip_time, lang),
    )
    return {"reply": reply, "action": "booking_created", "booking": booking_out, "refresh": True}


async def _handle_update_booking(db: AsyncSession, sio, args: dict, lang: str) -> dict:
    client_name = args.get("client_name")
    if not client_name:
        return {"reply": missing_fields_message(["client_name"], lang), "action": "missing_info"}

    existing_date = _parse_date(args.get("existing_trip_date"))
    booking = await _find_client_booking(db, client_name, existing_date)
    if booking is None:
        return {"reply": t("no_booking_found", lang, client_name=client_name), "action": "not_found"}

    new_date = _parse_date(args.get("trip_date")) or booking.trip_date
    new_time = _parse_time(args.get("trip_time")) or booking.trip_time

    reschedule = (new_date, new_time) != (booking.trip_date, booking.trip_time)
    if reschedule:
        conflict = await find_conflict(db, new_date, new_time, exclude_booking_id=booking.id)
        if conflict is not None:
            reply = t(
                "conflict_warning",
                lang,
                other_client=conflict.client_name,
                other_time=format_time_localized(conflict.trip_time, lang),
                date=format_date_localized(new_date, lang),
                window=CONFLICT_WINDOW_MINUTES,
            )
            return {
                "reply": reply,
                "action": "conflict",
                "conflict": {
                    "conflicting_booking": BookingOut.model_validate(conflict).model_dump(mode="json"),
                },
            }

    booking.pickup = normalize_location(args.get("pickup")) or booking.pickup
    booking.dropoff = normalize_location(args.get("dropoff")) or booking.dropoff
    booking.trip_date = new_date
    booking.trip_time = new_time
    if reschedule:
        # A trip that already had its reminder fire must be eligible again
        # for the new time -- otherwise it silently never reminds at all.
        booking.reminded = False
    if args.get("fare") is not None:
        booking.fare = _parse_fare(args.get("fare"))
    if args.get("notes") is not None:
        booking.notes = args.get("notes")

    await db.commit()
    await db.refresh(booking)

    booking_out = BookingOut.model_validate(booking).model_dump(mode="json")
    await _emit(sio, "booking_updated", booking_out)

    reply = t(
        "booking_updated",
        lang,
        client_name=booking.client_name,
        pickup=booking.pickup,
        dropoff=booking.dropoff,
        date=format_date_localized(booking.trip_date, lang),
        time=format_time_localized(booking.trip_time, lang),
    )
    return {"reply": reply, "action": "booking_updated", "booking": booking_out, "refresh": True}


async def _handle_cancel_booking(db: AsyncSession, sio, args: dict, lang: str) -> dict:
    client_name = args.get("client_name")
    if not client_name:
        return {"reply": missing_fields_message(["client_name"], lang), "action": "missing_info"}

    trip_date = _parse_date(args.get("trip_date"))
    booking = await _find_client_booking(db, client_name, trip_date)
    if booking is None:
        return {"reply": t("no_booking_found", lang, client_name=client_name), "action": "not_found"}

    booking.status = "cancelled"
    await db.commit()
    await db.refresh(booking)

    booking_out = BookingOut.model_validate(booking).model_dump(mode="json")
    await _emit(sio, "booking_cancelled", booking_out)

    reply = t(
        "booking_cancelled",
        lang,
        client_name=booking.client_name,
        date=format_date_localized(booking.trip_date, lang),
        time=format_time_localized(booking.trip_time, lang),
    )
    return {"reply": reply, "action": "booking_cancelled", "booking": booking_out, "refresh": True}


async def _handle_update_status(db: AsyncSession, sio, args: dict, lang: str) -> dict:
    client_name = args.get("client_name")
    new_status = args.get("new_status")
    if not client_name or not new_status:
        missing = [f for f in ["client_name", "new_status"] if not args.get(f)]
        return {"reply": missing_fields_message(missing, lang), "action": "missing_info"}

    trip_date = _parse_date(args.get("trip_date"))
    booking = await _find_client_booking(db, client_name, trip_date)
    if booking is None:
        return {"reply": t("no_booking_found", lang, client_name=client_name), "action": "not_found"}

    booking.status = new_status
    await db.commit()
    await db.refresh(booking)

    booking_out = BookingOut.model_validate(booking).model_dump(mode="json")
    await _emit(sio, "booking_status_updated", booking_out)

    reply = t(
        "status_updated",
        lang,
        client_name=booking.client_name,
        status=STATUS_LABELS.get(new_status, {}).get(lang, new_status),
    )
    return {"reply": reply, "action": "status_updated", "booking": booking_out, "refresh": True}


async def _handle_repeat_booking(db: AsyncSession, sio, args: dict, lang: str) -> dict:
    client_name = args.get("client_name")
    new_date_raw = args.get("new_date")
    if not client_name or not new_date_raw:
        missing = [f for f in ["client_name"] if not client_name]
        if not new_date_raw:
            missing.append("trip_date")
        return {"reply": missing_fields_message(missing, lang), "action": "missing_info"}

    last_booking = await _find_client_booking(db, client_name)
    if last_booking is None:
        return {"reply": t("no_booking_found", lang, client_name=client_name), "action": "not_found"}

    new_date = _parse_date(new_date_raw)
    new_time = _parse_time(args.get("new_time")) or last_booking.trip_time
    if new_date is None:
        return {"reply": t("invalid_datetime", lang), "action": "error"}

    conflict = await find_conflict(db, new_date, new_time)
    if conflict is not None:
        pending = {
            "client_name": last_booking.client_name,
            "pickup": last_booking.pickup,
            "dropoff": last_booking.dropoff,
            "trip_date": new_date.isoformat(),
            "trip_time": new_time.isoformat(),
            "fare": str(last_booking.fare),
            "notes": last_booking.notes,
        }
        reply = t(
            "conflict_warning",
            lang,
            other_client=conflict.client_name,
            other_time=format_time_localized(conflict.trip_time, lang),
            date=format_date_localized(new_date, lang),
            window=CONFLICT_WINDOW_MINUTES,
        )
        return {
            "reply": reply,
            "action": "conflict",
            "conflict": {
                "conflicting_booking": BookingOut.model_validate(conflict).model_dump(mode="json"),
                "pending_booking": pending,
            },
        }

    new_booking = Booking(
        client_name=last_booking.client_name,
        pickup=last_booking.pickup,
        dropoff=last_booking.dropoff,
        trip_date=new_date,
        trip_time=new_time,
        fare=last_booking.fare,
        notes=last_booking.notes,
        status="confirmed",
    )
    db.add(new_booking)
    await db.commit()
    await db.refresh(new_booking)

    booking_out = BookingOut.model_validate(new_booking).model_dump(mode="json")
    await _emit(sio, "booking_created", booking_out)

    reply = t(
        "booking_repeated",
        lang,
        client_name=new_booking.client_name,
        pickup=new_booking.pickup,
        dropoff=new_booking.dropoff,
        date=format_date_localized(new_booking.trip_date, lang),
        time=format_time_localized(new_booking.trip_time, lang),
    )
    return {"reply": reply, "action": "booking_created", "booking": booking_out, "refresh": True}


async def _handle_list_bookings(db: AsyncSession, sio, args: dict, lang: str) -> dict:
    today = today_beirut()
    date_filter = args.get("filter", "all")

    stmt = select(Booking).where(Booking.status.in_(["confirmed", "in_progress"]))
    if date_filter == "today":
        stmt = stmt.where(Booking.trip_date == today)
    elif date_filter == "tomorrow":
        stmt = stmt.where(Booking.trip_date == today + dt.timedelta(days=1))
    elif date_filter == "week":
        stmt = stmt.where(Booking.trip_date.between(today, today + dt.timedelta(days=6)))

    if args.get("client_name"):
        stmt = stmt.where(Booking.client_name.ilike(f"%{_escape_like(args['client_name'])}%", escape="\\"))

    stmt = stmt.order_by(Booking.trip_date, Booking.trip_time)
    result = await db.execute(stmt)
    bookings = result.scalars().all()
    bookings_out = [BookingOut.model_validate(b).model_dump(mode="json") for b in bookings]

    reply = t("list_bookings_summary", lang, count=len(bookings_out))
    return {"reply": reply, "action": "list_bookings", "bookings": bookings_out, "refresh": False}


async def _handle_get_summary(db: AsyncSession, sio, args: dict, lang: str) -> dict:
    today = today_beirut()
    period = args.get("period", "today")

    stmt = select(Booking).where(Booking.status != "cancelled")
    if period == "today":
        stmt = stmt.where(Booking.trip_date == today)
    elif period == "week":
        stmt = stmt.where(Booking.trip_date.between(today - dt.timedelta(days=6), today))

    result = await db.execute(stmt)
    bookings = result.scalars().all()

    earned = sum((b.fare for b in bookings if b.status == "completed"), Decimal("0"))
    projected = sum((b.fare for b in bookings), Decimal("0"))

    summary = {
        "period": period,
        "earned": str(earned),
        "projected": str(projected),
        "trip_count": len(bookings),
    }
    reply = t(
        "summary_result",
        lang,
        period=PERIOD_LABELS.get(period, {}).get(lang, period),
        earned=format_money_localized(earned, lang),
        projected=format_money_localized(projected, lang),
        count=len(bookings),
    )
    return {"reply": reply, "action": "get_summary", "summary": summary, "refresh": False}


TOOL_HANDLERS = {
    "extract_booking": _handle_extract_booking,
    "update_booking": _handle_update_booking,
    "cancel_booking": _handle_cancel_booking,
    "update_status": _handle_update_status,
    "repeat_booking": _handle_repeat_booking,
    "list_bookings": _handle_list_bookings,
    "get_summary": _handle_get_summary,
}


# --------------------------------------------------------------------------
# Entry point used by routes/chat.py
# --------------------------------------------------------------------------
async def process_message(
    db: AsyncSession,
    sio,
    message: str,
    history: list[dict],
    lang: str,
) -> dict:
    if is_simple_greeting(message):
        return {"reply": t("greeting", lang), "action": "chat"}

    try:
        client = get_client()
    except RuntimeError:
        return {"reply": t("ai_error", lang), "action": "error"}

    messages: list[dict[str, Any]] = [{"role": "system", "content": build_system_prompt(lang)}]
    for turn in history[-12:]:
        role = turn.get("role")
        content = turn.get("content")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": message})

    completion_kwargs = {
        "model": GROQ_MODEL,
        "messages": messages,
        "tools": TOOLS,
        "tool_choice": "auto",
        # Low (not zero) temperature: this is a classification/extraction task where
        # consistent field extraction matters more than lexical variety in replies.
        "temperature": 0.15,
        "max_tokens": 1024,
    }
    try:
        completion = await client.chat.completions.create(**completion_kwargs)
    except BadRequestError as exc:
        # Groq occasionally emits llama-3.3-70b-versatile's native <function=...>
        # tag syntax instead of a clean structured tool call ("tool_use_failed").
        # This is a known model-side quirk, not caused by our input. If it's the
        # `chat` pseudo-tool specifically, retrying won't help (see
        # extract_fallback_chat_text docstring) -- recover the text directly
        # instead of burning another Groq call on a guaranteed repeat failure.
        fallback_text = extract_fallback_chat_text(exc.body)
        if fallback_text is not None:
            return {"reply": fallback_text or t("generic_error", lang), "action": "chat"}

        # Otherwise this is a genuine malformed tool call on a real tool (e.g.
        # extract_booking) -- tends to be deterministic at a fixed temperature,
        # so nudge it up slightly to escape the same bad generation.
        logger.warning("Groq tool-call generation failed, retrying with nudged temperature: %s", exc)
        try:
            completion = await client.chat.completions.create(
                **{**completion_kwargs, "temperature": 0.5}
            )
        except BadRequestError as retry_exc:
            fallback_text = extract_fallback_chat_text(retry_exc.body)
            if fallback_text is not None:
                return {"reply": fallback_text or t("generic_error", lang), "action": "chat"}
            logger.exception("Groq retry after tool_use_failed also failed")
            return {"reply": t("ai_error", lang), "action": "error"}
        except Exception:
            logger.exception("Groq retry after tool_use_failed also failed")
            return {"reply": t("ai_error", lang), "action": "error"}
    except Exception:
        logger.exception("Groq chat completion request failed")
        return {"reply": t("ai_error", lang), "action": "error"}

    choice = completion.choices[0].message
    tool_calls = choice.tool_calls or []

    if not tool_calls:
        return {"reply": choice.content or t("generic_error", lang), "action": "chat"}

    call = tool_calls[0]
    name = call.function.name
    try:
        args = json.loads(call.function.arguments or "{}")
    except json.JSONDecodeError:
        args = {}

    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return {"reply": t("generic_error", lang), "action": "error"}

    try:
        return await handler(db, sio, args, lang)
    except Exception:
        logger.exception("Tool handler '%s' raised with args=%r", name, args)
        await db.rollback()
        return {"reply": t("generic_error", lang), "action": "error"}
