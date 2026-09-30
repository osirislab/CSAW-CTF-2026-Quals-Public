FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd -m -u 10001 app
COPY --chown=app:app main.py idp.py .
COPY --chown=app:app templates templates
USER app

CMD ["gunicorn", "--workers", "1", "--bind", "0.0.0.0:8990", "main:app"]
