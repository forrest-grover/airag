# Setup Guide for DataPipeline

## Prerequisites

- Python 3.11 or higher
- PostgreSQL 15 with pgvector extension
- Redis 7.x for task queue

## Installation

Install the package using pip:

```bash
pip install datapipeline[all]
```

## Configuration

### Database Connection

Set the following environment variables:

- `DB_HOST` — PostgreSQL hostname (default: localhost)
- `DB_PORT` — PostgreSQL port (default: 5432)
- `DB_NAME` — database name
- `DB_PASSWORD` — database password

### Redis Configuration

The task queue uses Redis for job scheduling and result caching:

- `REDIS_URL` — full Redis connection URL (default: redis://localhost:6379/0)
- `REDIS_MAX_CONNECTIONS` — connection pool size (default: 10)

## Running the Pipeline

Start the worker process:

```bash
datapipeline worker --concurrency 4
```

Submit a batch job:

```bash
datapipeline submit --input data/raw/ --output data/processed/
```

## Troubleshooting

### Connection Refused Errors

Verify PostgreSQL is running and accepting connections on the configured port. Check `pg_hba.conf` for authentication rules.

### Out of Memory

Reduce worker concurrency or increase the `BATCH_SIZE` configuration. The default batch size of 1000 rows works for most datasets under 10GB.
