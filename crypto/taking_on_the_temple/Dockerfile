FROM python:3.12-slim-bullseye AS builder
WORKDIR /challenge
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY data ./data
RUN python -m compileall -b app && rm -f app/*.py

FROM python:3.12-slim-bullseye AS runtime
WORKDIR /challenge
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --from=builder /challenge/app ./app
COPY --from=builder /challenge/data ./data
EXPOSE 5000
CMD ["python","app/app.pyc"]