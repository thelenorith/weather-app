# Authentication Standard

Guidelines for user authentication and authorization.

## OAuth 2.0

### Provider Integration

Start with **Google OAuth** for simplicity:
- Well-documented, widely used
- Handles email verification
- Provides profile information

### Scope Minimization

Request only required scopes:

```python
SCOPES = [
    "openid",           # Required for OIDC
    "email",            # User's email address
    "profile",          # Basic profile (name, picture)
    # Add specific scopes only when needed:
    # "https://www.googleapis.com/auth/calendar.readonly"
]
```

### Token Handling

| Token Type | Storage | Lifetime |
|------------|---------|----------|
| Access Token | Memory/encrypted DB | Short (1 hour) |
| Refresh Token | Encrypted DB only | Long (weeks/months) |
| Session Token | HTTP-only cookie | Session or configurable |

## Session Management

### JWT Sessions

Use JWT for stateless session tokens:

```python
payload = {
    "sub": str(user.id),      # Subject (user ID)
    "exp": expiration_time,    # Expiration
    "iat": issued_at,          # Issued at
    "jti": unique_id,          # JWT ID (for revocation)
}
```

### Cookie Settings

```python
response.set_cookie(
    key="session",
    value=token,
    httponly=True,      # Not accessible via JavaScript
    secure=True,        # HTTPS only (disable for local dev)
    samesite="lax",     # CSRF protection
    max_age=86400,      # 24 hours (or None for session cookie)
)
```

### Session Revocation

Options for invalidating sessions:
1. Short expiration times (simplest)
2. Token blacklist in cache (Redis)
3. Version number in user record (invalidate all sessions)

## Authorization

### FastAPI Dependencies

```python
async def get_current_user(
    session: str = Cookie(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate user from session."""
    if not session:
        raise HTTPException(401, "Not authenticated")
    ...

async def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    """Require admin role."""
    if not user.is_admin:
        raise HTTPException(403, "Admin access required")
    return user
```

### Route Protection

```python
@router.get("/profile")
async def get_profile(user: User = Depends(get_current_user)):
    """Protected route - requires authentication."""
    ...

@router.get("/admin/users")
async def list_users(admin: User = Depends(require_admin)):
    """Admin-only route."""
    ...
```

## Security Considerations

### Token Storage

- **Never** store tokens in localStorage (XSS vulnerable)
- Use HTTP-only cookies for session tokens
- Encrypt OAuth tokens at rest (see `persistent-storage.md`)

### CSRF Protection

- Use `SameSite=Lax` or `Strict` cookies
- For APIs consumed by SPAs, consider CSRF tokens

### Rate Limiting

Apply rate limits to auth endpoints:
- Login attempts: 5/minute per IP
- Token refresh: 10/minute per user
- Registration: 3/hour per IP

## Testing Auth Flows

```python
@pytest.fixture
def authenticated_client(test_user):
    """Client with valid session cookie."""
    token = create_session_token(test_user.id)
    client = TestClient(app)
    client.cookies.set("session", token)
    return client
```

Mock OAuth providers in tests - never hit real OAuth in CI.
