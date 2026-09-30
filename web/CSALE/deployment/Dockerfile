FROM python:3.12-slim@sha256:7a8b475003c4fe15a2cd4e55e5cfc2f3560bdc9333d624f24cdd6d4340fd7a17

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd --create-home --uid 10001 csale

COPY --chown=csale:csale main.py reset_db.py vault.py osrs_public.pem ./
COPY --chown=csale:csale templates ./templates
COPY --chown=csale:csale static ./static
COPY --chown=csale:csale private_listing_images ./private_listing_images
RUN chown csale:csale /app

USER csale

EXPOSE 5000

CMD ["sh", "-c", "python reset_db.py && exec gunicorn --workers 1 --bind 0.0.0.0:5000 --access-logfile - --error-logfile - main:app"]
