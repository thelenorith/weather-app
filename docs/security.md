# Security Guide

This document describes the security architecture and best practices for the Weather Event Recommendations application.

## Overview

Security is implemented at multiple layers:
- **Transport**: TLS encryption for all communication
- **Authentication**: Google OAuth 2.0
- **Authorization**: Session-based with signed JWTs
- **Data Protection**: Encryption at rest for sensitive data
- **Database**: PostgreSQL with SSL and encryption

## Transport Security (TLS)

### Requirements

- **Production**: All traffic MUST use HTTPS
- **Development**: HTTP allowed for localhost only
- Minimum TLS version: 1.2 (recommend 1.3)

### Configuration

#### Uvicorn with TLS

```bash
uvicorn weather_events.api.app:create_app --factory \
    --ssl-keyfile=/path/to/key.pem \
    --ssl-certfile=/path/to/cert.pem \
    --ssl-version=TLSv1_2
```

#### Behind Reverse Proxy (Recommended)

Use nginx or similar for TLS termination:

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /path/to/fullchain.pem;
    ssl_certificate_key /path/to/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Authentication

### Google OAuth 2.0

Authentication uses Google OAuth with minimal scopes:

| Scope | Purpose | Risk |
|-------|---------|------|
| `openid` | Authentication | Low |
| `email` | User identity | Low |
| `profile` | Display info | Low |
| `calendar.readonly` | Read events | Medium |
| `calendar.events` | Modify events | Medium |

### OAuth Security

- **State Parameter**: Random token prevents CSRF
- **PKCE**: Optional but recommended for added security
- **Token Storage**: Encrypted at rest
- **Automatic Refresh**: Tokens refreshed before expiry

### Session Management

Sessions use signed JWT tokens:

```python
{
    "sub": "user-uuid",  # User ID
    "iat": 1234567890,   # Issued at
    "exp": 1235172690,   # Expires
    "type": "session"
}
```

#### Session Security

- Tokens signed with HS256 algorithm
- Secret key from environment (minimum 32 chars)
- 7-day expiration (configurable)
- HTTP-only cookies prevent XSS access
- Secure flag in production (HTTPS only)
- SameSite=Lax prevents CSRF

## Data Encryption

### Encryption at Rest

Sensitive data (OAuth tokens) is encrypted using Fernet (AES-128-CBC):

```
┌─────────────┐
│ Plaintext   │
│ OAuth Token │
└──────┬──────┘
       │
       ▼
┌─────────────────────────┐
│ PBKDF2-HMAC-SHA256     │
│ (480,000 iterations)   │
│ Key derivation from    │
│ SECRET_KEY + salt      │
└──────────┬──────────────┘
           │
           ▼
    ┌─────────────┐
    │ Fernet      │
    │ Encryption  │
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐
    │ Ciphertext  │
    │ (base64)    │
    └─────────────┘
```

### Key Management

- **SECRET_KEY**: Primary secret for signing and encryption
- **ENCRYPTION_SALT**: Derived from SECRET_KEY if not set
- **Key Rotation**: Re-encrypt data with new key

### What's Encrypted

| Data | Encrypted | Notes |
|------|-----------|-------|
| OAuth Access Token | Yes | Short-lived |
| OAuth Refresh Token | Yes | Long-lived, sensitive |
| User Email | No | Used for identification |
| Calendar Data | No | Cached, not sensitive |
| User Settings | No | Preferences only |

## Database Security

### PostgreSQL Configuration

```bash
# Connection with SSL
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require
```

### SSL Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `disable` | No SSL | Never in production |
| `require` | SSL required | Minimum for production |
| `verify-ca` | Verify CA | Recommended |
| `verify-full` | Verify hostname | Most secure |

### Encryption at Rest

PostgreSQL Transparent Data Encryption (TDE):

```bash
# Or use encrypted filesystem
# Or cloud-managed encryption (AWS RDS, etc.)
```

### Connection Pooling

```python
DATABASE_POOL_SIZE = 5
DATABASE_MAX_OVERFLOW = 10
```

## CORS Configuration

```python
ALLOWED_ORIGINS = [
    "https://yourdomain.com",
    "https://app.yourdomain.com",
]
```

- Specify exact origins (no wildcards in production)
- Credentials allowed for session cookies
- Methods restricted to actual needs

## Rate Limiting

### Recommended Configuration

```python
# Using slowapi or similar
RATE_LIMIT_DEFAULT = "100/minute"
RATE_LIMIT_AUTH = "10/minute"  # Prevent brute force
```

### Per-Endpoint Limits

| Endpoint | Limit | Reason |
|----------|-------|--------|
| `/auth/login` | 10/min | Prevent abuse |
| `/auth/callback` | 10/min | OAuth flow |
| `/api/*` | 100/min | Normal usage |
| `/api/calendars/*/sync` | 10/min | API quota |

## Input Validation

All inputs are validated using Pydantic models:

```python
class LocationSettings(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
```

### SQL Injection Prevention

SQLAlchemy ORM prevents SQL injection:

```python
# Safe - parameterized
result = await db.execute(
    select(User).where(User.email == user_email)
)

# Never do this
# result = await db.execute(f"SELECT * FROM users WHERE email = '{email}'")
```

## Secrets Management

### Environment Variables

Never commit secrets. Use:
- `.env` file (gitignored)
- Environment variables
- Secret management service (Vault, AWS Secrets Manager)

### Required Secrets

| Secret | Purpose | Generation |
|--------|---------|------------|
| `SECRET_KEY` | Signing/encryption | `openssl rand -hex 32` |
| `DATABASE_URL` | DB connection | From your provider |
| `GOOGLE_CLIENT_SECRET` | OAuth | From Google Console |

## Security Checklist

### Development

- [ ] Use `.env` for secrets
- [ ] Don't commit `.env` to git
- [ ] Run with DEBUG=true for error details

### Production

- [ ] HTTPS everywhere (TLS 1.2+)
- [ ] Strong SECRET_KEY (32+ chars)
- [ ] Database SSL enabled
- [ ] DEBUG=false
- [ ] Restricted CORS origins
- [ ] Rate limiting enabled
- [ ] Security headers (CSP, HSTS)
- [ ] Regular dependency updates
- [ ] Log monitoring for anomalies

## Security Headers

Add via nginx or middleware:

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
```

## Vulnerability Disclosure

If you discover a security vulnerability:
1. Do not open a public issue
2. Email security@yourdomain.com
3. Include reproduction steps
4. Allow 90 days for fix before disclosure
