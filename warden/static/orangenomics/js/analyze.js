$(document).ready(function () {
    pie_chart_data = data.CHARTS.pie_chart;
    draw_pie_chart(pie_chart_data, 'allocation', 'pie_chart');
    draw_all_assets_chart(data.CHARTS.all_assets_data, 'all_assets_chart', 'All Assets');
    draw_rolling_correlation_chart(data.CHARTS.rolling_correlation, 'rolling_correlation_chart', 'Rolling Correlation of Assets and Bitcoin');
    draw_all_assets_chart(data.CHARTS.all_portfolios_data, 'all_portfolios_chart', 'Including BTC to Portfolio');
    draw_scatter_chart(data.CHARTS.scatter_charts.assets, 'scatter_assets_chart', 'Scatter Plot of Daily Returns', 'Click on legend to toggle assets');
    draw_scatter_chart(data.CHARTS.scatter_charts.portfolios, 'scatter_portfolios_chart', 'Scatter Plot of Daily Returns', 'Click on legend to toggle assets');
    draw_allocation_chart(data.CHARTS.allocation[0], 'allocation_chart')
    draw_correlation_table(data.TABLES.correlation_matrix, 'correlation_matrix');
    build_trellis(portfolio = true);
    build_trellis(portfolio = false);
    red_green();
});



function draw_correlation_table(data, element) {

    function getPointCategoryName(point, dimension) {
        var series = point.series,
            isY = dimension === 'y',
            axis = series[isY ? 'yAxis' : 'xAxis'];
        return axis.categories[point[isY ? 'y' : 'x']];
    }

    Highcharts.chart(element, {
        chart: {
            type: 'heatmap',
            plotBorderWidth: 2,
        },
        credits: {
            enabled: false
        },

        title: {
            text: ''
        },

        xAxis: {
            categories: data.categories,
            reversed: true,
            opposite: true,
        },

        yAxis: {
            categories: data.categories,
            title: null,
            // reversed: true
        },
        colorAxis: {
            stops: [
                [0.0, '#ffffff'],
                [0.1, '#ffffff'],
                [0.99, '#fd7e14']
            ],
            min: -5
        },

        legend: {
            align: 'right',
            layout: 'vertical',
            margin: 0,
            verticalAlign: 'top',
            y: 25,
            symbolHeight: 280
        },

        tooltip: {
            backgroundColor: '#b3b3b3',
            formatter: function () {
                return '<b>' + getPointCategoryName(this.point, 'x') + '</b> has a correlation of<br>' +
                    formatNumber(this.point.value, 2) + '% with ' + getPointCategoryName(this.point, 'y') + '</b>';
            }
        },

        series: [{
            name: 'Correlation',
            borderWidth: 1,
            data: data.data,
            dataLabels: {
                enabled: true,
                color: '#000000',
                format: '{point.value:.2f}%',
            }
        }],

    });


}


function change_allocation(alloc, element) {
    $(".alloc-butt").removeClass("btn-outline-success")
    $(".alloc-butt").addClass("btn-outline-light")
    $(element).addClass("btn-outline-success")
    $(element).removeClass("btn-outline-light")
    d = window.data.CHARTS.allocation[alloc]
    draw_allocation_chart(d, 'allocation_chart', redraw = true)
}

function draw_allocation_chart(data, element, redraw = false) {
    var myChart = Highcharts.stockChart(element, {
        credits: {
            enabled: false
        },
        navigator: {
            enabled: false
        },
        rangeSelector: {
            enabled: false
        },
        chart: {
            zoomType: 'x',
        },
        title: {
            text: 'Historical Portfolio Allocation (%)',
            align: 'center'
        },
        subtitle: {
            text: '',
            align: 'left'
        },
        xAxis: {
            type: 'datetime'
        },
        yAxis: {
            min: 0,
            max: 100
        },
        legend: {
            enabled: true,
            align: 'right'
        },
        series: data,
        plotOptions: {
            series: {
                data: {
                    minFontSize: 5,
                    maxFontSize: 15
                },
                label: {
                    connectorAllowed: false
                }
            },
            area: {
                stacking: 'percent',
                lineColor: '#ffffff',
                lineWidth: 1,
                marker: {
                    lineWidth: 1,
                    lineColor: '#ffffff'
                }
            }
        },
        tooltip: {
            pointFormat: '<span style="color:{series.color}">{series.name}</span>: <b>{point.percentage:,.2f}%<br/>',
            split: true
        }
    });

    if (redraw == true) {
        myChart.redraw();
    }

};

