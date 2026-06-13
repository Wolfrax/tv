// weather data is collected to the weather_data object,
//   actual from trafikverket
//   forecast from SMHI
//   concat is a flag, indicating if actual and forecast data should be concatenated

const API_BASE = '/tv_ws';

let currentStn = '';

let weather_data = {
    actual: {
        temp: [],
        hum: [],
        rain: [],
        rain_acc: [],
        wind: [],
        wind_max: [],
        wind_barb: [],
        wind_dir: [],
        first_sample: "",
        last_sample: "",
    },
    forecast: {
        temp: [],
        hum: [],
        rain: [],     // mm/5min (normalized to match actual unit)
        rain_acc: [], // mm/period (original SMHI values, for accumulation curve)
        wind: [],
        wind_max: [],
        wind_barb: [],
        wind_dir: [],
        first_sample: "",
        last_sample: "",
    },
    concat: true,
};

function table_actual(stn) {
    // Make a table for actual values, 1 hour
    $('#data').DataTable({
        order: [[0, "desc"]],
        paging: false,
        searching: false,
        info: false,
        ajax: {
            //'url': 'tv_ws/_ws',
            'url': API_BASE + '/_ws',
            'data': {'ind': 1, 'stn': stn}
        },
        columns: [
            {
                data: 'Sample', 'render': function (val) {
                    return new Date(val).toLocaleString("SWE")
                }, orderable: false
            },
            {data: 'Air.Temperature.Value', orderable: false},
            {data: 'Aggregated5minutes.Precipitation.TotalWaterEquivalent.Value', orderable: false},
            {data: 'Air.RelativeHumidity.Value', orderable: false},
            {data: 'Wind[0].Speed.Value', orderable: false},
            {data: 'Aggregated30minutes.Wind.SpeedMax.Value', orderable: false},
            {data: 'Wind[0].Direction.Value', orderable: false}
        ],
    });
}

// https://stackoverflow.com/a/40785593
Date.prototype.getUTCTime = function () {
    return this.getTime() - (this.getTimezoneOffset() * 60000);
};

function table_forecast(stn) {
    //$.getJSON('tv_ws/_ws', {stn: stn}, function (json) {
        $.getJSON('/tv_ws/_ws', {stn: stn}, function (json) {
        $('#fc_data').DataTable({
            order: [[0, "asc"]],
            paging: true,
            searching: false,
            info: true,
            pageLength: 25,
            lengthChange: false,
            ajax: {
                //'url': 'forecast/_fc',
                url: API_BASE + '/_fc',
                'data': {
                    'lat': json.data[json.data.length - 1].geometry.lat,
                    'lon': json.data[json.data.length - 1].geometry.lon,
                },
                'dataSrc': function (json) {
                    // Remove all elements in forecast that is older than 'now'
                    let now = new Date().getUTCTime();
                    json.data = json.data.filter(elem => 
                        {return new Date(elem.time).getTime() > now;});
                    //json.data.forEach(elem => {
                    //    if (new Date(elem.time).getTime() <= now) {
                    //        json.data.shift();
                    //    }
                    //});
                    return json.data;
                },
            },
            columns: [
                {
                    data: 'time', 'render': function (val) {
                        return val.slice(0, 19).replace('T', ' ')
                    }, orderable: false
                },
                {data: 'temp', orderable: false},
                {data: 'rain', orderable: false},
                {data: 'hum', orderable: false},
                {data: 'wind_speed', orderable: false},
                {data: 'wind_max', orderable: false},
                {data: 'wind_dir', orderable: false}
            ],
        })
    });
}

function concat() {
    weather_data.concat = !weather_data.concat;
    plot();
}

function renderRainChart(title, rain, rain_cum) {
    Highcharts.charts.forEach(function (c) {
        if (c && c.renderTo && c.renderTo.id === 'ws_rain') c.destroy();
    });
    plot_ws(
        'ws_rain', title,
        [{title: {text: 'Rain (mm)'}}, {title: {text: 'Rain acc (mm)'}, opposite: true}],
        [
            {yAxis: 0, name: 'Rain',     data: rain,     type: 'area', color: '#06b6d4', tooltip: {valueSuffix: 'mm'}},
            {yAxis: 1, name: 'Rain acc', data: rain_cum,               color: '#a78bfa', tooltip: {valueSuffix: 'mm'}}
        ]
    );
}

