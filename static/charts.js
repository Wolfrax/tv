Highcharts.setOptions({
    time: {
        timezone: 'Europe/Stockholm'
    },
    chart: {
        backgroundColor: '#ffffff',
        style: { fontFamily: "'Segoe UI', system-ui, -apple-system, sans-serif" }
    },
    colors: ['#f97316', '#16a34a', '#0891b2', '#7c3aed', '#e11d48', '#2563eb'],
    title: {
        style: { color: '#0f172a', fontSize: '13px', fontWeight: '600' }
    },
    subtitle: {
        style: { color: '#64748b', fontSize: '11px' }
    },
    xAxis: {
        gridLineColor: '#f1f5f9',
        lineColor: '#e2e8f0',
        tickColor: '#e2e8f0',
        labels: { style: { color: '#64748b' } },
        title: { style: { color: '#64748b' } }
    },
    yAxis: {
        gridLineColor: '#f1f5f9',
        lineColor: '#e2e8f0',
        tickColor: '#e2e8f0',
        labels: { style: { color: '#64748b' } },
        title: { style: { color: '#64748b' } }
    },
    legend: {
        itemStyle: { color: '#0f172a', fontWeight: '400' },
        itemHoverStyle: { color: '#2563eb' }
    },
    tooltip: {
        backgroundColor: '#ffffff',
        borderColor: '#e2e8f0',
        shadow: true,
        style: { color: '#0f172a' }
    },
    credits: { enabled: false }
});

function plot_ws(id, Title, yAx, obs, subtitle) {
    subtitle = subtitle || 'Last 24 hours';
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
            text: subtitle
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

function plot_rose(obs, id, Title, subtitle) {
    subtitle = subtitle || 'Last 24 hours';
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
            text: subtitle
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
