# Artemis Insight Backend

FastAPI backend for AI-powered document intelligence platform.

## Development Setup

### Prerequisites
- Python 3.11+
- Docker and Docker Compose

### Local Development

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create `.env` file:**
   ```bash
   cp ../.env.example ../.env
   # Edit .env with your configuration
   ```

3. **Run tests:**
   ```bash
   pytest tests/ -v --cov=app --cov-report=term-missing
   ```

4. **Run linting:**
   ```bash
   flake8 app/
   black app/ --check
   isort app/ --check-only
   ```

5. **Format code:**
   ```bash
   black app/
   isort app/
   ```

### Running with Docker

```bash
# From project root
docker-compose up backend
```

## API Documentation

When running in debug mode, API documentation is available at:
- Swagger UI: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`

## Authentication

The API uses JWT tokens for authentication:

- **Access Token**: Expires in 15 minutes
- **Refresh Token**: Expires in 7 days

### Endpoints

- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get tokens
- `POST /api/auth/refresh` - Refresh access token
- `GET /api/auth/me` - Get current user info

## Testing

Tests are organized into:
- `tests/unit/` - Unit tests for individual components
- `tests/integration/` - Integration tests for workflows

Target coverage: ≥85% for critical modules

## Project Structure

```
backend/
├── app/
│   ├── routes/          # API endpoints
│   ├── models/          # Pydantic models
│   ├── services/        # Business logic
│   ├── utils/           # Helper functions
│   ├── middleware/      # Auth and other middleware
│   ├── config.py        # Configuration management
│   ├── database.py      # MongoDB connection
│   ├── celery_app.py    # Celery configuration
│   └── main.py          # FastAPI app initialization
├── tests/               # Test suite
├── Dockerfile           # Docker configuration
├── requirements.txt     # Python dependencies
└── pyproject.toml       # Tool configuration
```
