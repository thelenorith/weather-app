# Weather Event Recommendations

A flexible, rule-based weather event recommendation system for outdoor activities. This application helps you plan activities by evaluating weather conditions against customizable requirements.

## Features

- **Multi-source Weather Data**: Support for multiple weather providers (MET Norway, Pirate Weather) with a canonical data format
- **Activity-Based Rules**: Define requirements for different activities (running, cycling, astronomy, solar observation)
- **Gear Recommendations**: Personalized clothing/gear suggestions based on weather conditions
- **Go/No-Go Decisions**: Weighted scoring system for making activity decisions
- **Time Slot Optimization**: Find optimal weather windows within a forecast period
- **Astronomical Calculations**: Accurate sun/moon positions, twilight times using astropy

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd weather-app

# Install in development mode
pip install -e ".[dev]"

# Or use make
make install-dev
```

## Requirements

- Python 3.12 or higher
- Dependencies listed in `pyproject.toml`

## Quick Start

```python
from datetime import datetime, timezone
from weather_events.models.location import Coordinates
from weather_events.models.activity import create_running_activity
from weather_events.providers import MetNoProvider
from weather_events.rules import RuleEngine

# Define location
coords = Coordinates(latitude=40.7128, longitude=-74.0060)

# Get forecast
async with MetNoProvider(user_agent="my-app/1.0 contact@example.com") as provider:
    forecast = await provider.get_forecast(coords)

# Evaluate conditions for running
activity = create_running_activity()
engine = RuleEngine()
decision = engine.make_decision(forecast.hourly[0], activity)

print(f"Decision: {decision.decision}")
print(f"Score: {decision.score:.1f}")
print(f"Summary: {decision.summary}")
```

## Architecture

### Core Models

- **Location**: Coordinates and address handling
- **Weather**: Canonical weather data format (temperature, wind, clouds, precipitation, etc.)
- **Event**: Calendar event integration
- **Activity**: Activity definitions with requirements
- **Recommendation**: Gear, time slot, and go/no-go recommendations

### Weather Providers

All providers translate their API responses to a canonical format:

| Provider | Endpoint | Auth | Rate Limit |
|----------|----------|------|------------|
| MET Norway | api.met.no | User-Agent header | Caching required |
| Pirate Weather | pirateweather.net | API key | Varies by plan |

### Rule Engine

The rule engine evaluates weather conditions against activity requirements:

```python
from weather_events.rules import RuleEngine, Condition, ConditionType, ComparisonOperator

# Create custom conditions
conditions = [
    Condition(
        type=ConditionType.TEMPERATURE,
        operator=ComparisonOperator.BETWEEN,
        value=[10, 25],
        description="Comfortable temperature range",
        is_required=True,
    ),
    Condition(
        type=ConditionType.WIND_SPEED,
        operator=ComparisonOperator.LESS_THAN,
        value=8,
        description="Calm wind",
    ),
]

# Evaluate
result = evaluate_conditions(forecast, conditions)
```

### Gear Recommendations

Personalized gear recommendations based on conditions:

```python
from weather_events.recommendations.gear import GearRecommender, create_running_gear_rules

recommender = GearRecommender(rules=create_running_gear_rules())
recommendation = recommender.recommend(forecast)

for item in recommendation.items:
    print(f"- {item.name} ({item.category})")
```

### Astronomy Calculations

Accurate astronomical calculations using astropy:

```python
from weather_events.astronomy import AstronomyCalculator

calc = AstronomyCalculator(coords)

# Get twilight times
twilight = calc.get_twilight_times(datetime.now())
print(f"Astronomical twilight: {twilight.astronomical_twilight_end}")

# Check if suitable for observing
is_dark = calc.is_astronomical_night(datetime.now())
```

### Go/No-Go Decisions

Weighted scoring for activity decisions:

```python
from weather_events.recommendations.go_no_go import AstronomyGoNoGoEvaluator

evaluator = AstronomyGoNoGoEvaluator(
    max_cloud_cover=30,
    max_precipitation_prob=20,
    max_wind_speed=8,
)
decision = evaluator.evaluate(forecast)

print(f"Decision: {decision.decision}")
for factor in decision.factors:
    print(f"  {factor.display_name}: {factor.value} ({factor.severity})")
```

## Development

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make coverage

# Run specific test file
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

# All checks
make check
```

## Project Structure

```
weather-app/
├── src/weather_events/
│   ├── models/           # Domain models
│   │   ├── location.py   # Coordinates, Location
│   │   ├── weather.py    # Forecast, HourlyForecast
│   │   ├── event.py      # Calendar events
│   │   ├── activity.py   # Activity definitions
│   │   └── recommendation.py  # Recommendation types
│   ├── providers/        # Weather data providers
│   │   ├── base.py       # Provider interface
│   │   ├── metno.py      # MET Norway
│   │   └── pirateweather.py  # Pirate Weather
│   ├── astronomy/        # Astronomical calculations
│   │   └── calculator.py # Sun/moon positions, twilight
│   ├── rules/            # Rule engine
│   │   ├── conditions.py # Condition definitions
│   │   └── engine.py     # Rule evaluation
│   └── recommendations/  # Recommendation systems
│       ├── gear.py       # Clothing recommendations
│       ├── go_no_go.py   # Go/no-go decisions
│       └── time_slots.py # Optimal time finding
├── tests/                # Test suite
├── pyproject.toml        # Project configuration
└── Makefile              # Development commands
```

## Weather Provider API Translations

### MET Norway (api.met.no)

| MET.no Field | Canonical Field | Unit |
|--------------|-----------------|------|
| air_temperature | temperature_c | °C |
| wind_speed | wind.speed_ms | m/s |
| cloud_area_fraction | cloud_cover.total_percent | % |
| precipitation_amount | precipitation.amount_mm | mm |

### Pirate Weather

| PirateWeather Field | Canonical Field | Unit (SI) |
|---------------------|-----------------|-----------|
| temperature | temperature_c | °C |
| apparentTemperature | feels_like_c | °C |
| humidity | relative_humidity_percent | 0-1 → % |
| cloudCover | cloud_cover.total_percent | 0-1 → % |

## Use Cases

### Calendar Event Forecasts

Add weather forecasts to calendar events based on location and time.

### Running/Cycling Gear

Get personalized clothing recommendations based on temperature, wind, and precipitation. Rules can be customized for individual preferences (e.g., "I need gloves earlier than most people").

### Astronomy Observing

Make go/no-go decisions for observing sessions considering clouds, precipitation, wind, temperature, and moon phase.

### Solar Observation

Find optimal time windows when the sun is at a suitable altitude with clear skies.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass with 80% coverage
5. Submit a pull request

## License

MIT License