function setRainRange(range) {
    document.getElementById('rain-btn-24h').classList.toggle('active', range === '24h');
    document.getElementById('rain-btn-7d').classList.toggle('active', range === '7d');

    if (range === '7d') {
        $.getJSON(API_BASE + '/_ws7days', {stn: currentStn}, function (json) {
            let rain7d = json.data.map(d => [new Date(d.ts).getTime(), d.rain]);
            let cum7d = [];
            rain7d.reduce(function (a, b, i) {
                return cum7d[i] = [rain7d[i][0], Math.round((a[1] + b[1]) * 10) / 10];
            }, rain7d[0]);
            renderRainChart('Rain (7 days)', rain7d, cum7d);
        });
    } else {
        // Re-render 24 h view from existing weather_data
        let rain = weather_data.concat
            ? weather_data.actual.rain.concat(weather_data.forecast.rain)
            : weather_data.actual.rain.slice();
        let rain_for_acc = weather_data.concat
            ? weather_data.actual.rain.concat(weather_data.forecast.rain_acc)
            : weather_data.actual.rain.slice();
        let cum = [];
        rain_for_acc.reduce(function (a, b, i) {
            return cum[i] = [rain_for_acc[i][0], Math.round((a[1] + b[1]) * 10) / 10];
        }, rain_for_acc[0]);
        renderRainChart('Rain (24 h)', rain, cum);
    }
}

function plot() {
    function inRange(x) {
        return this[0] <= x[0] && x[0] < this[1]
    }

    let temps, hums, rain, wind, wind_max, wind_barb, wind_dirs;
    let rain_cum = [];
    let latest_time;

    if (weather_data.concat) {
        // concatenate actual with forecasted values
        temps = weather_data.actual.temp.concat(weather_data.forecast.temp);
        hums = weather_data.actual.hum.concat(weather_data.forecast.hum);
        rain = weather_data.actual.rain.concat(weather_data.forecast.rain);
        wind = weather_data.actual.wind.concat(weather_data.forecast.wind);
        wind_max = weather_data.actual.wind_max.concat(weather_data.forecast.wind_max);
        wind_barb = weather_data.actual.wind_barb.concat(weather_data.forecast.wind_barb);
        wind_dirs = weather_data.actual.wind_dir.concat(weather_data.forecast.wind_dir);
        latest_time = new Date(weather_data.actual.first_sample).toLocaleString("SWE") + " to " +
            weather_data.forecast.last_sample
    } else {
        // Use only actual, make a copy
        temps = weather_data.actual.temp.slice();
        hums = weather_data.actual.hum.slice();
        rain = weather_data.actual.rain.slice();
        wind = weather_data.actual.wind.slice();
        wind_max = weather_data.actual.wind_max.slice();
        wind_barb = weather_data.actual.wind_barb.slice();
        wind_dirs = weather_data.actual.wind_dir.slice();
        latest_time = new Date(weather_data.actual.first_sample).toLocaleString("SWE") + " to " +
            new Date(weather_data.actual.last_sample).toLocaleString("SWE")
    }

    $("#latest_time").html(latest_time);

    // Build accumulation series using original mm/period SMHI values so the
    // total stays correct even though 'rain' bars are normalised to mm/5min.
    const rain_for_acc = weather_data.concat
        ? weather_data.actual.rain.concat(weather_data.forecast.rain_acc)
        : weather_data.actual.rain.slice();

    rain_for_acc.reduce(function (a, b, i) {
        return rain_cum[i] = [rain_for_acc[i][0], Math.round((a[1] + b[1]) * 10) / 10];
    }, rain_for_acc[0]);

    $("#latest_cum_rain").html("\u03A3" + rain_cum[rain_cum.length - 1][1] + "mm");

    plot_ws('ws_temp', 'Temperature & Humidity',
        [
            {
                title: {
                    text: 'Temperature (°C)',
                    style: {color: '#f97316'}
                },
                labels: {
                    style: {color: '#f97316'}
                },
                lineWidth: 2,
                lineColor: '#f97316',
            },
            {
                title: {
                    text: 'Humidity (%)',
                    style: {color: '#22c55e'}
                },
                labels: {
                    style: {color: '#22c55e'}
                },
                lineWidth: 2,
                lineColor: '#22c55e',
                opposite: true,
            }
        ],
        [
            {
                yAxis: 0,
                name: 'Temperature',
                data: temps,
                color: '#f97316',
                tooltip: {valueSuffix: '°C'},
            },
            {
                yAxis: 1,
                name: 'Humidity',
                data: hums,
                color: '#22c55e',
                tooltip: {valueSuffix: '%'},
            },
        ],
    );

    renderRainChart('Rain', rain, rain_cum);

    plot_ws('ws_wind', 'Wind',
        [{title: {text: 'Wind (m/s)'}}],
        [
            {name: 'Wind Max', data: wind_max, type: 'area', color: '#f43f5e', tooltip: {valueSuffix: 'm/s'}},
            {name: 'Wind', data: wind, color: '#a78bfa', tooltip: {valueSuffix: 'm/s'}},
            {
                name: 'Wind barb', type: 'windbarb', data: wind_barb.filter(
                    function (value, index) {
                        return index % 9 === 0;
                    })
            }
        ]
    );

    wind_dirs.sort(function (a, b) {
        return a[0] - b[0];
    });

    // Create a wind rose diagram. First make histogram bins for wind speeds (0 - 0.5, 0.5 - 2, ...)
    // The loop over these bins and count how many values are in ranges 0 - 45, 45 - 90, ...
    // Store [wind direction, frequency (%)] elements in wind_freq array, submit to plotting of the rose
    const wind_dirs_max = wind_dirs.reduce(function (a, b) {
        return Math.max(a, b[1]);
    }, 0);

    let histGenerator = d3.bin()
        .domain([0, wind_dirs_max])
        .value(d => d[1])
        .thresholds([0.5, 2, 4, 6, 8, 10])
    let wind_speed_bins = histGenerator(wind_dirs);

    const wind_freq = [];
    for (let i = 0; i < wind_speed_bins.length; i++) {
        const freq_elem = [];
        for (let j = 0; j <= 7; j++) {
            let freq = wind_speed_bins[i].filter(inRange, [j * 45, (j + 1) * 45]).length / wind_dirs.length;
            freq_elem.push([j * 45, (Math.round(freq * 10000) / 10000) * 100]);
        }
        wind_freq.push(freq_elem);
    }

    plot_rose([
        {name: '<0.5 m/s', data: wind_freq[0]},
        {name: '0.5-2 m/s', data: wind_freq[1]},
        {name: '2-4 m/s', data: wind_freq[2]},
        {name: '4-6 m/s', data: wind_freq[3]},
        {name: '6-8 m/s', data: wind_freq[4]},
        {name: '8-10 m/s', data: wind_freq[5]},
        {name: '>10 m/s', data: wind_freq[6]}
    ], 'ws_windrose', 'Wind');

}

