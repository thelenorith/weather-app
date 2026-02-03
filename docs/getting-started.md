# Getting Started

This guide walks you through setting up and running the Weather Event Recommendations application.

## Prerequisites

- Python 3.12 or higher
- PostgreSQL 14 or higher
- Google Cloud Platform account (for OAuth and Calendar API)

## Quick Start

### 1. Clone and Install

```bash
git clone <repository-url>
cd weather-app

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows

# Install dependencies
pip install -e ".[dev]"
```

### 2. Set Up PostgreSQL

```bash
# Create database
createdb weather_events

# Or with psql
psql -c "CREATE DATABASE weather_events;"
```

### 3. Configure Environment

Create a `.env` file in the project root:

```bash
# Required
SECRET_KEY=your-secret-key-at-least-32-characters-long
DATABASE_URL=postgresql://username:password@localhost:5432/weather_events

# Google OAuth (required for calendar features)
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# Optional
DEBUG=true
ENVIRONMENT=development
```

### 4. Set Up Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable the **Google Calendar API**
4. Go to **APIs & Services > Credentials**
5. Create **OAuth 2.0 Client ID** (Web application)
6. Add authorized redirect URI: `http://localhost:8000/auth/google/callback`
7. Copy Client ID and Client Secret to your `.env` file

### 5. Initialize Database

```bash
# Run migrations (when using Alembic)
alembic upgrade head

# Or for development, create tables directly
python -c "
import asyncio
from weather_events.database import init_db, create_tables

async def setup():
    await init_db()
    await create_tables()

asyncio.run(setup())
"
```

### 6. Run the Application

```bash
# Development server with auto-reload
uvicorn weather_events.api.app:create_app --factory --reload

# Or use the CLI
weather-app serve
```

The application will be available at http://localhost:8000

## First Steps

### 1. Log In

Visit http://localhost:8000/auth/login to sign in with Google.

### 2. Connect Calendar

After logging in, your calendars will be available at:
- `GET /api/calendars/available` - List Google calendars
- `POST /api/calendars` - Add a calendar to sync

### 3. Configure Settings

Update your preferences at:
- `GET /api/settings` - View current settings
- `PATCH /api/settings` - Update settings

## Development

### Running Tests

```bash
# All tests
make test

# With coverage
make coverage

# Specific test file
pytest tests/test_rules.py -v
```

### Code Quality

```bash
# Format code
make format

# Run linters
make lint

# Type checking
make typecheck
```

### Database Migrations

```bash
# Create a migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Next Steps

- Read the [Architecture Guide](architecture.md) for system overview
- See [Calendar Integration](calendar-integration.md) for setup details
- Check [API Reference](api-reference.md) for endpoint documentation
