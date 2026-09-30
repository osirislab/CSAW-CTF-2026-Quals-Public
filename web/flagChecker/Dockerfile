FROM python:3.12-slim

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY app.py .
COPY templates/ templates/
COPY .env .

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-k", "sync", "-b", "0.0.0.0:5000", "app_threadlocal:app"]
