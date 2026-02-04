var SHEET_NAME_LOCATIONS="Locations";
var CACHE_LOCATIONS={};

function spreadsheet_get_coordinates(location) {
  location = location.toUpperCase();
  debug("spreadsheet_get_coordinates(location='" + location + "')");
  
  if (location == null || location.trim() == "") {
    return null;
  }

  var coordinates = CACHE_LOCATIONS[location];
  
  if (coordinates == null) {
    debug("get_coordinates: building cache");
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME_LOCATIONS);
    var data = sheet.getRange(2, 1, 200, 3).getValues();
    for (var i = 0; i < data.length; i++) {
      var loc = data[i][0]; // location (city, state)
      var lat = data[i][1]; // lat
      var long = data[i][2]; // long
      
      if (loc == "") {
        // no more data
        break;
      }
      CACHE_LOCATIONS[loc.toUpperCase()] = [lat, long];
    }
    
    coordinates = CACHE_LOCATIONS[location];
  }
  
  // if still have nothing, look location contained
  var keys = Object.keys(CACHE_LOCATIONS);
  for (var i = 0; i < keys.length; i++) {
    if (location.indexOf(keys[i]) >= 0) {
      coordinates = CACHE_LOCATIONS[keys[i]];
    }
  }
  
  debug("COORDINATES: " + JSON.stringify(coordinates));
  
  return coordinates;
}
