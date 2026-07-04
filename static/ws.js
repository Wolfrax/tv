const API_BASE = '/tv_ws';

let currentStn = '';
let stationCoords = { lat: null, lon: null };
let forecastCache = null;

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
        rain: [],
        rain_acc: [],
        wind: [],
        wind_max: [],
        wind_barb: [],
        wind_dir: [],
        first_sample: "",
        last_sample: "",
    },
    concat: false,
};

function table_actual(stn) {
    $('#data').DataTable({
        order: [[0, "desc"]],
        paging: false,
        searching: false,
        info: false,
        ajax: {
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
    $.getJSON('/tv_ws/_ws', {stn: stn}, function (json) {
        $('#fc_data').DataTable({
            order: [[0, "asc"]],
            paging: true,
            searching: false,
            info: true,
            pageLength: 25,
            lengthChange: false,
            ajax: {
                url: API_BASE + '/_fc',
                'data': {
                    'lat': json.data[json.data.length - 1].geometry.lat,
                    'lon': json.data[json.data.length - 1].geometry.lon,
                },
                'dataSrc': function (json) {
                    let now = new Date().getUTCTime();
                    json.data = json.data.filter(elem =>
                        {return new Date(elem.time).getTime() > now;});
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

// Fetch 7-day historical data and SMHI forecast in parallel, then call callback(histJson, fcJson).
// fcJson is null if coordinates aren't known yet or if the SMHI request fails.
// Result is cached so toggling between charts avoids repeated SMHI fetches.
function fetch7dWithForecast(callback) {
    $.getJSON(API_BASE + '/_ws7days', {stn: currentStn}, function (histJson) {
        if (!stationCoords.lat) { callback(histJson, null); return; }
        if (forecastCache)      { callback(histJson, forecastCache); return; }
        $.getJSON(API_BASE + '/_fc', {lat: stationCoords.lat, lon: stationCoords.lon})
            .done(function (fcJson) { forecastCache = fcJson; callback(histJson, fcJson); })
            .fail(function ()       { callback(histJson, null); });
    });
}

function renderRainChart(title, rain, rain_cum, subtitle, fc_rain) {
    Highcharts.charts.forEach(function (c) {
        if (c && c.renderTo && c.renderTo.id === 'ws_rain') c.destroy();
    });
    let series = [
        {yAxis: 0, name: 'Rain',     data: rain,     type: 'area', color: '#06b6d4', tooltip: {valueSuffix: ' mm'}},
        {yAxis: 1, name: 'Rain acc', data: rain_cum,               color: '#a78bfa', tooltip: {valueSuffix: ' mm'}}
    ];
    if (fc_rain && fc_rain.length) series.push(
        {yAxis: 0, name: 'Forecast rain', data: fc_rain, type: 'column', color: '#38bdf8', tooltip: {valueSuffix: ' mm/h'}}
    );
    plot_ws(
        'ws_rain', title,
        [{title: {text: 'Rain (mm)'}}, {title: {text: 'Rain acc (mm)'}, opposite: true}],
        series,
        subtitle
    );
}

function setRainRange(range) {
    document.getElementById('rain-btn-24h').classList.toggle('active', range === '24h');
    document.getElementById('rain-btn-7d').classList.toggle('active', range === '7d');

    if (range === '7d') {
        fetch7dWithForecast(function (histJson, fcJson) {
            let rain7d = histJson.data.map(d => [new Date(d.ts).getTime(), d.rain]);
            let cum7d = [];
            rain7d.reduce(function (a, b, i) {
                return cum7d[i] = [rain7d[i][0], Math.round((a[1] + b[1]) * 10) / 10];
            }, rain7d[0]);
            let fc_rain = fcJson
                ? fcJson.data.filter(d => d.rain != null).map(d => [new Date(d.time).getTime(), d.rain])
                : [];
            let subtitle = fcJson ? 'Last 7 days + forecast' : 'Last 7 days';
            renderRainChart('Rain (7 days)', rain7d, cum7d, subtitle, fc_rain);
        });
    } else {
        let rain = weather_data.actual.rain.slice();
        let cum = [];
        rain.reduce(function (a, b, i) {
            return cum[i] = [rain[i][0], Math.round((a[1] + b[1]) * 10) / 10];
        }, rain[0]);
        renderRainChart('Rain (24 h)', rain, cum, 'Last 24 hours');
    }
}

function renderTempChart(temps, hums, subtitle, fc_temps, fc_hums) {
    Highcharts.charts.forEach(function (c) {
        if (c && c.renderTo && c.renderTo.id === 'ws_temp') c.destroy();
    });
    let series = [
        {yAxis: 0, name: 'Temperature', data: temps, color: '#f97316', tooltip: {valueSuffix: ' °C'}},
        {yAxis: 1, name: 'Humidity',    data: hums,  color: '#22c55e', tooltip: {valueSuffix: ' %'}},
    ];
    if (fc_temps && fc_temps.length) series.push(
        {yAxis: 0, name: 'Forecast temp', data: fc_temps, color: '#f97316', dashStyle: 'Dash', tooltip: {valueSuffix: ' °C'}}
    );
    if (fc_hums && fc_hums.length) series.push(
        {yAxis: 1, name: 'Forecast hum',  data: fc_hums,  color: '#22c55e', dashStyle: 'Dash', tooltip: {valueSuffix: ' %'}}
    );
    plot_ws('ws_temp', 'Temperature & Humidity',
        [
            {
                title: {text: 'Temperature (°C)', style: {color: '#f97316'}},
                labels: {style: {color: '#f97316'}},
                lineWidth: 2, lineColor: '#f97316',
            },
            {
                title: {text: 'Humidity (%)', style: {color: '#22c55e'}},
                labels: {style: {color: '#22c55e'}},
                lineWidth: 2, lineColor: '#22c55e',
                opposite: true,
            }
        ],
        series,
        subtitle
    );
}

function setTempRange(range) {
    document.getElementById('temp-btn-24h').classList.toggle('active', range === '24h');
    document.getElementById('temp-btn-7d').classList.toggle('active', range === '7d');

    if (range === '7d') {
        fetch7dWithForecast(function (histJson, fcJson) {
            let temps = histJson.data.filter(d => d.temp != null).map(d => [new Date(d.ts).getTime(), d.temp]);
            let hums  = histJson.data.filter(d => d.hum  != null).map(d => [new Date(d.ts).getTime(), d.hum]);
            let fc_temps = [], fc_hums = [];
            if (fcJson) {
                fc_temps = fcJson.data.filter(d => d.temp != null).map(d => [new Date(d.time).getTime(), d.temp]);
                fc_hums  = fcJson.data.filter(d => d.hum  != null).map(d => [new Date(d.time).getTime(), d.hum]);
            }
            let subtitle = fcJson ? 'Last 7 days + forecast' : 'Last 7 days';
            renderTempChart(temps, hums, subtitle, fc_temps, fc_hums);
        });
    } else {
        renderTempChart(weather_data.actual.temp.slice(), weather_data.actual.hum.slice(), 'Last 24 hours');
    }
}

function renderWindChart(wind_max, wind, wind_barb, subtitle, fc_wind, fc_wind_max) {
    Highcharts.charts.forEach(function (c) {
        if (c && c.renderTo && c.renderTo.id === 'ws_wind') c.destroy();
    });
    let series = [
        {name: 'Wind Max',  data: wind_max,  type: 'area', color: '#f43f5e', tooltip: {valueSuffix: ' m/s'}},
        {name: 'Wind',      data: wind,                    color: '#a78bfa', tooltip: {valueSuffix: ' m/s'}},
        {name: 'Wind barb', type: 'windbarb', data: wind_barb.filter((v, i) => i % 9 === 0)}
    ];
    if (fc_wind && fc_wind.length) series.push(
        {name: 'Forecast wind',     data: fc_wind,     color: '#a78bfa', dashStyle: 'Dash', tooltip: {valueSuffix: ' m/s'}}
    );
    if (fc_wind_max && fc_wind_max.length) series.push(
        {name: 'Forecast wind max', data: fc_wind_max, color: '#f43f5e', dashStyle: 'Dash', tooltip: {valueSuffix: ' m/s'}}
    );
    plot_ws('ws_wind', 'Wind',
        [{title: {text: 'Wind (m/s)'}}],
        series,
        subtitle
    );
}

function setWindRange(range) {
    document.getElementById('wind-btn-24h').classList.toggle('active', range === '24h');
    document.getElementById('wind-btn-7d').classList.toggle('active', range === '7d');

    if (range === '7d') {
        fetch7dWithForecast(function (histJson, fcJson) {
            let wind     = histJson.data.filter(d => d.wind     != null).map(d => [new Date(d.ts).getTime(), d.wind]);
            let wind_max = histJson.data.filter(d => d.wind_max != null).map(d => [new Date(d.ts).getTime(), d.wind_max]);
            let wind_barb = histJson.data.filter(d => d.wind != null && d.wind_dir != null)
                                         .map(d => [new Date(d.ts).getTime(), d.wind, d.wind_dir]);
            let fc_wind = [], fc_wind_max = [];
            if (fcJson) {
                fc_wind     = fcJson.data.filter(d => d.wind_speed != null).map(d => [new Date(d.time).getTime(), d.wind_speed]);
                fc_wind_max = fcJson.data.filter(d => d.wind_max  != null).map(d => [new Date(d.time).getTime(), d.wind_max]);
            }
            let subtitle = fcJson ? 'Last 7 days + forecast' : 'Last 7 days';
            renderWindChart(wind_max, wind, wind_barb, subtitle, fc_wind, fc_wind_max);
        });
    } else {
        renderWindChart(
            weather_data.actual.wind_max.slice(),
            weather_data.actual.wind.slice(),
            weather_data.actual.wind_barb.slice(),
            'Last 24 hours'
        );
    }
}

function buildWindRose(wind_dirs) {
    function inRange(x) {
        return this[0] <= x[0] && x[0] < this[1];
    }
    wind_dirs.sort((a, b) => a[0] - b[0]);
    const wind_dirs_max = wind_dirs.reduce((a, b) => Math.max(a, b[1]), 0);
    let histGenerator = d3.bin()
        .domain([0, wind_dirs_max])
        .value(d => d[1])
        .thresholds([0.5, 2, 4, 6, 8, 10]);
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
    return wind_freq;
}

function renderWindRose(wind_dirs, subtitle) {
    Highcharts.charts.forEach(function (c) {
        if (c && c.renderTo && c.renderTo.id === 'ws_windrose') c.destroy();
    });
    const wind_freq = buildWindRose(wind_dirs);
    plot_rose([
        {name: '<0.5 m/s',  data: wind_freq[0]},
        {name: '0.5-2 m/s', data: wind_freq[1]},
        {name: '2-4 m/s',   data: wind_freq[2]},
        {name: '4-6 m/s',   data: wind_freq[3]},
        {name: '6-8 m/s',   data: wind_freq[4]},
        {name: '8-10 m/s',  data: wind_freq[5]},
        {name: '>10 m/s',   data: wind_freq[6]}
    ], 'ws_windrose', 'Wind', subtitle);
}

function setWindRoseRange(range) {
    document.getElementById('rose-btn-24h').classList.toggle('active', range === '24h');
    document.getElementById('rose-btn-7d').classList.toggle('active', range === '7d');

    if (range === '7d') {
        fetch7dWithForecast(function (histJson, fcJson) {
            let wind_dirs = histJson.data
                .filter(d => d.wind != null && d.wind_dir != null)
                .map(d => [d.wind_dir, d.wind]);
            if (fcJson) {
                let fc_dirs = fcJson.data
                    .filter(d => d.wind_speed != null && d.wind_dir != null)
                    .map(d => [d.wind_dir, d.wind_speed]);
                wind_dirs = wind_dirs.concat(fc_dirs);
            }
            let subtitle = fcJson ? 'Last 7 days + forecast' : 'Last 7 days';
            renderWindRose(wind_dirs, subtitle);
        });
    } else {
        renderWindRose(weather_data.actual.wind_dir.slice(), 'Last 24 hours');
    }
}

// Local midnight is always within the trailing 24h window ws.json carries,
// so the same "rain" series used for the 24h total covers it - no extra
// fetch needed.
function rainSinceMidnight(rain) {
    const midnight = new Date();
    midnight.setHours(0, 0, 0, 0);
    const cutoff = midnight.getTime();

    let sum = 0;
    rain.forEach(function (point) {
        if (point[0] >= cutoff) {
            const val = parseFloat(point[1]);
            if (!isNaN(val)) sum += val;
        }
    });

    return Math.round(sum * 10) / 10;
}

function plot() {
    let rain_cum = [];

    const temps     = weather_data.actual.temp.slice();
    const hums      = weather_data.actual.hum.slice();
    const rain      = weather_data.actual.rain.slice();
    const wind      = weather_data.actual.wind.slice();
    const wind_max  = weather_data.actual.wind_max.slice();
    const wind_barb = weather_data.actual.wind_barb.slice();
    const wind_dirs = weather_data.actual.wind_dir.slice();

    const latest_time = new Date(weather_data.actual.first_sample).toLocaleString("SWE") + " to " +
        new Date(weather_data.actual.last_sample).toLocaleString("SWE");
    $("#latest_time").html(latest_time);

    rain.reduce(function (a, b, i) {
        return rain_cum[i] = [rain[i][0], Math.round((a[1] + b[1]) * 10) / 10];
    }, rain[0]);

    $("#latest_cum_rain").html("Σ" + rainSinceMidnight(rain) + "mm");

    renderTempChart(temps, hums, 'Last 24 hours');
    renderRainChart('Rain', rain, rain_cum, 'Last 24 hours');
    renderWindChart(wind_max, wind, wind_barb, 'Last 24 hours');
    renderWindRose(wind_dirs, 'Last 24 hours');
}

function getData_plot(stn) {
    currentStn = stn;
    $.getJSON('/tv_ws/_ws', {stn: stn}, function (json) {
        let last = json.data.length - 1

        $("#latest_temp").html(json.data[last].Air.Temperature.Value + "°C");
        $("#latest_hum").html(json.data[last].Air.RelativeHumidity.Value + "%");
        $("#latest_rain").html(json.data[last].Aggregated5minutes.Precipitation.TotalWaterEquivalent.Value + "mm/5m");
        let rain_acc = 0.0;
        json.data.forEach(elem => {
            let val = parseFloat(elem.Aggregated5minutes.Precipitation.TotalWaterEquivalent.Value);
            if (isNaN(val)) val = 0.0;
            rain_acc += val;
        });
        $("#latest_day_rain").html(Math.round(rain_acc * 10) / 10 + "mm/24h");

        let wind_speed = json.data[last].Wind[0].Speed.Value ? json.data[last].Wind[0].Speed.Value : " --- ";
        let wind_dir = json.data[last].Wind[0].Direction.Value !== null ? json.data[last].Wind[0].Direction.Value : " --- ";
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

        weather_data.actual.first_sample = json.data[0].Sample;
        weather_data.actual.last_sample = json.data[last].Sample;

        stationCoords = {
            lat: json.data[last].geometry.lat,
            lon: json.data[last].geometry.lon,
        };

        for (const key of Object.keys(json.data)) {
            let t = new Date(json.data[key].Sample).getTime();
            weather_data.actual.temp.push([t, json.data[key].Air.Temperature.Value]);
            weather_data.actual.hum.push([t, json.data[key].Air.RelativeHumidity.Value]);
            weather_data.actual.rain.push([t, json.data[key].Aggregated5minutes.Precipitation.TotalWaterEquivalent.Value]);

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

        let map = L.map('map', {dragging: false}).setView([json.data[last].geometry.lat, json.data[last].geometry.lon], 10);
        L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 20
        }).addTo(map);
        L.marker([json.data[last].geometry.lat, json.data[last].geometry.lon]).addTo(map);

        plot();
    });

    $.getJSON(API_BASE + '/_ws7dayssum', {stn: stn}, function (json) {
       $("#latest_7days_rain").html(Math.round(json.data * 10) / 10 + "mm/7d");
    });
}
