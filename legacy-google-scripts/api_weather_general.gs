/**
 * Generic API for use elsewhere.  Will call specific back-ends for various implementations.
 * Definition of these function's API must be captured here.
 */

// ------------------------------
// Mutable APIs:
// ------------------------------

/**
 * Inputs:
 *   location:string - address for the request
 */
function get_astronomy(location) {
  return sunrise_sunset_api_get_astronomy(location);
}

/**
 * Input:
 *   GoogleEvent - the event we're getting data for
 * Output:
 *   [
 *     {
 *       temp_f: integer,
 *       relative_temp_f: integer,
 *       dewpoint_f: integer
 *       wind_mph: integer,
 *       chance_of_rain: integer, // [0..100]
 *       cloud_cover: integer, // [0..100]
 *       condition_raw: string,
 *       conditions: { // see get_conditions_for(weather)
 *         is_rain: boolean,
 *         is_snow: boolean,
 *         is_cloudy: boolean,
 *         is_thunderstorm: boolean,
 *         is_slight: boolean,
 *         is_chance: boolean,
 *         is_light: boolean,
 *         is_heavy: boolean
 *       }
 *       emoji: string,
 *       time_of_day: dateTime,
 *       city: string,
 *       state: string,
 *       year: integer,
 *       month: integer, // [1..12]
 *       day: integer, // [1..]
 *       time_of_day: string
 *       time_of_day_sunrise: time,
 *       time_of_day_sunset: time,
 *       forecast_datetime: datetime,
 *       coordinates: [lat, long],
 *     }
 *   ]
 */
function get_forecast(event) {
  debug("DEBUG >> get_forecast("+event.getId()+")");
  var weather = weatherservice_get_forecast(event)
  return weather
}

/**
 * Inputs:
 *   location:string - address for the request
 * Output:
 *   [lat, long]
 */
function get_coordinates(location) {
  return spreadsheet_get_coordinates(location)
}


// ------------------------------
// Standard APIs:
// ------------------------------

/**
 * Input:
 *   GoogleEvent - the event we're getting data for
 * Output:
 *   {
 *     data: [(one of: night, dawn, day, dusk)], 
 *     sunrise: string, 
 *     sunset: string
 *   }
 */
function get_time_of_day(event) {
  return _get_time_of_day(event.getStartTime(), event.getEndTime(), event.getLocation());
}


// ------------------------------
// Utility Functions:
// ------------------------------

/**
 * Inputs:
 *   weather:string - forecast short description
 * Output:
 *   {
 *     is_rain: boolean,
 *     is_snow: boolean,
 *     is_cloudy: boolean,
 *     is_thunderstorm: boolean,
 *     is_slight: boolean,
 *     is_chance: boolean,
 *     is_light: boolean,
 *     is_heavy: boolean
 *   }
 */
function get_conditions_for(weather) {
  debug("get_conditions_for("+weather+")");

  var output = {
    is_rain: false,
    is_snow: false,
    is_cloudy: false,
    is_thunderstorm: false,
    is_slight: false,
    is_chance: false,
    is_light: false,
    is_heavy: false
  };

  // split on "and"
  var conditions_uc = weather.toUpperCase().split(" AND ");

  var i = 0;

  while (i < conditions_uc.length) {
    condition_uc = conditions_uc[i];

    output.is_slight = condition_uc.indexOf("SLIGHT CHANCE") > -1;
    output.is_chance = (condition_uc.indexOf("CHANCE") > -1 || condition_uc.indexOf("LIKELY") > -1 || condition_uc.indexOf("ISOLATED") > -1);
    output.is_light = (condition_uc.indexOf("LIGHT") > -1 || condition_uc.indexOf("PARTIAL") > -1 || condition_uc.indexOf("PATCHES") > -1 || condition_uc.indexOf("SHALLOW") > -1);
    output.is_heavy = (condition_uc.indexOf("HEAVY") > -1);
    
    // order matters.  bad conditions first
    if (condition_uc.indexOf("THUNDERSTORM") > -1) {
      output.is_thunderstorm = true;
    } else if (condition_uc.indexOf("SNOW") > -1 || condition_uc.indexOf("HAIL") > -1 || condition_uc.indexOf("ICE") > -1) {
      output.is_snow = true;
    } else if (condition_uc.indexOf("SQUALLS") > -1) {
      output.is_rain = true;
      output.is_light = false;
      output.is_heavy = true;
    } else if (condition_uc.indexOf("RAIN") > -1 || condition_uc.indexOf("SHOWERS") > -1) {
      output.is_rain = true;
    } else if (condition_uc.indexOf("DRIZZLE") > -1) {
      output.is_rain = true;
      output.is_light = true;
      output.is_heavy = false;
    } else if (condition_uc.indexOf("FOG") > -1 || condition_uc.indexOf("HAZE") > -1 || condition_uc.indexOf("MIST") > -1) {
      output.is_cloudy = true;
    } else if (condition_uc.indexOf("OVERCAST") > -1) {
      output.is_cloudy = true;
    } else if (condition_uc.indexOf("CLOUDY") > -1 || condition_uc.indexOf("CLOUDS") > -1) {
      output.is_cloudy = true;
      //output.is_light = true; // commented out when switching from weather underground to weather api
    }

    // if it's a chance of thunderstorm, skip additional conditions (some level of rain)
    // as thunderstorm is the one we care about
    if (output.is_thunderstorm) {
      break
    }

    i++;
  }

  return output;
}

