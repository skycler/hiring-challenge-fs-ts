# ---------------------------------------------------------------------------
# Builder — compile the release binary
# ---------------------------------------------------------------------------
FROM rust:1.84-bookworm AS builder

# TLS: inject extra CA cert if provided (e.g. corporate TLS proxy)
# Usage: EXTRA_CA_CERT="$(security find-certificate -a -p -c 'Cloudflare' /Library/Keychains/System.keychain)" docker compose build
ARG EXTRA_CA_CERT=""
RUN if [ -n "$EXTRA_CA_CERT" ]; then \
      printf '%s\n' "$EXTRA_CA_CERT" > /usr/local/share/ca-certificates/extra-ca.crt && \
      update-ca-certificates; \
    fi

WORKDIR /build

# Cache dependency compilation: copy manifests first, create dummy main
COPY Cargo.toml Cargo.lock ./
RUN mkdir src && echo 'fn main() { println!("dummy"); }' > src/main.rs
RUN cargo build --release || true
# Remove dummy source + compiled binary so real build is forced
RUN rm -rf src target/release/asset-api target/release/deps/asset_api*

# Copy real source and build
COPY src/ ./src/
RUN cargo build --release

# ---------------------------------------------------------------------------
# Test — run cargo test (unit tests) with JUnit XML report
# ---------------------------------------------------------------------------
FROM builder AS test

RUN cargo install cargo-nextest@0.9.93 --locked

COPY .config/ .config/

CMD ["sh", "-c", "cargo nextest run --release --profile ci && cp target/nextest/ci/junit.xml /reports/alt-unit-tests.xml"]

# ---------------------------------------------------------------------------
# Production — minimal image, non-root user
# ---------------------------------------------------------------------------
FROM debian:bookworm-slim AS production

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system app && useradd --system --gid app app

WORKDIR /app

COPY --from=builder /build/target/release/asset-api /app/asset-api

RUN chown -R app:app /app
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["/app/asset-api"]
