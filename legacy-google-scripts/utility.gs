var CACHE_CONFIG = {};
var CACHE_URL = {};
var CACHE_CITY = {};
var CACHE_STATE = {};

var SHEET_NAME_CONFIG="Config";
var SHEET_NAME_LOGS="Logs";
var SHEET_NAME_CLOTHING="Rules: clothing";

var SUNRISE_LENGTH_MIN=get_config("SUNRISE_LENGTH_MIN");
var SUNSET_LENGTH_MIN=get_config("SUNSET_LENGTH_MIN");;

var HUMID_DEWPOINT_MIN=get_config("HUMID_DEWPOINT_MIN");;
var LIGHT_WIND_MAX=get_config("LIGHT_WIND_MAX");
var MAX_EASY_RUN_MILES=get_config("MAX_EASY_RUN_MILES");

var DEFAULT_CITY =get_config("DEFAULT_CITY");
var DEFAULT_STATE =get_config("DEFAULT_STATE");
var DEFAULT_MILES = get_config("DEFAULT_MILES");

var EVENT_TITLE_RACE = get_config("EVENT_TITLE_RACE").toUpperCase();
var EVENT_TITLE_SOCCER = get_config("EVENT_TITLE_SOCCER").toUpperCase();
var EVENT_TITLE_ASTROPHOTOGRAPHY = get_config("EVENT_TITLE_ASTROPHOTOGRAPHY").toUpperCase();
var CLOTHING_EVENT_TITLE_REGEX = get_config("CLOTHING_EVENT_TITLE_REGEX");

var CALENDAR_NAME_RUN = get_config("CALENDAR_NAME_RUN");
var CALENDAR_NAME_RUN_UC = CALENDAR_NAME_RUN.toUpperCase();
var CALENDAR_NAME_MAIN_1 = get_config("CALENDAR_NAME_MAIN_1");
var CALENDAR_NAME_MAIN_2 = get_config("CALENDAR_NAME_MAIN_2");
var CALENDAR_NAME_MAIN_3 = get_config("CALENDAR_NAME_MAIN_3");
var CALENDAR_NAME_ASTRONOMY = get_config("CALENDAR_NAME_ASTRONOMY");

var DELIMITER_TITLE = get_config("DELIMITER_TITLE");
var DELIMITER_DESC = get_config("DELIMITER_DESC");
var DELIMITER_TITLE_ERROR = get_config("DELIMITER_TITLE_ERROR");
var DELIMITER_DESC_ERROR = get_config("DELIMITER_DESC_ERROR");

var EVENT_COLOR_OUTSIDE = get_config("EVENT_COLOR_OUTSIDE");
var EVENT_COLOR_ERROR = get_config("EVENT_COLOR_ERROR");

var DARK_SKY_API_KEY = get_config("DARK_SKY_API_KEY");

var OPENWEATHERMAP_API_KEY = get_config("OPENWEATHERMAP_API_KEY")

var LAST_EXECUTED = get_config("LAST_EXECUTED")
var QUIET_SECONDS = get_config("QUIET_SECONDS")

function install() {
  log_start("install");
  
  // first uninstall, otherwise this creates duplicate triggers
  uninstall();
  
  // spreadsheet menu
  ScriptApp.newTrigger("create_menu")
           .forSpreadsheet(SpreadsheetApp.getActiveSpreadsheet()).onOpen().create();

  // calendars...
  /*
  // main
  ScriptApp.newTrigger("trigger_calendar_updated")
           .forUserCalendar("nzmalik@gmail.com")
           .onEventUpdated().create();
  */

  /*
  // kids
  ScriptApp.newTrigger("trigger_calendar_updated")
           .forUserCalendar("s0i83cv2ujpu00r2fuam9atlcs@group.calendar.google.com")
           .onEventUpdated().create();
  */

  /*
  // astronomy
  ScriptApp.newTrigger("trigger_calendar_updated")
           .forUserCalendar("a72be363mdifupquejip3t41q8@group.calendar.google.com")
           .onEventUpdated().create();
  */

  /* 
  // family
  ScriptApp.newTrigger("trigger_calendar_updated")
           .forUserCalendar("family12415878515501450675@group.calendar.google.com")
           .onEventUpdated().create();
  */

  // periodic
  ScriptApp.newTrigger("process_today")
           .timeBased().everyHours(1).create();
  ScriptApp.newTrigger("process_future")
           .timeBased().everyDays(1).atHour(1).create();

  log_stop("install");
}

