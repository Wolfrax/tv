# TV - reading weather information from Trafikverket

In Sweden, Trafikverket (Swedish Transport Administration) have a 
[country wide network of weather stations](https://www.trafikverket.se/tjanster/trafiktjanster/VViS/) to monitor
road conditions. The primary purpose is to use data for managing of roads, but data is available through
an [Open API](https://api.trafikinfo.trafikverket.se/).

This implementation reads data from selected station recurrently (when new data is produced), store into a file and
produces some plots as png-files and an HTML-file. The implementation store and plot 24 hours of data at most.

As an example, weather data for station "Lund N" is [here](https://www.viltstigen.se/tv_ws/)

Any station available can be read by using its name, refer to this [map](https://www.trafikverket.se/trafikinformation/vag/?TrafficType=personalTraffic&map=1%2F606442.17%2F6886316.22%2F&Layers=RoadWeather%2b)
and zoom in to find the right name.

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

# Plotting
This implementation use [matplotlib](https://matplotlib.org/index.html), partly for training purposes.
The windrose plotting use [python-windrose](https://github.com/python-windrose/windrose) for convience.

As plotting is made recurrently, every time new data is available, matplot memory needs to be released. For this purpose
I use do the plotting in a seprate process that is started/terminated for each plotting instance.
