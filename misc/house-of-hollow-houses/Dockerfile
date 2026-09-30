FROM python:3.14.7-slim

RUN useradd -m chal

USER chal

WORKDIR /chal

COPY ./chal .


CMD ["python3", "-m", "http.server", "8000"]