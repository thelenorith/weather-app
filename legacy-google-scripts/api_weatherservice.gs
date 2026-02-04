function weatherservice_get_forecast(event) {
  debug("DEBUG >> weatherservice_get_forecast("+event.getId()+")");

  var calendarName = CalendarApp.getCalendarById(event.getOriginalCalendarId()).getName()

  var weather_data = [];

  var start_time = new Date(event.getStartTime());
  start_time.setMinutes(0);
  start_time.setSeconds(0);

  // number of hours for the event
  var hour_count = Math.max(1, Math.floor((event.getEndTime().getTime() - event.getStartTime().getTime()) / 1000 / 60 / 60));

  var location = event.getLocation();
  var coordinates = get_coordinates(location);
  
  debug("location: " + location);
  
  source="weathergov"
  //var url = "http://REDACTED:9213/forecast/" + coordinates[0] + "/" + coordinates[1] + "?source=" + source + "&apikey=" + OPENWEATHERMAP_API_KEY
  var url = "http://REDACTED:9213/forecast/" + coordinates[0] + "/" + coordinates[1] + "?source=" + source
  debug(url)
  var forecasts = JSON.parse(get_url(url));
  data_keys = Object.keys(forecasts.data)

  // find first event in forecasts that matches startDateStr
  for (var j = 0; j < data_keys.length; j++) {
    var forecast = forecasts.data[data_keys[j]];
    
    if (forecast.dt == start_time.getTime() / 1000) {
      // found first forecast, from here, use each of the following up to and including hour_count
      
      // get the time of day
      var time_of_day = get_time_of_day(event);
      debug("TIME_OF_DAY: " + JSON.stringify(time_of_day));

      debug("hour_count = " + hour_count)
      for (var i = 0; i < hour_count; i++) {
        forecast = forecasts.data[data_keys[j + i]];

        debug("raw forecast = " + JSON.stringify(forecast))

        // units are set, you cannot request imperial.  convert in-line here.
        weather_data[i] = {
          time_of_day: time_of_day,

          // data needed for forecast link, where and when
          city: get_city_for(event),
          state: get_state_for(event),
          year: event.getStartTime().getYear(),
          month: event.getStartTime().getMonth() + 1,
          day: event.getStartTime().getDate(),
          
          // parsable for description
          time_of_day: time_of_day.data[i],
          time_of_day_sunrise: time_of_day.sunrise,
          time_of_day_sunset: time_of_day.sunset,
          forecast_datetime: forecast.dt,

          source: "REDACTED?source=" + source,
        };

        if (false && calendarName == CALENDAR_NAME_ASTRONOMY) {
          // set start and end
          var start = event.getStartTime();
          start.setHours(time_of_day.astronomical_twilight_end.split(":")[0])
          start.setMinutes(time_of_day.astronomical_twilight_end.split(":")[1])
          var end = event.getStartTime();
          end.setDate(end.getDate() + 1) // day after start
          end.setHours(time_of_day.civil_twilight_begin.split(":")[0])
          end.setMinutes(time_of_day.civil_twilight_begin.split(":")[1])
          debug("event.setTime(" + start + ", " + end + ");");
          event.setTime(start, end);
          weather_data[i].time_of_day_sunset=time_of_day.astronomical_twilight_end;
          weather_data[i].time_of_day_sunrise=time_of_day.civil_twilight_begin;
        }
        
        if (calendarName == CALENDAR_NAME_ASTRONOMY && event.getTitle().toUpperCase().indexOf(EVENT_TITLE_ASTROPHOTOGRAPHY) >= 0) {
          // set start and end for astrophotography
          var sunupdown = getSunsetAndSunrise(event.getStartTime().getTime(), coordinates[0], coordinates[1], -18);
          debug("event.setTime(" + new Date(sunupdown[0]) + ", " + new Date(sunupdown[1]) + ");");
          event.setTime(new Date(sunupdown[0]), new Date(sunupdown[1]));
          weather_data[i].time_of_day_sunset=time_of_day.astronomical_twilight_end;
          weather_data[i].time_of_day_sunrise=time_of_day.civil_twilight_begin;
        }

        if (forecast.temperature) {
          weather_data[i].temp_f = Math.floor(convert_C_to_F(forecast.temperature.value))
        }
        if (forecast.apparentTemperature) {
          weather_data[i].relative_temp_f = Math.floor(convert_C_to_F(forecast.apparentTemperature.value))
        }
        if (forecast.dewpoint) {
          weather_data[i].dewpoint_f = Math.floor(convert_C_to_F(forecast.dewpoint.value))
        }
        if (forecast.windSpeed) {
          weather_data[i].wind_mph = Math.floor(forecast.windSpeed.value/ 1.60934 * 10) / 10
        }
        if (forecast.probabilityOfPrecipitation) {
          weather_data[i].chance_of_rain = Math.floor(forecast.probabilityOfPrecipitation.value)
        }
        if (forecast.skyCover) {
          weather_data[i].cloud_cover = Math.floor(forecast.skyCover.value)
        }

        // do "weather" last as setting conditions and emoji depends on the other data
        if (forecast.weather) {
          weather_data[i].condition_raw = forecast.weather.value
          weather_data[i].conditions = get_conditions_for(forecast.weather.value)
          weather_data[i].emoji = get_emojis(weather_data[i].conditions, weather_data[i].wind_mph, weather_data[i].dewpoint_f);
        }

        // calculate relative temp and set on weather
        var relative_temp_f = get_relative_temperature(weather_data[i]);
        weather_data[i].relative_temp_f = relative_temp_f; // overrides whatever came from the weather service, this is intentional
        
        debug("WEATHER: " +JSON.stringify(weather_data[i]));
      }
      
      // don't need to process outer loop, we are done
      break;
    }
  }
  
  debug("DEBUG << openweathermap_get_forecast("+event.getId()+")");

  return weather_data;
}
