# Persistent Storage Standard

Guidelines for database design, migrations, and data security.

## Database Choice

**PostgreSQL** as the primary database:
- Robust async support via `asyncpg`
- Strong data integrity
- JSON/JSONB for flexible schemas
- Full-text search capabilities

## SQLAlchemy Patterns

### Async Setup

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # True for debugging SQL
    pool_pre_ping=True,  # Verify connections
)
```

### Model Design

```python
class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
```

### Relationships

Use `Mapped` annotations for type safety:

```python
class User(Base):
    settings: Mapped["UserSettings"] = relationship(
        back_populates="user",
        uselist=False,
        lazy="selectin",  # Eager load by default
    )
```

## Migrations

Use **Alembic** for schema migrations:

```
alembic/
├── env.py
├── versions/
│   ├── 001_initial.py
│   └── 002_add_settings.py
└── alembic.ini
```

### Migration Guidelines

1. **One change per migration** - easier to review and rollback
2. **Always include downgrade** - even if it's just `pass`
3. **Test both directions** - up and down
4. **No data migrations in schema migrations** - separate concerns

### Naming Conventions

```
{sequence}_{description}.py
001_create_users_table.py
002_add_email_index.py
003_create_settings_table.py
```

## Data Encryption

### Sensitive Data at Rest

Encrypt sensitive fields (OAuth tokens, API keys):

```python
from cryptography.fernet import Fernet

def encrypt_token(token: str, key: bytes) -> str:
    """Encrypt sensitive data before storage."""
    f = Fernet(key)
    return f.encrypt(token.encode()).decode()

def decrypt_token(encrypted: str, key: bytes) -> str:
    """Decrypt data after retrieval."""
    f = Fernet(key)
    return f.decrypt(encrypted.encode()).decode()
```

### Key Derivation

Derive encryption keys from application secret:

```python
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=SALT,  # Static, stored separately from SECRET_KEY
    iterations=480_000,
)
key = base64.urlsafe_b64encode(kdf.derive(SECRET_KEY.encode()))
```

### What to Encrypt

| Data Type | Encrypt? | Notes |
|-----------|----------|-------|
| OAuth access/refresh tokens | Yes | Always |
| API keys for external services | Yes | Always |
| User passwords | Hash, don't encrypt | Use bcrypt/argon2 |
| Email addresses | Consider | Depends on requirements |
| General user data | No | Use DB-level encryption if needed |

## Connection Security

### TLS/SSL

Always use SSL for database connections:

```python
DATABASE_URL = "postgresql+asyncpg://user:pass@host/db?ssl=require"
```

### Connection Pooling

Configure pool size based on workload:

```python
engine = create_async_engine(
    DATABASE_URL,
    pool_size=5,        # Concurrent connections
    max_overflow=10,    # Additional connections under load
    pool_timeout=30,    # Wait time for connection
)
```

## Testing

Refer to ap-base `testing.md`, with additions:

### Test Database Isolation

```python
@pytest.fixture
async def db_session():
    """Isolated database session with rollback."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        yield session
        await session.rollback()
```

### In-Memory for Unit Tests

```python
# conftest.py
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
```

Use PostgreSQL for integration tests to catch dialect-specific issues.
