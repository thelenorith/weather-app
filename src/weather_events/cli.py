"""Command-line interface for weather event recommendations."""

import argparse
import sys


def main() -> int:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Weather Event Recommendations - Plan outdoor activities based on weather"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Forecast command
    forecast_parser = subparsers.add_parser(
        "forecast", help="Get weather forecast for a location"
    )
    forecast_parser.add_argument(
        "location",
        help="Location (address or lat,lon coordinates)",
    )
    forecast_parser.add_argument(
        "--provider",
        choices=["metno", "pirateweather"],
        default="metno",
        help="Weather data provider",
    )

    # Recommend command
    recommend_parser = subparsers.add_parser(
        "recommend", help="Get recommendations for an activity"
    )
    recommend_parser.add_argument(
        "activity",
        choices=["running", "cycling", "astronomy", "solar"],
        help="Activity type",
    )
    recommend_parser.add_argument(
        "location",
        help="Location (address or lat,lon coordinates)",
    )

    # Go/No-Go command
    gonogo_parser = subparsers.add_parser(
        "gonogo", help="Get go/no-go decision for an activity"
    )
    gonogo_parser.add_argument(
        "activity",
        choices=["astronomy", "solar"],
        help="Activity type",
    )
    gonogo_parser.add_argument(
        "location",
        help="Location (address or lat,lon coordinates)",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    # Commands are not yet implemented - this is a placeholder
    print(f"Command '{args.command}' is not yet implemented.")
    print("This CLI is a placeholder for future development.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
