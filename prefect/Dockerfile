FROM python:3.11-slim

WORKDIR /opt/prefect

ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir prefect==2.19.9 pydantic==2.6.4

CMD ["prefect", "server", "start", "--host", "0.0.0.0"]
