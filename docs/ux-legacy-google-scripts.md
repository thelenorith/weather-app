# Legacy Google Scripts: User Experience

## Overview

A Google Apps Script system that runs in the background, automatically updating Google Calendar events with weather forecasts and clothing recommendations.

## User Journey

### 1. Initial Setup

1. User creates a Google Spreadsheet with required sheets
2. User copies Google Apps Script code into Script Editor
3. User configures sheets:
   - **Config**: Key-value settings
   - **Rules: clothing**: Clothing rules table
   - **Emojis**: Category/key/emoji mappings
   - **Coordinates**: Location name to lat/lon mappings (cached lookups)
4. User runs `install()` function to create triggers
5. System is now running automatically

### 2. Configuration via Spreadsheet

**Config Sheet** contains settings like:
- `CALENDAR_NAME_RUN` - Calendar for running events
- `CALENDAR_NAME_ASTRONOMY` - Calendar for astronomy events
- `CALENDAR_NAME_MAIN_1/2/3` - Main calendars to scan
- `EVENT_COLOR_OUTSIDE` - Color code for outdoor events
- `CLOTHING_EVENT_TITLE_REGEX` - Pattern to match (e.g., "run|walk|hike")
- `EVENT_TITLE_RACE` - Keyword for race events
- `EVENT_TITLE_ASTROPHOTOGRAPHY` - Keyword for astrophotography
- `DEFAULT_CITY`, `DEFAULT_STATE` - Fallback location
- `HUMID_DEWPOINT_MIN` - Threshold for humidity indicator
- `LIGHT_WIND_MAX` - Threshold for wind indicator
- `DELIMITER_TITLE`, `DELIMITER_DESC` - Separators for appending data

**Clothing Rules Sheet** columns:
| where | what | min_temp_f | max_temp_f | condition |
|-------|------|------------|------------|-----------|
| head | beanie | | 35 | |
| head | headband | 35 | 50 | |
| torso | t-shirt | 55 | | |
| torso | long sleeve | 40 | 60 | |
| hands | light gloves | 35 | 50 | |
| hands | heavy gloves | | 35 | |
| legs | shorts | 50 | | |
| legs | tights | | 55 | |

**Emojis Sheet** columns:
| category | key | emoji |
|----------|-----|-------|
| weather | clear | ☀️ |
| weather | partly cloudy | ⛅ |
| weather | rain | 🌧️ |
| weather | windy | 💨 |
| legend | temp_f | 🌡️ |

**Coordinates Sheet** - cached location lookups:
| location | latitude | longitude |
|----------|----------|-----------|
| Central Park, NYC | 40.7829 | -73.9654 |

### 3. Event Identification

Events are processed if they match ANY of:
- **By Calendar**: Events on `CALENDAR_NAME_RUN` or `CALENDAR_NAME_ASTRONOMY`
- **By Color**: Events on main calendars with `EVENT_COLOR_OUTSIDE` color
- **By Title**: Events matching `EVENT_TITLE_SOCCER` keyword

For clothing recommendations specifically, event title must match `CLOTHING_EVENT_TITLE_REGEX`.

### 4. Automatic Processing

**Triggers** (set by `install()`):
- **Hourly**: Process today's events
- **Daily at 1 AM**: Process next 6 days of events

**Processing Flow**:
1. Acquire user lock (prevents concurrent execution)
2. For each calendar:
   - Get events for target date
   - Filter by color/title criteria
3. For each matching event:
   - Check if event is in the future (skip past events)
   - Check if user accepted (for events with guests)
   - Get event location (or use default)
   - Fetch weather forecast from weather-service
   - Calculate relative temperature
   - Get time-of-day context (night/dawn/day/dusk)
   - Generate weather title with emojis
   - Generate weather description
   - If running event: generate clothing recommendations
   - Update event title and description
4. Release lock

### 5. Weather Data Processing

**Relative Temperature Calculation** (custom, not "feels like"):
- Start with actual temperature
- Subtract for precipitation:
  - Chance of rain: -3°F
  - Light rain: -4°F
  - Rain: -7°F
  - Heavy rain/thunderstorm: -10°F
  - Snow: -3°F
- Subtract for wind: -1°F per mph (max -9°F)
- Add for sun exposure (if not wet):
  - Day + clear: +10°F
  - Day + partly cloudy: +5°F
  - Day + cloudy: +2°F
  - Dawn/dusk + clear: +5°F
  - Dawn/dusk + partly cloudy: +2°F
  - Night: no adjustment

**Time of Day Classification**:
- **Night**: Before dawn or after dusk
- **Dawn**: SUNRISE_LENGTH_MIN minutes before sunrise
- **Day**: Between sunrise and sunset
- **Dusk**: SUNSET_LENGTH_MIN minutes after sunset

### 6. Astronomy Event Handling

For events on astronomy calendar with "astrophotography" in title:
1. Calculate astronomical twilight times for the date
2. Auto-set event start to astronomical twilight end (evening)
3. Auto-set event end to civil twilight begin (next morning)
4. Weather description shows astronomical twilight times

### 7. Race Event Handling

For events with "race" in title:
- Standard reminders: 5 min, 60 min, evening before
- Additional reminder: 3 days before

### 8. Event Update Format

**Title**: `Original Title | 🌡️72F☀️`

If conditions change through event:
`Original Title | 🌡️72F☀️ → 🌡️68F⛅`

**Description**:
```html
[Original description]

---
<strong>🌡️</strong>: 72F → 70F → 68F<br>
<strong>🌡️</strong>: 65F → 63F → 61F<br>  [relative temp]
<strong>💧</strong>: 62F<br>  [dewpoint]
<strong>☁️</strong>: Partly Cloudy → Cloudy<br>
<strong>🌧️</strong>: 10% → 20%<br>
<strong>☁️</strong>: 30% → 50%<br>  [cloud cover]
<strong>💨</strong>: 5 mph → 8 mph<br>
<strong>🌅</strong>: day → dusk<br>
<strong>🌅</strong>: 6:30 AM<br>  [sunrise]
<strong>🌇</strong>: 8:15 PM<br>  [sunset]

<a href="http://.../legend.html">Legend</a>
---
<strong>🧢</strong>: headband<br>
<strong>👕</strong>: long sleeve<br>
<strong>🧤</strong>: light gloves<br>
<strong>🩳</strong>: shorts<br>
---
Updated: Mon Jan 15 2024 10:30:00
Source: weather-service?source=weathergov
```

### 9. Error Handling

On error:
- Title gets error delimiter: `Original Title ⚠️`
- Description gets error details with timestamp
- If location missing: special location emoji added
- Processing continues to next event

### 10. Location Resolution

1. Use event's location field
2. Look up in Coordinates spreadsheet (cached)
3. If not found, geocode and cache result
4. Fall back to DEFAULT_CITY, DEFAULT_STATE

## Key Behaviors

1. **Non-destructive updates**: Original title/description preserved, data appended after delimiters
2. **Hourly granularity**: Weather shown for each hour of event duration
3. **Transitions shown**: Values that change are shown with arrows (72F → 68F)
4. **Lock mechanism**: Prevents concurrent updates from overlapping
5. **Quiet period**: Holds lock briefly after processing to prevent rapid re-triggers
6. **Idempotent**: Can re-run safely, replaces data after delimiters