function uninstall() {
  log_start("uninstall");

  //locate all the triggers created for the script
  //remove them when uninstalling
  var triggers = ScriptApp.getProjectTriggers();
  for (var i=0; i<triggers.length; i++) {
    ScriptApp.deleteTrigger(triggers[i]);
  }
  //This will need to be run manually if you want to remove the script
  //OR if you alter the script and want to reinstall
  
  log_stop("uninstall");
}

function create_menu() 
{
  log_start("create_menu");
  var menuEntries = [ 
    {name: "1. Weather: Today", functionName: "process_today"},
    {name: "2. Weather: Tomorrow", functionName: "process_tomorrow"},
    {name: "3. Weather: Future", functionName: "process_future"},
  ];
  SpreadsheetApp.getActiveSpreadsheet().addMenu("➤ Run", menuEntries);
  log_stop("create_menu");
}

function get_config(key) {
  var value = CACHE_CONFIG[key];
  
  if (value == null) {
    debug("get_config: building cache");
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Config");
    var data = sheet.getRange(2, 2, 100, 2).getValues();
    for (var i = 0; i < data.length; i++) {
      if (data[i][1] == "") {
        break;
      }

      //debug("CACHE_CONFIG CACHE[" + data[i][0] + "] = " + data[i][1]);
      
      CACHE_CONFIG[data[i][0]] = data[i][1];
    }
    
    value = CACHE_CONFIG[key];
  }
  
  return value;
}

function clear_cache() {
  CACHE_URL = {}
}

function get_url(url) {
  var response = CACHE_URL[url];
  
  if (response == null) {
    debug("fetching data, adding to cache: " + url);
    response = UrlFetchApp.fetch(url);
    CACHE_URL[url] = response;
  } else {
    debug("using cache: " + url);
  }
  
  return response;
}

function log_start(functionName) {
  internal_log(functionName, 2); // #2 is the "start" column
}

function log_stop(functionName) {
  internal_log(functionName, 3); // #3 is the "end" column
}

function internal_log(functionName, column) {
  debug("IN internal_log(" + functionName + ", " + column + ")");
  var sheet_logs = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME_LOGS);
  // NOTE limit range, don't pull more than 50 rows?
  var range = sheet_logs.getRange("A2:D51");
  var row = 0;
  var data = range.getValues();
  for (; row < data.length; row++) {
    var name = data[row][0];
    if (name == functionName) {
      break;
    }
    if (name == "") {
      range.getCell(row+1,1).setValue(functionName);
      break;
    }
  }
  // set self
  range.getCell(row+1,column).setValue(Utilities.formatDate(new Date(), "EST", "yyyy-MM-dd HH:mm:ss 'EST'"));
  // clear to right
  range.getCell(row+1,column+1).setValue("");
  debug("OUT internal_log(" + functionName + ", " + column + ")");
}

function debug(msg) {
  Logger.log(msg);
}

// https://stackoverflow.com/questions/7244246/generate-an-rfc-3339-timestamp-similar-to-google-tasks-api
function ISODateString(d){
  function pad(n){return n<10 ? '0'+n : n}
  return d.getUTCFullYear()+'-'
  + pad(d.getUTCMonth()+1)+'-'
  + pad(d.getUTCDate())+'T'
  + pad(d.getUTCHours())+':'
  + pad(d.getUTCMinutes())+':'
  + pad(d.getUTCSeconds())+'Z'
}

function get_city_for(event) {
  return CACHE_CITY[event.getId()];
}

function set_city_for(event, city) {
  CACHE_CITY[event.getId()] = city;
}

function get_state_for(event) {
  return CACHE_STATE[event.getId()];
}

function set_state_for(event, state) {
  CACHE_STATE[event.getId()] = state;
}

function get_noon_ms() {
  var d = new Date()
  d.setHours(12)
  d.setMinutes(0)
  d.setSeconds(0)
  Logger.log(d.getTime())
  return d.getTime()
}

function dayOfYear(date) {
  var start = new Date(date.getFullYear(), 0, 0);
  var diff = date - start;
  var oneDay = 1000 * 60 * 60 * 24;
  var day = Math.floor(diff / oneDay);
  return day;
}

function addOneDay(date) {
  return adjustDays(date, 1)
}

function adjustDays(date, days) {
  return new Date(date.getTime() + days*24*60*60*1000)
}

function sin(a) {
  return Math.sin(a*Math.PI/180)
}
function asin(x) {
  return Math.asin(x)*(180/Math.PI)
}
function cos(a) {
  return Math.cos(a*Math.PI/180)
}
function acos(x) {
  return Math.acos(x)*(180/Math.PI)
}
function tan(a) {
  return Math.tan(a*Math.PI/180)
}
function atan(x) {
  return Math.atan(x)*(180/Math.PI)
}

function now_ms() {
  return Date.now()
}
