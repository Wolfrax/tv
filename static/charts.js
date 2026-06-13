Highcharts.setOptions({
    time: {
        timezone: 'Europe/Stockholm'
    },
    chart: {
        backgroundColor: 'transparent',
        style: { fontFamily: "'Segoe UI', system-ui, -apple-system, sans-serif" }
    },
    colors: ['#f97316', '#22c55e', '#06b6d4', '#a78bfa', '#f43f5e', '#60a5fa'],
    title: {
        style: { color: '#e2e8f0', fontSize: '13px', fontWeight: '600' }
    },
    subtitle: {
        style: { color: '#7d92b2', fontSize: '11px' }
    },
    xAxis: {
        gridLineColor: '#253554',
        lineColor: '#253554',
        tickColor: '#253554',
        labels: { style: { color: '#7d92b2' } },
        title: { style: { color: '#7d92b2' } }
    },
    yAxis: {
        gridLineColor: '#253554',
        lineColor: '#253554',
        tickColor: '#253554',
        labels: { style: { color: '#7d92b2' } },
        title: { style: { color: '#7d92b2' } }
    },
    legend: {
        itemStyle: { color: '#e2e8f0', fontWeight: '400' },
        itemHoverStyle: { color: '#ffffff' }
    },
    tooltip: {
        backgroundColor: '#131d30',
        borderColor: '#253554',
        style: { color: '#e2e8f0' }
    },
    credits: { enabled: false }
});

function plot_ws(id, Title, yAx, obs) {
    Highcharts.chart(id, {
        chart: {
            type: 'spline',
            shadow: false,
            events: {
                load: function () {
                    var chart = this,
                        points = chart.series[0].points,
                        minValue, maxValue,
                        chosenMinPoint, chosenMaxPoint;

                    points.forEach(function (point) {
                        if (!minValue || minValue > point.y) {
                            minValue = point.y;
                            chosenMinPoint = point;
                        }
                    });

                    points.forEach(function (point) {
                        if (!maxValue || maxValue < point.y) {
                            maxValue = point.y;
                            chosenMaxPoint = point;
                        }
                    });

                    if (chosenMinPoint) {
                        chosenMinPoint.update({
                            marker: { enabled: true },
                            dataLabels: { enabled: true },
                        });
                    }

                    if (chosenMaxPoint) {
                        chosenMaxPoint.update({
                            marker: { enabled: true },
                            dataLabels: { enabled: true },
                        });
                    }
                }
            }
        },
        title: {
            text: Title
        },
        subtitle: {
            text: 'Last 24 hours'
        },
        xAxis: {
            type: 'datetime',
            offset: 40,
            title: { text: 'Time' },
            plotLines: [{ value: new Date().getTime(), dashStyle: 'dash', width: 2, color: '#f43f5e' }]
        },
        yAxis: yAx,
        series: obs
    });
}

function plot_rose(obs, id, Title) {
    const categories = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
    Highcharts.chart(id, {
        series: obs,
        chart: {
            polar: true,
            type: 'column',
            shadow: false
        },
        title: {
            text: Title
        },
        subtitle: {
            text: 'Last 24 hours + forecast'
        },
        legend: {
            align: 'right',
            verticalAlign: 'top',
            y: 100,
            layout: 'vertical'
        },
        xAxis: {
            min: 0,
            max: 360,
            type: '',
            tickInterval: 45,
            tickmarkPlacement: 'on',
            labels: {
                formatter: function () {
                    return categories[this.value / 45];
                }
            }
        },
        yAxis: {
            endOnTick: false,
            showLastLabel: true,
            title: { text: 'Frequency (%)' },
            labels: {
                formatter: function () {
                    return this.value + '%';
                }
            },
            reversedStacks: false
        },
        plotOptions: {
            series: {
                stacking: 'normal',
                shadow: false,
                groupPadding: 0,
                pointPlacement: 'on',
                borderWidth: 0
            }
        }
    });
}
