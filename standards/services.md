# Services Standard

Guidelines for building API services and async processing.

## Framework

Use **FastAPI** for HTTP APIs:
- Native async support
- Automatic OpenAPI documentation
- Pydantic integration for validation
- Dependency injection system

## API Design

### Route Organization

```
src/<package>/api/
├── app.py          # App factory, lifespan, middleware
├── dependencies.py # Shared FastAPI dependencies
└── routes/
    ├── __init__.py
    ├── auth.py     # Auth-related endpoints
    └── <domain>.py # Domain-specific endpoints
```

### Endpoint Patterns

```python
@router.get("/{id}", response_model=ResponseSchema)
async def get_item(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResponseSchema:
    """Short description of what this endpoint does."""
    ...
```

### HTTP Methods

| Method | Use Case |
|--------|----------|
| GET | Retrieve resources (idempotent) |
| POST | Create resources, trigger actions |
| PUT | Full resource replacement |
| PATCH | Partial updates |
| DELETE | Remove resources |

### Response Codes

- `200` Success with body
- `201` Created (include Location header)
- `204` Success, no content
- `400` Bad request (validation failed)
- `401` Unauthorized (not authenticated)
- `403` Forbidden (authenticated but not allowed)
- `404` Not found
- `409` Conflict (duplicate, state conflict)
- `422` Unprocessable entity (semantic error)
- `500` Internal server error (unexpected)

## Async Patterns

### Service Layer

Separate business logic from route handlers:

```python
class WeatherService:
    def __init__(self, provider: WeatherProvider, cache: Cache):
        self.provider = provider
        self.cache = cache

    async def get_forecast(self, location: Coordinates) -> Forecast:
        """Business logic here, not in route handlers."""
        ...
```

### External API Calls

Use `httpx.AsyncClient` with:
- Connection pooling (reuse clients)
- Timeouts on all requests
- Retry logic with exponential backoff (use `tenacity`)

```python
async with httpx.AsyncClient(timeout=30.0) as client:
    response = await client.get(url)
```

### Background Tasks

For non-blocking operations:
- FastAPI `BackgroundTasks` for simple cases
- Consider task queues (Celery, arq) for complex workflows

## Error Handling

### Custom Exceptions

Define domain exceptions, map to HTTP responses:

```python
class WeatherAPIError(Exception):
    """Base for weather-related errors."""

class ProviderUnavailable(WeatherAPIError):
    """Weather provider is not responding."""
```

### Exception Handlers

Register handlers in app factory:

```python
@app.exception_handler(ProviderUnavailable)
async def handle_provider_error(request, exc):
    return JSONResponse(status_code=503, content={"detail": str(exc)})
```

## Configuration

Use `pydantic-settings` for configuration:
- Environment variables for secrets
- `.env` files for local development
- Validation at startup (fail fast)

See ap-base `naming.md` for environment variable conventions.

## Testing

Refer to ap-base `testing.md`, with additions:

- Use `httpx.AsyncClient` for testing FastAPI
- Mock external services at the `httpx` level
- Test authentication flows with test tokens
