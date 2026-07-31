FROM python:3.11-slim AS builder

WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.11-slim

RUN useradd --create-home --uid 1000 appuser

COPY --from=builder /install /usr/local

WORKDIR /app
USER appuser

ENV SOLAR_AGENT_MODE=serve \
    SOLAR_AGENT_HTTP_HOST=0.0.0.0 \
    SOLAR_AGENT_HTTP_PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["solar-agent"]
