# UX Comparison: New vs Legacy

## Feature Comparison

| Feature | Legacy | New | Gap? |
|---------|--------|-----|------|
| Authentication | Google account (implicit via Apps Script) | Google OAuth explicit | ✅ OK |
| Configuration storage | Google Spreadsheet | PostgreSQL | ✅ OK |
| Calendar identification | By name | By ID after OAuth | ✅ OK |
| Event filtering by color | ✅ `EVENT_COLOR_OUTSIDE` | ❌ Not implemented | **GAP** |
| Event filtering by title regex | ✅ `CLOTHING_EVENT_TITLE_REGEX` | ❌ Not implemented | **GAP** |
| Event filtering by calendar | ✅ Specific calendar names | ✅ Calendar sync config | ✅ OK |
| Weather source | weather-service (weathergov) | MET Norway, Pirate Weather | **PARTIAL** |
| Relative temperature | ✅ Custom calculation | ❌ Uses API "feels like" | **GAP** |
| Time of day (dawn/day/dusk/night) | ✅ Full support | ❌ Only day/night | **GAP** |
| Hourly transitions | ✅ Shows hour-by-hour changes | ❌ Single snapshot | **GAP** |
| Clothing rules | ✅ Spreadsheet with conditions | ✅ Database rules | ✅ OK |
| Clothing by condition (rain/snow) | ✅ `condition` column | ⚠️ Partial (rain flag) | **PARTIAL** |
| Emoji configuration | ✅ Spreadsheet customizable | ❌ Hardcoded | **GAP** |
| Astronomy event time adjustment | ✅ Auto-adjusts to twilight | ✅ Implemented | ✅ OK |
| Race event reminders | ✅ Custom reminder schedule | ❌ Not implemented | **GAP** |
| Error handling on events | ✅ Marks title, captures error | ❌ Not implemented | **GAP** |
| Location caching | ✅ Spreadsheet cache | ❌ Not implemented | **GAP** |
| Default location fallback | ✅ Config setting | ⚠️ Per-user setting | ✅ OK |
| Lock/concurrency control | ✅ UserLock | ✅ DB transactions | ✅ OK |
| Update format (delimiters) | ✅ Configurable | ⚠️ Hardcoded | **PARTIAL** |
| Legend link | ✅ Configurable URL | ❌ Not implemented | **MINOR** |

## Critical Gaps

### 1. Relative Temperature Calculation

**Legacy**: Custom calculation adjusting actual temp for:
- Precipitation effect (-3 to -10°F)
- Wind chill (-1°F per mph, max -9°F)
- Sun exposure (+2 to +10°F based on time of day + clouds)

**New**: Uses `feels_like` from weather API which only accounts for wind chill and humidity, not sun exposure or precipitation wetness.

**Impact**: Clothing recommendations may be wrong. User explicitly mentioned "I need gloves before switching out of a t-shirt" - this depends on accurate relative temperature.

### 2. Event Filtering by Color/Title

**Legacy**:
- Events on main calendars filtered by color code
- Events filtered by title regex for clothing

**New**: Only filters by calendar membership, no color or title filtering.

**Impact**: User would need separate calendars instead of using color coding on main calendar.

### 3. Hourly Transitions

**Legacy**: Shows weather changing through event duration:
```
🌡️: 72F → 70F → 68F
```

**New**: Shows single values, no transitions.

**Impact**: User can't see if conditions will change during a long event.

### 4. Time of Day Context

**Legacy**: Classifies each hour as night/dawn/day/dusk, affects relative temp calculation.

**New**: Only binary day/night from astronomical data.

**Impact**: Dawn/dusk adjustments to relative temperature are lost.

### 5. Emoji Customization

**Legacy**: Emojis stored in spreadsheet, user can customize.

**New**: Emojis hardcoded in code.

**Impact**: User can't customize appearance.

### 6. Condition-Based Clothing

**Legacy**: Clothing rules can specify `condition` like "is_rain".

**New**: Rules have `requires_rain` boolean but not full condition support (snow, thunderstorm, etc.).

**Impact**: Can't specify "wear rain jacket if thunderstorm" vs "wear light rain jacket if drizzle".

## Moderate Gaps

### 7. Race Event Handling

**Legacy**: Detects "race" keyword, sets special reminder schedule (evening before + 3 days before).

**New**: No concept of race events.

**Impact**: User loses automatic race-day reminders.

### 8. Error Display on Events

**Legacy**: On error, event title gets error marker, description captures error details.

**New**: Errors logged but not visible on event.

**Impact**: User can't see which events failed to update.

### 9. Location Caching

**Legacy**: Geocoded locations cached in spreadsheet.

**New**: No location caching, would re-geocode each time.

**Impact**: Slower processing, potential API rate limits.

## Minor Gaps

### 10. Weather Service Integration

**Legacy**: Uses user's own weather-service with weathergov backend.

**New**: Uses MET Norway and Pirate Weather.

**Note**: This is more of a configuration need - should add weather-service as a provider option.

### 11. Configurable Delimiters

**Legacy**: `DELIMITER_TITLE` and `DELIMITER_DESC` configurable.

**New**: Hardcoded ` | ` and `---`.

**Impact**: Minor - most users won't care.

## Recommendations

### Must Fix (Core Functionality)

1. **Implement relative temperature calculation** - Port the legacy algorithm
2. **Add event filtering by color** - Match legacy behavior
3. **Add event filtering by title pattern** - Match legacy behavior
4. **Add hourly transitions** - Show changes through event duration
5. **Implement dawn/dusk time periods** - Four states not just day/night

### Should Fix (Important UX)

6. **Add condition-based clothing rules** - Full condition support
7. **Add error display on events** - Match legacy error handling
8. **Add weather-service provider** - Support user's existing service
9. **Add location caching** - Performance and rate limiting

### Nice to Have

10. **Configurable emojis** - Database or settings
11. **Race event detection** - Special reminder handling
12. **Configurable delimiters** - User preference