function convert_C_to_F(temp_C) {
  return (temp_C * 9 / 5) + 32
}

/**
 * "Internal" style function that takes specific bits required to generate the required output.
 */
function _get_time_of_day(startTime, endTime, location) {
  debug("_get_time_of_day("+startTime+","+endTime+","+location+")");
  
  var duration = endTime.valueOf() - startTime.valueOf();

  var time_of_day = [];
  var astronomy;
  
  debug("LOCATION: " + location);
  
  try {
    astronomy = get_astronomy(location);

    // make sure all dates are on the same day else it's crazy.
    var sunrise = new Date(astronomy.sunrise.epoch);
    var sunset = new Date(astronomy.sunset.epoch);
    var dusk = new Date(sunset.getTime() + 1000 * 60 * SUNSET_LENGTH_MIN); // actually when dusk ends.
    var dawn = new Date(sunrise.getTime() - 1000 * 60 * SUNRISE_LENGTH_MIN);
    
    debug("dawn: " + dawn);
    debug("sunrise: " + sunrise);
    debug("sunset: " + sunset);
    debug("dusk: " + dusk);

    var start = new Date(startTime.getTime());
    // move start to the same day as sunrise so epoch comparison works
    start.setYear(sunrise.getYear());
    start.setMonth(sunrise.getMonth());
    start.setDate(sunrise.getDate());
    
    // and adjust end date based on new start
    var end = new Date(start.valueOf() + duration);

    // switch to epoch (after updating start's day)
    dawn = dawn.valueOf();
    sunrise = sunrise.valueOf();
    sunset = sunset.valueOf();
    dusk = dusk.valueOf();

    debug("dawn: " + dawn);
    debug("sunrise: " + sunrise);
    debug("sunset: " + sunset);
    debug("dusk: " + dusk);
    debug("start: " + start.valueOf());
    debug("end: " + end.valueOf());

    // get one extra hour of data
    while (start.valueOf() <= end.valueOf() + 1000 * 60 * 60) {
      var event_start = start.valueOf();
      
      debug("event_start: " + event_start);
      
      // order of checks matters
      
      if (event_start < dawn) {
        time_of_day.push("night");
      } else if (dawn <= event_start && event_start < sunrise) {
        time_of_day.push("dawn");
      } else if (sunrise <= event_start && event_start < sunset) {
        time_of_day.push("day");
      } else if (sunset <= event_start && event_start < dusk) {
        time_of_day.push("dusk");
      } else if (dusk < event_start) {
        time_of_day.push("night");
      }
      
      // move to next hour
      start = new Date(start.getTime() + 1000 * 60 * 60);
      debug("start: " + start);
    }
    
    return {
      "data": time_of_day,
      "sunrise": astronomy.sunrise.string,
      "sunset": astronomy.sunset.string,
      "solar_noon": astronomy.solar_noon.string,
      "civil_twilight_begin": astronomy.civil_twilight_begin.string,
      "civil_twilight_end": astronomy.civil_twilight_end.string,
      "nautical_twilight_begin": astronomy.nautical_twilight_begin.string,
      "nautical_twilight_end": astronomy.nautical_twilight_end.string,
      "astronomical_twilight_begin": astronomy.astronomical_twilight_begin.string,
      "astronomical_twilight_end": astronomy.astronomical_twilight_end.string,
    }

  } catch (e) {
    debug("Failed to get astronomy stuff! Defaulting.. :(");
    debug("ERROR: " + JSON.stringify(e));
    time_of_day = "day";
    return {
      "data": [],
      "sunrise": "unknown",
      "sunset": "unknown"
    };
  }
}

/**
 * Returns an adjusted value.
 * Inputs:
 *   value_start:integer - the start value of the range
 *   value_stop:integer - the stop/end value of the range
 *   minutes_from_start:integer - minutes from the start of the range to adjust to
 *   minutes_duration:integer - total minutes for the range
 * Output:
 *   adjusted value:integer
 */
