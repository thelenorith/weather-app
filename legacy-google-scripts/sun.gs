
function test_AstronomicalSunset() {
  lat=35.6
  long=-78.7
  date_ms = now_ms()
  asunset_ms = AstronomicalSunset(lat,long,date_ms)
  debug("AstronomicalSunset: " + asunset_ms)
  debug("AstronomicalSunset: " + new Date(asunset_ms))
}

function test_AstronomicalSunrise() {
  lat=35.6
  long=-78.7
  date_ms = Date.now()
  asunrise_ms = AstronomicalSunrise(lat,long,date_ms)
  debug("AstronomicalSunrise: " + asunrise_ms)
  debug("AstronomicalSunrise: " + new Date(asunrise_ms))
}

function AstronomicalSunset(lat,long,date_ms) {
  sunset_ms = getSunsetAndSunrise(date_ms,lat,long,-18)[0]
  debug("sunset: " + sunset_ms)
  return sunset_ms
}

function test_AstronomicalSunsetAsDate() {
  d=new Date()
  debug("NOW: " + d) 
  AstronomicalSunsetAsDate(35.6,-78.7,d)
}

function AstronomicalSunsetAsDate(lat,long,date_ms) {
  return new Date(AstronomicalSunset(lat,long,date_ms));
}

function AstronomicalSunrise(lat,long,date_ms) {
  sunrise_ms = getSunsetAndSunrise(date_ms,lat,long,-18)[1]
  debug("sunrise_ms: " + sunrise_ms)
  return sunrise_ms
}

function AstronomicalSunriseAsDate(lat,long,date_ms) {
  return new Date(AstronomicalSunrise(lat,long,date_ms));
}

function test_MiddleOfAstronomicalNightAsDate() {
  lat=35.6
  long=-78.7
  a = MiddleOfAstronomicalNightAsDate(lat,long)
  debug("MiddleOfAstronomicalNightAsDate: " + a)
}

function MiddleOfAstronomicalNightAsDate(lat,long,date_ms) {
  if (!date_ms) {
    date_ms = get_noon_ms()
  }
  data=getSunsetAndSunrise(date_ms,lat,long,-18)
  sunset_ms=data[0]
  sunrise_ms=data[1]
  debug("Sunset: " + new Date(sunset_ms))
  debug("Sunrise: " + new Date(sunrise_ms))
  return new Date(sunset_ms + (sunrise_ms - sunset_ms) / 2)
}


function getSunsetAndSunrise(date_ms,lat,long,target_altitude) {
  if (!target_altitude) {
    debug("ERROR: target_altitude not set in getSunsetAndSunrise")
  }
  date=new Date(date_ms)

  // https://stackoverflow.com/questions/8619879/javascript-calculate-the-day-of-the-year-1-366
  doy=dayOfYear(date)
  debug("doy="+doy)

  // source: https://www.pveducation.org/pvcdrom/properties-of-sunlight/the-suns-position

  // Tgmt: the difference of the Local Time (LT) from Greenwich Mean Time (GMT) in hours
  Tgmt=date.getTimezoneOffset()/-60
  debug("Tgmt="+Tgmt)
  
  // Local Standard Time Meridian
  LSTM=15*Tgmt
  debug("LSTM="+LSTM)

  // B, in degrees and d is the number of days since the start of the year.
  B=(360/365)*(doy-81)
  debug("B="+B)

  // The equation of time (EoT) (in minutes) is an empirical equation that corrects for the eccentricity of the Earth's orbit and the Earth's axial tilt.
  EoT=9.87*sin(2*B)-7.53*cos(B)-1.5*sin(B)
  debug("EoT="+EoT)

  // Time Correction Factor (in minutes) accounts for the variation of the Local Solar Time (LST)
  TC=4*(long-LSTM)+EoT
  debug("TC="+TC)

  // declination angle
  dec=23.45*sin(B)
  debug("dec="+dec)

  // solve for Hour Angle (HRA) by setting target altitude
  HRA=acos((sin(target_altitude)-sin(dec)*sin(lat))/(cos(dec)*cos(lat)))
  debug("HRA="+HRA)

  // Local Solar Time (LST) calculated from HRA
  // negative HRA is sunrise, positive is sunset.  we want both
  LST_sunrise=-HRA/15+12
  debug("LST_sunrise="+LST_sunrise)

  LST_sunset=HRA/15+12
  debug("LST_sunset="+LST_sunset)

  // Local Time from LST and TC
  LT_sunrise=LST_sunrise-TC/60
  debug("LT_sunrise="+LT_sunrise)
  debug("LT_sunrise(h): "+Math.floor(LT_sunrise))
  debug("LT_sunrise(m): "+Math.floor(60*(LT_sunrise-Math.floor(LT_sunrise))))

  LT_sunset=LST_sunset-TC/60
  debug("LT_sunset="+LT_sunset)
  debug("LT_sunset(h): "+Math.floor(LT_sunset))
  debug("LT_sunset(m): "+Math.floor(60*(LT_sunset-Math.floor(LT_sunset))))

  // convert to UTC and then get milliseconds since epoch
  sunrise=new Date(date.valueOf()+24*60*60*1000)
  sunrise.setUTCHours(-1*Tgmt) // start with the TZ offset (which is negative..)
  sunrise.setUTCMinutes(0)
  sunrise.setUTCSeconds(0)
  sunrise.setUTCMilliseconds(0)
  sunrise_ms = sunrise.getTime()
  sunrise_ms += LT_sunrise*60*60*1000 // hours to ms

  sunset=new Date(date.valueOf())
  sunset.setUTCHours(-1*Tgmt) // start with the TZ offset (which is negative..)
  sunset.setUTCMinutes(0)
  sunset.setUTCSeconds(0)
  sunset.setUTCMilliseconds(0)
  sunset_ms = sunset.getTime()
  sunset_ms += LT_sunset*60*60*1000 // hours to ms

  // from an astrophotography point of view I care about from sunset to sunrise, so that's the order I return.  also matches function name
  return [sunset_ms,sunrise_ms]
}