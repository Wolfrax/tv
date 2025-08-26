# TV - reading weather information from Trafikverket and SMHI

In Sweden, Trafikverket (Swedish Transport Administration) have a 
[country wide network of weather stations](https://www.trafikverket.se/tjanster/trafiktjanster/VViS/) to monitor
road conditions. The primary purpose is to use data for managing of roads, but data is available through
an [Open API](https://api.trafikinfo.trafikverket.se/).

This implementation reads data from selected station recurrently (when new data is produced) and store into a file. 
The implementation store and plot 24 hours of data at most. At the same time it reads 
[progonse data from SMHI](http://opendata.smhi.se/apidocs/metfcst/index.html)

As an example, weather data for station "Lund N" is [here](https://www.viltstigen.se/tv_ws?stn=Lund)

Any station available can be read by using its name, refer to this [map](https://www.trafikverket.se/trafikinformation/vag/?TrafficType=personalTraffic&map=1%2F606442.17%2F6886316.22%2F&Layers=RoadWeather%2b)
and zoom in to find the right name. Data from SMHI uses the coordinates from the station.

To use the API, an authorization key is needed, a [registration](https://api.trafikinfo.trafikverket.se/Account/Register)
is needed (free of charge). The key is available there.
Place the key in file `auth.yml` (in the same directory as `ws.py`) using syntax:

    auth:
        key: 71fa8aa80d...
    
There are some specifics to the implementation described below.

## SSE
Trafikverkets servers use [Server Side Events (SSE)](https://en.wikipedia.org/wiki/Server-sent_events) to subscribe
for data. For this purpose, the implementation use [sseclient](https://github.com/btubbs/sseclient) in a loop.

As the connection is exposed to reset-errors the value of `eventid` from the server needs to be passed as parameter value
to `lasteventid` to re-establish the connection.

A typical frequency of new data is every 10 minute (but might vary between stations).

## UI
The frontend (webpage) use [bootstrap](https://getbootstrap.com/) and [highcharts](https://www.highcharts.com/) to
display data.

`ws_emitter.py` is the server process, using flask and templates to generate HTML. At a request to Index ("/"), flask 
render the template `ws.html`. These libraries are loaded:

* bootstrap and bootstrap-icons
* jQuery dataTables
* highcharts and highcharts windbarb
* D3
* Leaflet

Layout of UI is done through bootstrap, plotting through highcharts and a table of data through jQuery. Map for
position of station is done through leaflet.
Special care is taken to draw a windrose, D3 is used to create the bins for the histogram used as input for the Windrose.