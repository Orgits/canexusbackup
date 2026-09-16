# CA Nexus Backend API

Unified practice management API for CA firms built with FastAPI, PostgreSQL, Redis, and Celery.

## Features

- **Multi-tenancy**: Row-level security (RLS) with PostgreSQL policies
- **Authentication**: JWT with refresh token rotation, Redis-backed blacklist
- **Authorization**: RBAC with 9 roles and 100+ permissions
- **Audit logging**: Comprehensive audit trail with PII encryption
- **Background processing**: Celery with 4 worker queues + scheduled tasks
- **Document management**: Azure Blob Storage with malware scanning
- **Compliance engine**: Configurable compliance tracking (ITR, GST, TDS, MCA/ROC)
- **Workflow engine**: Configurable state machines with role-gated transitions
- **Observability**: OpenTelemetry tracing, Prometheus metrics, Grafana dashboards
- **Rate limiting**: Per-endpoint limits with Redis backend

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│    API      │────▶│ PostgreSQL  │
└─────────────┘     │  (FastAPI)  │     │  (RLS)      │
                    └─────────────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    ▼             ▼
              ┌───────────┐ ┌───────────┐
              │  Redis    │ │  Celery   │
              │ (Cache/   │ │  Workers  │
              │  Queue)   │ │           │
              └───────────┘ └───────────┘
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- PostgreSQL 14+
- Redis 7+
- Python 3.11+ (for local development)

### Using Docker Compose (Recommended)

```bash
# Clone the repository
cd FastAPI\ Backend

# Create environment file
cp .env.example .env
# Edit .env with your configuration

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Run tests
docker-compose exec api pytest tests/ -v
```

### Local Development (without Docker)

```bash
# Install dependencies
pip install -e ".[dev]"

# Set environment variables
export DATABASE_URL=postgresql+asyncpg://ca_nexus:password@localhost:5432/ca_nexus
export REDIS_URL=redis://localhost:6379/0
export SECRET_KEY=your-secret-key-min-32-chars
export ENCRYPTION_KEY=base64-encoded-32-byte-key

# Run migrations
alembic upgrade head

# Start Redis
redis-server

# Start API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start Celery workers (separate terminals)
celery -A app.core.celery.app worker -Q compliance -c 2 --loglevel=info
celery -A app.core.celery.app worker -Q notifications -c 2 --loglevel=info
celery -A app.core.celery.app worker -Q workload -c 2 --loglevel=info
celery -A app.core.celery.app worker -Q outbox -c 2 --loglevel=info
celery -A app.core.celery.app beat --loglevel=info
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Environment (development/staging/production) | development |
| `DATABASE_URL` | PostgreSQL async connection string | `postgresql+asyncpg://...` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `CELERY_BROKER_URL` | Celery broker URL | `redis://localhost:6379/1` |
| `CELERY_RESULT_BACKEND` | Celery result backend | `redis://localhost:6379/2` |
| `SECRET_KEY` | JWT signing key (min 32 chars) | Required |
| `ENCRYPTION_KEY` | Base64-encoded 32-byte Fernet key | Required |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OpenTelemetry collector endpoint | Optional |
| `LOG_LEVEL` | Log level (DEBUG/INFO/WARNING/ERROR) | INFO |
| `LOG_FORMAT` | Log format (json/console) | json |
| `ENABLE_TRACING` | Enable OpenTelemetry tracing | true |
| `ENABLE_METRICS` | Enable Prometheus metrics | true |

## Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Check current revision
alembic current

# View migration history
alembic history
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test categories
pytest tests/unit/ -v           # Unit tests
pytest tests/integration/ -v    # Integration tests
pytest tests/api/ -v            # API tests

# Run with coverage
pytest tests/ --cov=app --cov-report=term-missing

# Run RLS isolation tests
python test_rls_isolation.py
```

## API Documentation

- Swagger UI: `http://localhost:8000/docs` (development only)
- ReDoc: `http://localhost:8000/redoc` (development only)
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Key Endpoints

