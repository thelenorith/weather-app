# User Interfaces Standard

Guidelines for API responses, error handling, and user experience patterns.

## API Response Design

### Consistent Structure

Successful responses:
```json
{
  "data": { ... },
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "abc123"
  }
}
```

Error responses:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable description",
    "details": [ ... ]
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "abc123"
  }
}
```

### Pagination

For list endpoints:
```json
{
  "data": [ ... ],
  "pagination": {
    "total": 100,
    "page": 1,
    "per_page": 20,
    "pages": 5
  }
}
```

Use cursor-based pagination for large datasets:
```json
{
  "data": [ ... ],
  "pagination": {
    "next_cursor": "eyJpZCI6MTIzfQ==",
    "has_more": true
  }
}
```

## Error Handling

### Error Codes

Define application-specific error codes:

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `AUTHENTICATION_REQUIRED` | 401 | Not authenticated |
| `PERMISSION_DENIED` | 403 | Not authorized |
| `RESOURCE_NOT_FOUND` | 404 | Resource doesn't exist |
| `RESOURCE_CONFLICT` | 409 | Duplicate or state conflict |
| `EXTERNAL_SERVICE_ERROR` | 502 | Upstream service failed |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

### Validation Errors

Provide field-level detail:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      },
      {
        "field": "temperature_threshold",
        "message": "Must be between -50 and 50"
      }
    ]
  }
}
```

### User-Friendly Messages

- Write messages for end users, not developers
- Avoid technical jargon in user-facing errors
- Suggest corrective actions when possible

```python
# Bad
"NullPointerException in WeatherService.getForecast()"

# Good
"Weather data is temporarily unavailable. Please try again in a few minutes."
```

## Recommendations UX

### Go/No-Go Decisions

Present decisions clearly:
```json
{
  "decision": "GO",
  "confidence": 0.85,
  "score": 82,
  "summary": "Good conditions for astronomy tonight",
  "factors": [
    {
      "name": "Cloud Cover",
      "value": "15%",
      "status": "good",
      "note": "Clear skies expected"
    },
    {
      "name": "Moon Phase",
      "value": "12%",
      "status": "ideal",
      "note": "New moon - excellent for deep sky"
    }
  ],
  "blocking_factors": []
}
```

### Gear Recommendations

Group by category for easy scanning:
```json
{
  "activity": "running",
  "conditions": "12°C, light wind",
  "recommendations": {
    "torso": ["Long sleeve base layer"],
    "legs": ["Running tights"],
    "accessories": ["Light gloves", "Headband"]
  },
  "notes": [
    "Temperature will drop after sunset",
    "Consider bringing a light jacket"
  ]
}
```

### Time Slots

Rank and explain options:
```json
{
  "optimal_slot": {
    "start": "2024-01-15T14:00:00Z",
    "end": "2024-01-15T16:00:00Z",
    "score": 92,
    "summary": "Best window - clear skies, mild temperatures"
  },
  "alternatives": [
    {
      "start": "2024-01-15T10:00:00Z",
      "end": "2024-01-15T12:00:00Z",
      "score": 78,
      "summary": "Good, but cooler temperatures"
    }
  ]
}
```

## Progressive Disclosure

### Summary First

Lead with the key information:
1. Decision/recommendation (GO, wear shorts, best time is 2pm)
2. Confidence/score
3. Brief explanation
4. Detailed factors (expandable)

### Configurable Detail

Let users control verbosity:
```
GET /api/forecast?detail=summary   # Just the basics
GET /api/forecast?detail=full      # Everything
```

## Internationalization Considerations

Plan for future i18n:
- Keep user-facing strings in separate constants/files
- Use ISO formats for dates/times, convert on display
- Store temperatures in Celsius, convert on display
- Avoid concatenating translated strings

## CLI Output

Refer to ap-base `cli.md` for command-line interface standards.

For this project, CLI should mirror API patterns:
- `--format json` for machine-readable output
- `--verbose` for detailed information
- Color-coded status (green=GO, red=NO_GO, yellow=MARGINAL)
