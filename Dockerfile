FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    --no-install-recommends build-essential ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /usr/sbin/nologin --uid 1000 telekit

WORKDIR /app

COPY --chown=telekit:telekit . /app

ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir .

RUN mkdir -p /app/data/sessions /app/jobs
RUN printf '[]\n' > /app/data/clients.json
RUN chown -R telekit:telekit /app

USER telekit

CMD ["telekit", "start-program"]
