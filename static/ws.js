function table(stn) {
    $('#data').DataTable({
        order: [[0, "desc"]],
        paging: false,
        searching: false,
        info: false,
        ajax: {
            'url': 'tv_ws/_ws',
            'data': {'ind': -7, 'stn': stn}
        },
        columns: [
            {
                data: 'Sample', 'render': function (val) {
                    return new Date(val).toLocaleString("SWE")
                }, orderable: false
            },
            {data: 'Air.Temperature.Value', orderable: false},
            {data: 'Aggregated10minutes.Precipitation.TotalWaterEquivalent.Value', orderable: false},
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

function fc_table(stn) {
    $.getJSON('tv_ws/_ws', {stn: stn}, function (json) {
        $('#fc_data').DataTable({
            order: [[0, "asc"]],
            paging: true,
            searching: false,
            info: true,
            pageLength: 25,
            lengthChange: false,
            ajax: {
                'url': 'forecast/_fc',
                'data': {
                    'lat': json.data[json.data.length - 1].geometry.lat,
                    'lon': json.data[json.data.length - 1].geometry.lon,
                },
                'dataSrc': function (json) {
                    // Remove all elements in forecat that is older than 'now'
                    let now = new Date().getUTCTime();
                    json.data.forEach(elem => {
                        if (new Date(elem.time).getTime() <= now) {
                            json.data.shift();
                        }
                    });
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

function inRange(x) {
    return this[0] <= x[0] && x[0] < this[1]
}

function forecast_plot() {
    plot_data.concat = !plot_data.concat;
    plot();
}

let plot_data = {
    actual: {
        temps: [],
        hums: [],
        rain: [],
        wind: [],
        wind_max: [],
        wind_barb: [],
        wind_dirs: [],
        first_sample: "",
        last_sample: "",
    },
    forecast: {
        temps: [],
        hums: [],
        rain: [],
        wind: [],
        wind_max: [],
        wind_barb: [],
        wind_dirs: [],
        first_sample: "",
        last_sample: "",
    },
    concat: true,
};

function plot() {
    let temps, hums, rain, wind, wind_max, wind_barb, wind_dirs;
    let rain_cum = [];
    let latest_time;

    if (plot_data.concat) {
        // concatenate actual with forecasted values
        temps = plot_data.actual.temps.concat(plot_data.forecast.temps);
        hums = plot_data.actual.hums.concat(plot_data.forecast.hums);
        rain = plot_data.actual.rain.concat(plot_data.forecast.rain);
        wind = plot_data.actual.wind.concat(plot_data.forecast.wind);
        wind_max = plot_data.actual.wind_max.concat(plot_data.forecast.wind_max);
        wind_barb = plot_data.actual.wind_barb.concat(plot_data.forecast.wind_barb);
        wind_dirs = plot_data.actual.wind_dirs.concat(plot_data.forecast.wind_dirs);
        latest_time = new Date(plot_data.actual.first_sample).toLocaleString("SWE") + " to " +
            plot_data.forecast.last_sample
    } else {
        // Use only actual, make a copy
        temps = plot_data.actual.temps.slice();
        hums = plot_data.actual.hums.slice();
        rain = plot_data.actual.rain.slice();
        wind = plot_data.actual.wind.slice();
        wind_max = plot_data.actual.wind_max.slice();
        wind_barb = plot_data.actual.wind_barb.slice();
        wind_dirs = plot_data.actual.wind_dirs.slice();
        latest_time = new Date(plot_data.actual.first_sample).toLocaleString("SWE") + " to " +
            new Date(plot_data.actual.last_sample).toLocaleString("SWE")
    }

    $("#latest_time").html(latest_time);

    rain.reduce(function (a, b, i) {
        return rain_cum[i] = [rain[i][0], Math.round((a[1] + b[1]) * 10) / 10];
    }, rain[0]);

    $("#latest_cum_rain").html("\u03A3" + rain_cum[rain_cum.length - 1][1] + "mm");

    plot_ws('ws_temp', 'Temperature & Humidity',
        [{title: {text: 'Temperature (°C)'}}, {title: {text: 'Humidity (%)'}, opposite: true}],
        [
            {yAxis: 1, name: 'Humidity', data: hums, color: '#6CF', tooltip: {valueSuffix: '%'}},
            {yAxis: 0, name: 'Temperature', data: temps, color: 'gray', tooltip: {valueSuffix: '°C'}}
        ],
    );

    plot_ws('ws_rain', 'Rain',
        [{title: {text: 'Rain (mm)'}}, {title: {text: 'Rain acc (mm)'}, opposite: true}],
        [
            {yAxis: 0, name: 'Rain', data: rain, type: 'area', tooltip: {valueSuffix: 'mm'}},
            {yAxis: 1, name: 'Rain acc', data: rain_cum, tooltip: {valueSuffix: 'mm'}}
        ]
    );

    plot_ws('ws_wind', 'Wind',
        [{title: {text: 'Wind (m/s)'}}],
        [
            {name: 'Wind Max', data: wind_max, type: 'area', tooltip: {valueSuffix: 'm/s'}},
            {name: 'Wind', data: wind, tooltip: {alueSuffix: 'm/s'}},
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

function ws_graph(stn) {
    $.getJSON('tv_ws/_ws', {stn: stn}, function (json) {
        let last = json.data.length - 1

        $("#latest_temp").html(json.data[last].Air.Temperature.Value + "°C");
        $("#latest_hum").html(json.data[last].Air.RelativeHumidity.Value + "%");
        $("#latest_rain").html(json.data[last].Aggregated10minutes.Precipitation.TotalWaterEquivalent.Value + "mm");
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

        $("#latest_wind_dir").html(categories[wind_dir / 45]);

        plot_data.actual.first_sample = json.data[0].Sample;
        plot_data.actual.last_sample = json.data[last].Sample;
        for (const key of Object.keys(json.data)) {
            t = new Date(json.data[key].Sample).getTime();
            plot_data.actual.temps.push([t, json.data[key].Air.Temperature.Value]);
            plot_data.actual.hums.push([t, json.data[key].Air.RelativeHumidity.Value]);
            plot_data.actual.rain.push([t, json.data[key].Aggregated10minutes.Precipitation.TotalWaterEquivalent.Value]);
            if (json.data[key].Wind[0].Speed.Value) {
                plot_data.actual.wind.push([t, json.data[key].Wind[0].Speed.Value]);
            }
            if (json.data[key].Aggregated30minutes.Wind.SpeedMax.Value) {
                plot_data.actual.wind_max.push([t, json.data[key].Aggregated30minutes.Wind.SpeedMax.Value]);
            }
            if (json.data[key].Wind[0].Speed.Value && json.data[key].Wind[0].Direction.Value) {
                plot_data.actual.wind_barb.push([t, json.data[key].Wind[0].Speed.Value, json.data[key].Wind[0].Direction.Value]);
            }
            if (json.data[key].Wind[0].Speed.Value) {
                plot_data.actual.wind_dirs.push([json.data[key].Wind[0].Direction.Value, json.data[key].Wind[0].Speed.Value]);
            }
        }

        let map = L.map('map').setView([json.data[last].geometry.lat, json.data[last].geometry.lon], 14);
        L.tileLayer('https://api.mapbox.com/styles/v1/{id}/tiles/{z}/{x}/{y}?access_token={accessToken}', {
            attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, Imagery © <a href="https://www.mapbox.com/">Mapbox</a>',
            maxZoom: 18,
            id: 'mapbox/streets-v11',
            tileSize: 512,
            zoomOffset: -1,
            accessToken: 'pk.eyJ1IjoiZWNzbWFtZSIsImEiOiJja3hoeWFudDYxODNpMnducHVvc2R3bWQ0In0.XFA2z4SqARYem91PAB_Yag'
        }).addTo(map);
        L.marker([json.data[last].geometry.lat, json.data[last].geometry.lon]).addTo(map);

        $.getJSON('forecast/_fc', {
            lat: json.data[last].geometry.lat,
            lon: json.data[last].geometry.lon,
        }, function (json) {
            // Remove all elements in forecast that is older than 'now'
            let now = new Date().getUTCTime();
            json.data.forEach(elem => {
                if (new Date(elem.time).getTime() <= now) {
                    json.data.shift();
                }
            });

            plot_data.forecast.first_sample = json.data[0].time.slice(0, 19).replace('T', ' ');
            plot_data.forecast.last_sample = json.data[json.data.length - 1].time.slice(0, 19).replace('T', ' ');
            json.data.forEach(function (elem) {
                t = new Date(elem.time).getTime();
                plot_data.forecast.temps.push([t, elem.temp]);
                plot_data.forecast.hums.push([t, elem.hum]);
                plot_data.forecast.rain.push([t, elem.rain]);
                plot_data.forecast.wind.push([t, elem.wind_speed]);
                plot_data.forecast.wind_max.push([t, elem.wind_max]);
                plot_data.forecast.wind_barb.push([t, elem.wind_speed, elem.wind_dir]);
                plot_data.forecast.wind_dirs.push([elem.wind_dir, elem.wind_speed]);
            });

            plot();
        });
    })
}
