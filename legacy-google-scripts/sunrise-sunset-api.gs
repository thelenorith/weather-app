function sunrise_sunset_api_get_astronomy(location) {
  var coordinates = get_coordinates(location); // array
  
  // if no coordinates found, use defaults
  if (coordinates == null) {
    debug("Using default location, no coordinates found with location '" + location + "'.");
    coordinates = get_coordinates(DEFAULT_CITY + ", " + DEFAULT_STATE);
  }
  
  var data = JSON.parse(get_url("https://api.sunrise-sunset.org/json?lat=" + coordinates[0] + "&lng=" + coordinates[1] + "&formatted=0"));
  
  var sunrise = new Date(data.results.sunrise);
  var sunset = new Date(data.results.sunset);
  var solar_noon = new Date(data.results.solar_noon);
  var civil_twilight_begin = new Date(data.results.civil_twilight_begin);
  var civil_twilight_end = new Date(data.results.civil_twilight_end);
  var nautical_twilight_begin = new Date(data.results.nautical_twilight_begin);
  var nautical_twilight_end = new Date(data.results.nautical_twilight_end);
  var astronomical_twilight_begin = new Date(data.results.astronomical_twilight_begin);
  var astronomical_twilight_end = new Date(data.results.astronomical_twilight_end);
  
  return {
    "sunrise": {
      "string": (sunrise.getHours() + ":" + Utilities.formatString("%02d", sunrise.getMinutes())),
      "epoch": sunrise.getTime()
    },
    "sunset": {
      "string": (sunset.getHours() + ":" + Utilities.formatString("%02d", sunset.getMinutes())),
      "epoch": sunset.getTime()
    },
    "solar_noon": {
      "string": (solar_noon.getHours() + ":" + Utilities.formatString("%02d", solar_noon.getMinutes())),
      "epoch": solar_noon.getTime()
    },
    "civil_twilight_begin": {
      "string": (civil_twilight_begin.getHours() + ":" + Utilities.formatString("%02d", civil_twilight_begin.getMinutes())),
      "epoch": civil_twilight_begin.getTime()
    },
    "civil_twilight_end": {
      "string": (civil_twilight_end.getHours() + ":" + Utilities.formatString("%02d", civil_twilight_end.getMinutes())),
      "epoch": civil_twilight_end.getTime()
    },
    "nautical_twilight_begin": {
      "string": (nautical_twilight_begin.getHours() + ":" + Utilities.formatString("%02d", nautical_twilight_begin.getMinutes())),
      "epoch": nautical_twilight_begin.getTime()
    },
    "nautical_twilight_end": {
      "string": (nautical_twilight_end.getHours() + ":" + Utilities.formatString("%02d", nautical_twilight_end.getMinutes())),
      "epoch": nautical_twilight_end.getTime()
    },
    "astronomical_twilight_begin": {
      "string": (astronomical_twilight_begin.getHours() + ":" + Utilities.formatString("%02d", astronomical_twilight_begin.getMinutes())),
      "epoch": astronomical_twilight_begin.getTime()
    },
    "astronomical_twilight_end": {
      "string": (astronomical_twilight_end.getHours() + ":" + Utilities.formatString("%02d", astronomical_twilight_end.getMinutes())),
      "epoch": astronomical_twilight_end.getTime()
    },
  };
}
