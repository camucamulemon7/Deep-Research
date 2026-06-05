FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Tokyo

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      bash \
      ca-certificates \
      coreutils \
      curl \
      findutils \
      jq \
      nodejs \
      npm \
      procps \
      tzdata \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash app \
    && mkdir -p /home/app/.config /home/app/.local/share /home/app/.local/state /home/app/.cache \
    && chown -R app:app /home/app/.config /home/app/.local /home/app/.cache

WORKDIR /workspace

USER app

CMD ["./run.sh"]