function getData_plot(stn) {
    currentStn = stn;
    $.getJSON('/tv_ws/_ws', {stn: stn}, function (json) {
        let last = json.data.length - 1

        $("#latest_temp").html(json.data[last].Air.Temperature.Value + "°C");
        $("#latest_hum").html(json.data[last].Air.RelativeHumidity.Value + "%");
        $("#latest_rain").html(json.data[last].Aggregated5minutes.Precipitation.TotalWaterEquivalent.Value + "mm/5m");
        let rain_acc = 0.0 ;
        json.data.forEach(elem => {
            let val = parseFloat(elem.Aggregated5minutes.Precipitation.TotalWaterEquivalent.Value);
            //if (val == NaN) val = 0.0;
            if (isNaN(val)) val = 0.0;
            rain_acc += val;
        });
        $("#latest_day_rain").html(Math.round(rain_acc * 10) / 10 + "mm/24h");

        let wind_speed = json.data[last].Wind[0].Speed.Value ? json.data[last].Wind[0].Speed.Value : " --- "
        let wind_dir = json.data[last].Wind[0].Direction.Value !== null ? json.data[last].Wind[0].Direction.Value : " --- "
        $("#latest_wind_speed").html(wind_speed + "m/s");

        const categories = [
            'N' + '<i class="bi bi-arrow-down"></i>',
            'NE' + '<i class="bi bi-arrow-down-left"></i>',
            'E' + '<i class="bi bi-arrow-left"></i>',
            'SE' + '<i class="bi bi-arrow-up-left"></i>',
            'S' + '<i class="bi bi-arrow-up"></i>',
            'SW' + '<i class="bi bi-arrow-up-right"></i>',
            'W' + '<i class="bi bi-arrow-right"></i>',
            'NW' + '<i class="bi bi-arrow-down-right"></i>'];

        // Direction is in degrees (0-360); round to nearest 45° compass point
        let dirIndex = (typeof wind_dir === 'number') ? Math.round(wind_dir / 45) % 8 : null;
        $("#latest_wind_dir").html(dirIndex !== null ? categories[dirIndex] : '—');

        // Now fill weather_data object with actual values
        weather_data.actual.first_sample = json.data[0].Sample;
        weather_data.actual.last_sample = json.data[last].Sample;

        for (const key of Object.keys(json.data)) {
            t = new Date(json.data[key].Sample).getTime();
            weather_data.actual.temp.push([t, json.data[key].Air.Temperature.Value]);
            weather_data.actual.hum.push([t, json.data[key].Air.RelativeHumidity.Value]);
            weather_data.actual.rain.push([t, json.data[key].Aggregated5minutes.Precipitation.TotalWaterEquivalent.Value]);

            // Below values are tested for null, this might occur as some stations doesn't measure wind
            if (json.data[key].Wind[0].Speed.Value) {
                weather_data.actual.wind.push([t, json.data[key].Wind[0].Speed.Value]);
            }
            if (json.data[key].Aggregated30minutes.Wind.SpeedMax.Value) {
                weather_data.actual.wind_max.push([t, json.data[key].Aggregated30minutes.Wind.SpeedMax.Value]);
            }
            if (json.data[key].Wind[0].Speed.Value && json.data[key].Wind[0].Direction.Value) {
                weather_data.actual.wind_barb.push([t, json.data[key].Wind[0].Speed.Value, json.data[key].Wind[0].Direction.Value]);
            }
            if (json.data[key].Wind[0].Speed.Value) {
                weather_data.actual.wind_dir.push([json.data[key].Wind[0].Direction.Value, json.data[key].Wind[0].Speed.Value]);
            }
        }

        // Draw a map, and put a marker for the station
        let map = L.map('map', {dragging: false}).setView([json.data[last].geometry.lat, json.data[last].geometry.lon], 10);
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 20
        }).addTo(map);
        L.marker([json.data[last].geometry.lat, json.data[last].geometry.lon]).addTo(map);

        // Now get forecast data from SMHI
        //$.getJSON('forecast/_fc', {
        $.getJSON('/tv_ws/_fc', {
            lat: json.data[last].geometry.lat,
            lon: json.data[last].geometry.lon,
        }, function (json) {
            // Remove all elements in forecast that is older than 'now', thus avoiding overlap with actual
            let now = new Date().getUTCTime();
            json.data.forEach(elem => {
                if (new Date(elem.time).getTime() <= now) {
                    json.data.shift();
                }
            });

            // Now fill weather_data object with forecast values
            weather_data.forecast.first_sample = json.data[0].time.slice(0, 19).replace('T', ' ');
            weather_data.forecast.last_sample = json.data[json.data.length - 1].time.slice(0, 19).replace('T', ' ');

            json.data.forEach(function (elem, index) {
                let t = new Date(elem.time).getTime();

                // SMHI precipitation_amount_max is mm per forecast interval (1h, 3h, …).
                // Compute the interval so we can normalise to mm/5min, matching the
                // Trafikverket Aggregated5minutes unit used for the actual series.
                let intervalMin;
                if (index + 1 < json.data.length) {
                    intervalMin = (new Date(json.data[index + 1].time).getTime() - t) / 60000;
                } else {
                    intervalMin = index > 0
                        ? (t - new Date(json.data[index - 1].time).getTime()) / 60000
                        : 60;
                }

                weather_data.forecast.temp.push([t, elem.temp]);
                weather_data.forecast.hum.push([t, elem.hum]);
                weather_data.forecast.rain.push([t, Math.round(elem.rain * 5 / intervalMin * 1000) / 1000]);
                weather_data.forecast.rain_acc.push([t, elem.rain]);
                weather_data.forecast.wind.push([t, elem.wind_speed]);
                weather_data.forecast.wind_max.push([t, elem.wind_max]);
                weather_data.forecast.wind_barb.push([t, elem.wind_speed, elem.wind_dir]);
                weather_data.forecast.wind_dir.push([elem.wind_dir, elem.wind_speed]);
            });

            plot();
        });
    });

    //$.getJSON('tv_ws/_ws7dayssum', {stn: stn}, function (json) {
    $.getJSON(API_BASE + '/_ws7dayssum', {stn: stn}, function (json) {
       $("#latest_7days_rain").html(Math.round(json.data * 10) / 10 + "mm/7d");
    });
}