function draw_scatter_chart(data, element, title, subtitle) {
    Highcharts.chart(element, {
        credits: {
            enabled: false
        },
        chart: {
            type: 'scatter',
            zoomType: 'xy'
        },
        title: {
            text: title,
        },
        subtitle: {
            text: subtitle,
        },
        xAxis: {
            title: {
                enabled: true,
                text: 'Portfolio Return'
            },
            startOnTick: true,
            endOnTick: true,
            showLastLabel: true,
            min: -0.10,
            max: 0.10,
        },
        yAxis: {
            min: -0.10,
            max: 0.10,
            title: {
                text: 'Asset Return'
            }
        },
        legend: {
            layout: 'vertical',
            align: 'right',
            verticalAlign: 'top',
            y: 50,
            floating: true,
            backgroundColor: Highcharts.defaultOptions.chart.backgroundColor,
            borderWidth: 1
        },
        plotOptions: {
            scatter: {
                marker: {
                    radius: 2,
                    symbol: "circle",
                    // states: {
                    //     hover: {
                    //         enabled: true,
                    //         lineColor: 'rgb(100,100,100)'
                    //     }
                    // }
                },
                states: {
                    hover: {
                        marker: {
                            enabled: false
                        }
                    }
                },
                tooltip: {
                    headerFormat: '<b>{series.name}</b><br>',
                    pointFormat: '{point.x}, {point.y}'
                }
            }
        },
        series: data
    });

}


function draw_all_assets_chart(data, element, title) {
    Highcharts.stockChart(element, {
        rangeSelector: {
            selected: 3
        },
        credits: {
            enabled: false
        },
        title: {
            text: title
        },
        yAxis: {
            labels: {
                formatter: function () {
                    return (this.value > 0 ? ' + ' : '') + this.value + '%';
                }
            },
            plotLines: [{
                value: 0,
                width: 2,
                color: 'silver'
            }]
        },

        plotOptions: {
            series: {
                compare: 'percent',
                showInNavigator: true
            }
        },
        legend: {
            enabled: true,
            verticalAlign: 'top',
        },
        tooltip: {
            pointFormat: '<span style="color:{series.color}">{series.name}</span>: <b>{point.y}</b> ({point.change}%)<br/>',
            valueDecimals: 2,
            split: true
        },
        series: data
    });

}



function draw_rolling_correlation_chart(data, element, title) {
    Highcharts.stockChart(element, {

        chart: {
            type: 'spline',
            zoomType: 'xy'
        },
        credits: {
            enabled: false
        },
        rangeSelector: {
            selected: 3
        },
        title: {
            text: title
        },
        yAxis: {
            labels: {
                formatter: function () {
                    return (this.value > 0 ? ' + ' : '') + this.value + '%';
                }
            },
            plotLines: [{
                value: 0,
                width: 2,
                color: 'silver'
            }]
        },

        plotOptions: {
            series: {
                showInNavigator: true
            }
        },
        legend: {
            enabled: true,
            verticalAlign: 'top',
        },
        tooltip: {
            pointFormat: '<span style="color:{series.color}">{series.name}</span>: <b>{point.y}</b> ({point.change}%)<br/>',
            valueDecimals: 2,
            split: true
        },
        series: data
    });

}



// Stack CHART
function draw_performance_chart(data, element) {
    var myChart = Highcharts.stockChart(element, {
        credits: {
            enabled: false
        },
        navigator: {
            enabled: false
        },
        rangeSelector: {
            selected: 5,
        },
        chart: {
            zoomType: 'x',
        },
        title: {
            text: 'Portfolio NAV'
        },
        subtitle: {
            text: ''
        },
        xAxis: {
            type: 'datetime'
        },
        yAxis: {
            title: {
                text: 'NAV'
            },
            startOnTick: false,
            endOnTick: false
        },
        legend: {
            enabled: false
        },
        series: [{
            type: 'spline',
            dataGrouping: {
                enabled: false
            },
            name: 'NAV',
            data: data,
            turboThreshold: 0,
            tooltip: {
                pointFormat: "{point.y:,.0f}"
            }
        }]
    });

};


function build_trellis(portfolio = true) {
    var charts = []
    if (portfolio == true) {
        containers = document.querySelectorAll('#trellis_portfolio td'),
            datasets = data.CHARTS.stats_chart.portfolio.datasets;
    } else {
        containers = document.querySelectorAll('#trellis_assets td'),
            datasets = data.CHARTS.stats_chart.assets.datasets;
    }

    datasets.forEach(function (dataset, i) {
        charts.push(Highcharts.chart(containers[i], {
            chart: {
                type: 'bar',
                marginLeft: 100
            },

            title: {
                text: dataset.name,
                align: 'left',
                x: 90
            },

            credits: {
                enabled: false
            },
            plotOptions: {
                bar: {
                    dataLabels: {
                        enabled: true,
                        overflow: 'justify',
                        // format below will have a % if value is not a ratio
                        format: dataset.name.toLowerCase().includes('ratio') ? '{point.y:.2f}' : '{point.y:,.2f}%',
                        style: {
                            fontSize: '9px',
                            fontFamily: 'arial'
                        }
                    }
                }
            },
            tooltip: {
                enabled: false
            },
            xAxis: {
                categories: portfolio ? data.CHARTS.stats_chart.portfolio.categories : data.CHARTS.stats_chart.assets.categories,
                labels: {
                    enabled: true,
                    rotation: 0,
                    style: {
                        fontSize: '11px',
                        fontFamily: 'arial'
                    }
                }
            },
            yAxis: {
                allowDecimals: false,
                title: {
                    text: null
                },

            },

            legend: {
                enabled: false
            },

            series: [dataset],
            dataLabels: {
                inside: false,
                enabled: true,
            }

        }));
    });
}