### Authentication
- `POST /api/v1/auth/login` - Login with email/password
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/logout` - Logout (revokes tokens)
- `GET /api/v1/auth/me` - Current user profile

### Core Resources
- `GET/POST /api/v1/clients` - Client management
- `GET/POST /api/v1/matters` - Matter management
- `GET/POST /api/v1/tasks` - Task management
- `GET/POST /api/v1/documents` - Document management
- `GET/POST /api/v1/compliance/types` - Compliance types
- `GET/POST /api/v1/compliance/cycles` - Compliance cycles

### Monitoring
- `GET /health` - Basic health check
- `GET /ready` - Readiness probe (checks DB + Redis)
- `GET /metrics` - Prometheus metrics

## Rate Limits

| Endpoint Category | Limit |
|-------------------|-------|
| Login | 5/minute |
| Token Refresh | 10/minute |
| Password Operations | 3/minute |
| Document Upload | 30/minute |
| Compliance Initialize | 5/minute |
| Workflow Transitions | 20/minute |
| Default | 100/minute |

## Observability

### OpenTelemetry Tracing
- Distributed tracing across API → Service → Database → Worker
- Request ID propagation via `traceparent`/`tracestate` headers
- OTLP export to configured endpoint

### Metrics (Prometheus)
- HTTP metrics: requests/sec, duration, status codes
- Database: pool usage, query duration, errors
- Celery: task rates, durations, queue depth, failures
- External providers: latency, errors

### Grafana Dashboards
Access at `http://localhost:3000` (admin/admin)
- API Overview: request rates, latency, errors
- Database: pool usage, query performance
- Celery: task throughput, queue depth, worker health
- External providers: latency, error rates

### Logging
- Structured JSON logging with request IDs
- Trace ID propagation through all layers
- No sensitive PII in logs

## Rate Limiting

Rate limits are enforced per IP with path-specific limits:

| Endpoint | Limit |
|----------|-------|
| `/auth/login` | 5/minute |
| `/auth/refresh` | 10/minute |
| `/auth/*password*` | 3/minute |
| `/documents/*` | 30/minute |
| `/workflow/*/transition` | 20/minute |
| Default | 100/minute |

## Deployment

### Production Checklist

- [ ] Strong `SECRET_KEY` (64+ chars)
- [ ] Rotated `ENCRYPTION_KEY` (Fernet)
- [ ] PostgreSQL with SSL
- [ ] Redis with TLS
- [ ] Configure OTLP endpoint for tracing
- [ ] Set up Prometheus/Grafana monitoring
- [ ] Configure log aggregation
- [ ] Set up backup/restore procedures
- [ ] Configure CORS for production domains
- [ ] Set up SSL/TLS termination

### Docker Production

```bash
# Build production image
docker build -t ca-nexus-api:latest .

# Run with production env file
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Project Structure

```
FastAPI Backend/
├── app/
│   ├── api/              # API layer (routers, middleware)
│   ├── core/             # Core infrastructure (config, db, security, observability)
│   ├── modules/          # Business modules (clients, matters, tasks, etc.)
│   └── main.py           # FastAPI app factory
├── migrations/           # Alembic migrations
├── tests/                # Test suite
├── monitoring/           # Prometheus/Grafana configs
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── alembic.ini
```

## Key Technologies

- **FastAPI** - Modern async web framework
- **SQLAlchemy 2.0** - Async ORM with RLS support
- **PostgreSQL 14** - Primary database with RLS
- **Redis 7** - Caching, sessions, Celery broker
- **Celery 5** - Distributed task queue
- **OpenTelemetry** - Distributed tracing
- **Prometheus/Grafana** - Metrics & visualization
- **Alembic** - Database migrations
- **Pydantic v2** - Data validation
- **Argon2** - Password hashing

## Security

- JWT with short-lived access tokens (30 min)
- Refresh token rotation with reuse detection
- Argon2 password hashing
- Row-level security (RLS) on all tenant tables
- PII encryption at rest (Fernet AES-128-GCM)
- Token blacklist with Redis
- Account lockout after failed attempts
- No sensitive data in logs

## Contributing

1. Follow the existing code style (Ruff + MyPy)
2. Write tests for new features
3. Update documentation
4. Run linting: `ruff check . && mypy app/`
5. Run tests before submitting PR

## License

Proprietary - CA Nexus