function adjust_data(value_start, value_stop, mintues_from_start, minutes_duration) {
  debug("adjust_data("+value_start+","+value_stop+","+mintues_from_start+","+minutes_duration+") =>")
  if (!value_start || !value_stop) {
    return value_start;
  }
  value_start = Number(value_start)
  value_stop = Number(value_stop)
  mintues_from_start = Number(mintues_from_start)
  minutes_duration = Number(minutes_duration)
  var output = (value_start + (value_stop - value_start) * mintues_from_start / minutes_duration)
  debug("adjust_data("+value_start+","+value_stop+","+mintues_from_start+","+minutes_duration+") = "+output)
  return output
}

function get_emojis(conditions, windSpeedMph, dewpointF) {
  debug("get_emojis("+conditions+", "+windSpeedMph+", "+dewpointF+")")
  var emoji = "";
  
  // prefix modifiers
  if (conditions.is_slight) {
    emoji += get_emoji("weather", "chance_of")
  }
  if (conditions.is_chance) {
    emoji += get_emoji("weather", "chance_of")
  }
  
  // condition
  if (conditions.is_thunderstorm) {
    emoji += get_emoji("weather", "thunderstorm")
  } else if (conditions.is_snow) {
    emoji += get_emoji("weather", "snow");
  } else if (conditions.is_cloudy) {
    var key = "";
    if (conditions.is_light) {
      key += "partly ";
    }
    key += "cloudy";
    emoji += get_emoji("weather", key);
  } else if (conditions.is_rain) {
    var key = "";
    if (conditions.is_light) {
      key += "light ";
    } else if (conditions.is_heavy) {
      key += "heavy ";
    }
    key += "rain";
    emoji += get_emoji("weather", key);
  } else {
    emoji += get_emoji("weather", "clear");
  }
  
  if (windSpeedMph > LIGHT_WIND_MAX) {
    emoji += get_emoji("weather", "windy");
  }

  if (dewpointF >= HUMID_DEWPOINT_MIN) {
    emoji += get_emoji("weather", "humid");
  }

  return emoji
}



function _get_relative_temperature(
  temp_f,
  wind_mph,
  time_of_day,
  is_rain,
  is_snow,
  is_cloudy,
  is_thunderstorm,
  is_chance,
  is_light,
  is_heavy
) {
  var weather = {
    "temp_f": temp_f,
    "wind_mph": wind_mph,
    "time_of_day": time_of_day,
    "conditions": {
      "is_rain": is_rain,
      "is_snow": is_snow,
      "is_cloudy": is_cloudy,
      "is_thunderstorm": is_thunderstorm,
      "is_chance": is_chance,
      "is_light": is_light,
      "is_heavy": is_heavy
    }
  };
  
  return get_relative_temperature(weather);
}

function get_relative_temperature(weather) {
  debug("get_relative_temperature: " + JSON.stringify(weather));
  var w = weather;
  var relative_temp_f = w.temp_f;
  var is_wet = false;
  
  // precipitation doesn't depend on time of day
  if (!w.conditions.is_slight) {
    if (w.conditions.is_rain) {
      is_wet = true;
      if (w.conditions.is_chance) {
        relative_temp_f -= 3;
      } else if (w.conditions.is_light) {
        relative_temp_f -= 4;
      } else if (w.conditions.is_heavy) {
        relative_temp_f -= 10;
      } else {
        relative_temp_f -= 7;
      }
    } else if (w.conditions.is_thunderstorm) {
      is_wet = true;
      if (w.conditions.is_chance) {
        relative_temp_f -= 4;
      } else {
        relative_temp_f -= 10; // same as heavy rain
      }
    } else if (w.conditions.is_snow) {
      is_wet = true;
      relative_temp_f -= 3;
    }
  }
  
  // wind doesn't depend on time of day, just assume each mph drops temp by 1F with a max of 9F
  relative_temp_f -= Math.min(9, w.wind_mph);
  
  // time of day only matters if it isn't wet
  if (!is_wet) {
    switch (w.time_of_day) {
      case "day":
        if (w.conditions.is_cloudy) {
          if (w.conditions.is_light) {
            relative_temp_f += 5;
          } else {
            relative_temp_f += 2;
          }
        } else {
          // clear
          relative_temp_f += 10;
        }
        break;
      case "dawn":
      case "dusk":
        if (w.conditions.is_cloudy && w.conditions.is_light) {
          relative_temp_f += 2;
          // note, no adjustment if it's overcast
        } else {
          // clear
          relative_temp_f += 5;
        }
        break;
      default: // night
        // noop, doesn't matter what cloud cover is at night
    }
  }
  
  return relative_temp_f;
}
