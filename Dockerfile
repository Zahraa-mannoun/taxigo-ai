FROM python:3.11-slim

# Trip dates/times represent Lebanon wall-clock time; the backend also uses
# this for "today"/"tomorrow" filters and the reminder service's 28-32
# minute window. Without this, a UTC-default container would silently
# compute all of that 2-3 hours off (see timezone_utils.py).
ENV TZ=Asia/Beirut

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY frontend/ ./frontend/
WORKDIR /app/backend
CMD ["sh", "-c", "uvicorn main:socket_app --host 0.0.0.0 --port ${PORT:-8000}"]
