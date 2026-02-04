
function get_weather_title(weather) {
  // build title
  var title = get_emoji("legend","relative_temp_f") + Math.round(weather[0].relative_temp_f) + "F" + weather[0].emoji;
  
  for (var i = 1; i < weather.length; i++) {
    if (weather[i-1].emoji != weather[i].emoji) {
      title += (get_emoji("legend","relative_temp_f") + Math.round(weather[0].relative_temp_f) + "F" + get_emoji("misc", "arrow") + weather[i].emoji);
    }
  }
  
  return title;
}

function get_weather_description(weather) {
  debug("DEBUG >> get_weather_description")
  var description = '';
  
  debug(JSON.stringify(weather))

  description += create_description_data(weather, "temp_f", "F", true);
  description += create_description_data(weather, "relative_temp_f", "F", true);
  description += create_description_data(weather, "dewpoint_f", "F", true);
  description += create_description_data(weather, "condition_raw", null, true); // this may not work
  description += create_description_data(weather, "chance_of_rain", "%", true);
  description += create_description_data(weather, "cloud_cover", "%", true);
  description += create_description_data(weather, "wind_mph", "mph", true);
  description += create_description_data(weather, "time_of_day", null, true);
  description += create_description_data(weather, "time_of_day_sunrise", null, false);
  description += create_description_data(weather, "time_of_day_sunset", null, false);
  //description += create_description_data(weather, "forecast_datetime", null, false);

  description += '<br><a href="http://REDACTED/legend.html">Legend</a>'
  
  debug("get_weather_description = " + description);
  
  debug("DEBUG << get_weather_description")
  return description;
}
