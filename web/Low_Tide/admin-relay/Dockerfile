FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY admin_app.py .

ENV FLAG=CSAW{time_sensitive_scada_proxy_chain}

EXPOSE 5000

# single worker - LEVELS is an in-memory dict shared across requests,
# same reasoning as the load balancer and station services
RUN pip install --no-cache-dir gunicorn
CMD ["gunicorn", "-w", "1", "--threads", "8", "-b", "0.0.0.0:5000", "admin_app:app"]
