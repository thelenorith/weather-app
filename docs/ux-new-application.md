# New Application: User Experience

## Overview

A web-based service that provides weather-aware recommendations for calendar events and outdoor activities.

## User Journey

### 1. Initial Setup

1. User visits the application URL
2. User clicks "Sign in with Google"
3. Google OAuth flow requests permissions:
   - Basic profile (email, name)
   - Calendar read/write access
4. User grants permissions and is redirected back
5. User lands on dashboard

### 2. Calendar Configuration

1. User sees list of their Google Calendars
2. User selects which calendars to sync
3. For each calendar, user chooses sync mode:
   - **Polling**: App checks for updates periodically
   - **Webhook**: Google pushes updates (requires public URL)
4. User sets sync interval (e.g., every 30 minutes)

### 3. Activity Configuration

1. User creates activity profiles (e.g., "Running", "Astronomy")
2. For each activity, user defines:
   - Temperature range (min/max acceptable, ideal range)
   - Wind speed limits
   - Precipitation threshold
   - Cloud cover requirements (for astronomy)
   - Sun altitude requirements (for solar observation)

### 4. Gear Rules Configuration

1. User creates gear rules per activity
2. Each rule specifies:
   - Body part category (head, torso, hands, legs)
   - Item name (e.g., "Light Gloves")
   - Temperature range when applicable
   - Weather conditions (rain, wind)
   - Priority (for exclusive categories)

### 5. Event Processing

**Trigger**: Sync runs on schedule or webhook notification

**For each event**:
1. App checks if event matches activity criteria:
   - Calendar membership
   - Event color (if configured)
   - Title pattern match
2. If matched, app fetches weather forecast for:
   - Event location (from event or default)
   - Event time window
3. App generates recommendations:
   - Go/No-Go decision with score
   - Gear recommendations
   - Weather summary
4. App updates the calendar event:
   - Appends weather emoji + summary to title
   - Appends detailed forecast to description
   - Appends gear recommendations to description

### 6. Astronomy Events

For astronomy-tagged events:
1. App calculates twilight times for event date/location
2. App auto-adjusts event start to astronomical twilight end
3. App auto-adjusts event end to civil twilight begin (next morning)
4. App evaluates astronomy-specific conditions:
   - Cloud cover
   - Moon illumination
   - Transparency/seeing (if available)
5. App provides Go/No-Go for observing session

### 7. Viewing Recommendations

**Via Calendar**: User sees updated event title/description in Google Calendar

**Via API**: User can query:
- `GET /api/forecast?location=...&time=...` - Raw forecast
- `GET /api/recommendations/{event_id}` - Recommendations for specific event
- `GET /api/gear?activity=running&temp=15` - Gear for conditions

### 8. Manual Refresh

User can trigger manual sync from dashboard to update events immediately.

## Event Update Format

**Title**: `Original Title | 🌡️72°F ☀️`

**Description**:
```
[Original description]

---
Weather Forecast
🌡️ 72°F → 68°F
🌡️ Feels: 70°F → 66°F
💧 10% chance of rain
☁️ 20% cloud cover
💨 5 mph wind

---
Gear Recommendations
👕 T-Shirt
🩳 Shorts
🧢 Running Cap

---
Updated: 2024-01-15 10:30 AM
Source: weather-service
```

## Configuration Storage

All configuration stored in database:
- Activity profiles per user
- Gear rules per user
- Calendar sync settings per user
- Default location per user
