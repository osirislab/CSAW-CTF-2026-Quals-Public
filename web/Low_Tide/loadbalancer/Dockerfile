FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY lb_app.py .

# station URLs point at docker-compose service names in production
ENV REQUIRED_UA="StationSync-Agent/2.1" \
    STATION_URLS="http://station-1:5000,http://station-2:5000,http://station-3:5000,http://station-4:5000"

EXPOSE 8080

RUN pip install --no-cache-dir gunicorn
# IMPORTANT: exactly 1 worker - SESSIONS is an in-memory dict; multiple worker
# processes would each have their own copy and silently lose session state.
# Threads (not processes) give concurrency within that single shared memory space.
CMD ["gunicorn", "-w", "1", "--threads", "8", "-b", "0.0.0.0:8080", "lb_app:app"]
