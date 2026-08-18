# postgis/postgis doesn't include pgvector by default; build a small image
# that has both extensions available for CREATE EXTENSION.
FROM postgis/postgis:16-3.4

RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-16-pgvector \
    && rm -rf /var/lib/apt/lists/*
