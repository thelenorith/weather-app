# Calendar Integration

This guide explains how to integrate with Google Calendar and configure calendar synchronization.

## Overview

The application syncs with Google Calendar to:
1. **Read events** from your calendars
2. **Detect outdoor activities** based on keywords, colors, or calendar names
3. **Add weather forecasts** to event titles and descriptions
4. **Adjust event times** for astronomy activities (sunset, twilight, etc.)

## Setting Up Google Calendar

### 1. Enable API Access

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select or create a project
3. Navigate to **APIs & Services > Library**
4. Search for "Google Calendar API"
5. Click **Enable**

### 2. Create OAuth Credentials

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth client ID**
3. Select **Web application**
4. Add authorized redirect URIs:
   - Development: `http://localhost:8000/auth/google/callback`
   - Production: `https://yourdomain.com/auth/google/callback`
5. Save the Client ID and Client Secret

### 3. Configure Application

Add to your `.env` file:

```bash
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
```

## OAuth Scopes

The application requests these scopes:

| Scope | Purpose |
|-------|---------|
| `openid` | Authentication |
| `email` | User identification |
| `profile` | Display name and picture |
| `calendar.readonly` | Read calendar list and events |
| `calendar.events` | Modify events (add weather info) |

## Sync Modes

### Polling (Default)

The application periodically checks for calendar changes.

```json
{
  "sync_mode": "poll",
  "poll_interval_minutes": 15
}
```

**Pros:**
- Simple setup
- Works behind firewalls
- No external URL needed

**Cons:**
- Slight delay in updates
- More API calls

### Webhooks

Google pushes changes to your application.

```json
{
  "sync_mode": "webhook"
}
```

**Pros:**
- Real-time updates
- Fewer API calls

**Cons:**
- Requires HTTPS public URL
- Must handle webhook expiration (renew every 24h)

**Setup:**
1. Set `WEBHOOK_BASE_URL` environment variable
2. Ensure URL is publicly accessible via HTTPS
3. Add URL to Google Cloud Console authorized domains

### Manual

Only sync when user requests.

```json
{
  "sync_mode": "manual"
}
```

## Adding a Calendar

### API Endpoint

```bash
POST /api/calendars
```

### Request Body

```json
{
  "calendar_id": "primary",
  "calendar_name": "My Calendar",
  "sync_mode": "poll",
  "poll_interval_minutes": 15,
  "event_filter_rules": {
    "colors": ["1", "2"],
    "keywords": ["outdoor", "run", "bike"],
    "require_location": false,
    "skip_all_day": false
  },
  "default_activity_type": "outdoor"
}
```

### Filter Rules

#### By Color

Google Calendar uses color IDs (1-11). Filter by specific colors:

```json
{
  "colors": ["1", "5", "10"]
}
```

Color IDs:
- 1: Lavender
- 2: Sage
- 3: Grape
- 4: Flamingo
- 5: Banana
- 6: Tangerine
- 7: Peacock
- 8: Graphite
- 9: Blueberry
- 10: Basil
- 11: Tomato

#### By Keywords

Match events containing specific words in title:

```json
{
  "keywords": ["run", "running", "outdoor", "hike"]
}
```

#### By Location

Only process events with a location:

```json
{
  "require_location": true
}
```

#### Skip All-Day Events

```json
{
  "skip_all_day": true
}
```

## Special Calendar Types

### Astronomy Calendar

For astronomy observing sessions:

```json
{
  "calendar_name": "Astronomy",
  "default_activity_type": "astronomy",
  "event_filter_rules": {
    "keywords": ["observing", "telescope"]
  }
}
```

Events are processed with:
- Time adjusted to astronomical twilight
- Go/no-go decision based on clouds, moon, wind

### Running Calendar

```json
{
  "default_activity_type": "running",
  "event_filter_rules": {
    "keywords": ["run", "jog", "marathon"]
  }
}
```

Events include:
- Weather forecast
- Clothing recommendations

## Event Updates

### Title Format

Weather is prepended to the title:

```
☀️ 22°C | Original Event Title
```

Or for multi-hour events:

```
☀️ 18°C → 🌤️ 22°C | Outdoor Activity
```

### Description Format

Weather details are appended:

```
--- Weather Forecast ---
Updated: 2024-06-15 10:30 UTC

📍 Central Park, New York
🌡️ Temperature: 22°C (feels like 24°C)
💨 Wind: 3.5 m/s from S
☁️ Cloud cover: 20%
💧 Precipitation: 10% chance

Forecast data from MET Norway
```

## Customization

### Title Delimiter

Change the separator between weather and title:

```json
{
  "display": {
    "title_delimiter": " | "
  }
}
```

### Emoji Usage

Disable emoji in titles:

```json
{
  "display": {
    "use_emoji": false
  }
}
```

### Prepend vs Append

Weather can be prepended (default) or appended:

```json
{
  "display": {
    "prepend_weather_to_title": false
  }
}
```

## Troubleshooting

### Events Not Syncing

1. Check calendar is enabled: `GET /api/calendars`
2. Verify filter rules match your events
3. Check for sync errors in response
4. Try manual sync: `POST /api/calendars/{id}/sync`

### OAuth Token Expired

Tokens are automatically refreshed. If issues persist:
1. Log out: `POST /auth/logout`
2. Log in again: `GET /auth/login`

### Rate Limiting

Google Calendar API has quotas:
- 1,000,000 queries/day
- 500 queries/100 seconds/user

The application uses sync tokens for incremental updates to minimize API calls.

### Webhook Not Receiving

1. Verify HTTPS is working
2. Check firewall allows incoming connections
3. Verify webhook URL in Google Cloud Console
4. Webhooks expire after 24h - they're renewed automatically

## Data Security

- OAuth tokens are encrypted at rest
- Calendar data is cached locally for performance
- No calendar data is shared with third parties
- Users can delete their account and all data
