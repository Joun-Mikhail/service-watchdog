FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN useradd --system --uid 10001 --no-create-home watchdog

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./
COPY config.yaml ./

RUN mkdir -p /app/logs && chown watchdog /app/logs
USER watchdog

VOLUME ["/app/logs"]

ENTRYPOINT ["python", "watchdog.py"]
CMD ["--config", "config.yaml"]
