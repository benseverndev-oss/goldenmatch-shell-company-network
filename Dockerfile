FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    SHELLNET_DATA_DIR=/data

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates gnupg git \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g reconcile@latest \
    && rm -rf /var/lib/apt/lists/*

# Max Harlow's Node.js scrapers (not on npm). Cloned + `npm install`ed
# at image build so the Python wrappers can shell out to `node`. See
# src/shellnet/sources/scrapers.py for the runner contract.
RUN mkdir -p /opt/scrapers \
    && git clone --depth 1 https://github.com/maxharlow/scrape-disqualified-directors.git \
       /opt/scrapers/disqualified-directors \
    && (cd /opt/scrapers/disqualified-directors && npm install --omit=dev) \
    && git clone --depth 1 https://github.com/maxharlow/scrape-members-financial-interests.git \
       /opt/scrapers/members-financial-interests \
    && (cd /opt/scrapers/members-financial-interests && npm install --omit=dev)

COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev --extra job

COPY configs ./configs
COPY scripts ./scripts

ENV PATH="/app/.venv/bin:${PATH}"

EXPOSE 8000
CMD ["sh", "-c", "uvicorn shellnet.job_server:app --host 0.0.0.0 --port ${PORT:-8000}"]
