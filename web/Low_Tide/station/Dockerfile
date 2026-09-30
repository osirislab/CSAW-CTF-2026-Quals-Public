FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY station_app.py .

# station identity/clock is passed at runtime via env vars, not baked into the image,
# so the same image serves all 4 stations
ENV STATION_ID=st-01 \
    TARGET_TIME=2018-07-12T04:00:00-04:00 \
    WINDOW_SECONDS=5 \
    IS_RELAY_STATION=false \
    ADMIN_RELAY_HOST=10.10.14.31 \
    RELAY_KEY=4f9a-77c2-e01d

EXPOSE 5000

# gunicorn for anything beyond local testing - dev server is single-threaded.
# IMPORTANT: exactly 1 worker. OFFSET_SECONDS is computed once at module-import
# time; with gunicorn's default preload_app=False, EACH worker process imports
# the module independently after being forked, computing its own offset at
# whatever moment that worker happens to finish starting - meaning multiple
# workers can genuinely disagree on this station's "current time" by seconds,
# causing a token valid on worker A to be rejected by worker B. Threads (not
# processes) give concurrency without this risk, since they share the same
# already-imported module state.
RUN pip install --no-cache-dir gunicorn
CMD ["gunicorn", "-w", "1", "--threads", "8", "-b", "0.0.0.0:5000", "station_app:app"]
