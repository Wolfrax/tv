Highcharts.setOptions({
    time: {
        timezone: 'Europe/Stockholm'
    }
});

function plot_ws(id, Title, yAx, obs) {
    Highcharts.chart(id, {
        chart: {
            type: 'spline',
            shadow: true,
            events: {
                load: function () {
                    var chart = this,
                        points = chart.series[0].points,
                        minValue, maxValue,
                        chosenMinPoint, chosenMaxPoint;

                    points.forEach(function (point, index) {
                        if (!minValue || minValue > point.y) {
                            minValue = point.y;
                            chosenMinPoint = point;
                        }
                    });

                    points.forEach(function (point, index) {
                        if (!maxValue || maxValue < point.y) {
                            maxValue = point.y;
                            chosenMaxPoint = point;
                        }
                    });

                    if (chosenMinPoint) {
                        chosenMinPoint.update({
                            marker: {
                                enabled: true,
                            },
                            dataLabels: {
                                enabled: true,
                            },
                        });
                    }

                    if (chosenMaxPoint) {
                        chosenMaxPoint.update({
                            marker: {
                                enabled: true,
                            },
                            dataLabels: {
                                enabled: true,
                            },
                        });
                    }
                }
            }

        },
        title: {
            text: Title
        },
        subtitle: {
            text: weather_data.concat ? 'Last 24 hours + forecast' : 'Last 24 hours'
        },
        xAxis: {
            type: 'datetime',
            offset: 40,
            title: {
                text: 'Time'
            },
            plotLines: [{value: new Date().getTime(), dashStyle: 'dash', width: 2, color: '#d33'}]
        },
        yAxis: yAx,
        colors: ['#6CF', '#39F', '#06C', '#036', '#000'],
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
                shadow: true
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
                type: "",
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
                title: {
                    text: 'Frequency (%)'
                },
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
        }
    )
}
