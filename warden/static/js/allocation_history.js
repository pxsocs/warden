$(document).ready(function () {
    // AJAX to get the list of tickers that ever traded in portfolio
    $.ajax({
        type: "GET",
        dataType: 'json',
        url: "/portfolio_tickers_json",
        success: function (tickers) {
            $('#alerts').html("")
            console.log("ajax request [tickers]: OK")
            run_ajax(tickers);

        },
        error: function (xhr, status, error) {
            $('#alerts').html("<div class='small alert alert-danger alert-dismissible fade show' role='alert'>An error occured while refreshing data." +
                "<button type='button' class='close' data-dismiss='alert' aria-label='Close'><span aria-hidden='true'>&times;</span></button></div>")
            console.log(status);
        }
    });
});
function run_ajax(tickers) {
    // Ajax to get the NAV json
    $.ajax({
        type: "GET",
        dataType: 'json',
        url: "/generatenav_json",
        success: function (data) {
            $('#alerts').html("")
            console.log("ajax request [NAV]: OK")
            handle_ajax_data(data, tickers);

        },
        error: function (xhr, status, error) {
            $('#alerts').html("<div class='small alert alert-danger alert-dismissible fade show' role='alert'>An error occured while refreshing data." +
                "<button type='button' class='close' data-dismiss='alert' aria-label='Close'><span aria-hidden='true'>&times;</span></button></div>")
            console.log(status);
        }
    });

    // GET PnL Data for attribution
    $.ajax({
        type: "GET",
        dataType: 'json',
        url: "/positions_json",
        success: function (pnl_data) {
            $('#alerts').html("")
            console.log("ajax request [PnL Data]: OK")
            console.log(pnl_data)
            run_alloc(pnl_data, tickers, pnl_data.user.symbol);
        },
        error: function (xhr, status, error) {
            $('#alerts').html("<div class='small alert alert-danger alert-dismissible fade show' role='alert'>An error occured while refreshing data." +
                "<button type='button' class='close' data-dismiss='alert' aria-label='Close'><span aria-hidden='true'>&times;</span></button></div>")
            console.log(status);
        }
    });
};

function handle_ajax_data(data, tickers) {
    // Prepare data for charts
    var chart_data_list = [];
    // // Looping through Tickers (only ones that downloaded ok)
    $.each(tickers, function (key_ticker) {
        ticker = tickers[key_ticker]
        if (data[ticker + '_pos']) {
            // if (ticker != "USD") {
            // Prep data for chart
            tmp_dict = {};
            tmp_dict['name'] = ticker;
            tmp_dict['type'] = 'area';
            tmp_dict['turboThreshold'] = 0;
            // The line below maps in a format that HighCharts can understand. the *1 (for date) is necessary for some weird reason.
            // it maps to (date, value)
            tmp_dict['data'] = Object.keys(data[ticker + '_fx_perc']).map((key) => [((key * 1)), data[ticker + '_fx_perc'][key] * 100]);
            tmp_dict['yAxis'] = 0;
            chart_data_list.push(tmp_dict);
        }
    });
    createChart(chart_data_list);
};


//  CHART
function createChart(data, tickers) {


    var myChart = Highcharts.stockChart('aloc_chart', {
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
            backgroundColor: "#FAFAFA",
        },
        title: {
            text: 'Historical Portfolio Allocation (%)'
        },
        subtitle: {
            text: document.ontouchstart === undefined ?
                'Click and drag in the plot area to zoom in' : 'Pinch the chart to zoom in'
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

};


// CREATE SECOND CHART - PNL ATTRIBUTION
function run_alloc(data, tickers, fx) {
    // Prepare data for charts
    var chart_data_list = [];
    // // Looping through Tickers (only ones that downloaded ok)
    $.each(tickers, function (key_ticker) {
        ticker = tickers[key_ticker]
        if (ticker != "USD") {
            // // Prep data for chart
            tmp_tuple = [ticker, data['positions'][ticker]['pnl_gross']]
            chart_data_list.push(tmp_tuple);
        }
    });
    var index;
    while ((index = tickers.indexOf("USD")) > -1) {
        tickers.splice(index, 1);
    }
    var myPNLChart = Highcharts.chart('atrib_chart', {
        credits: {
            enabled: false
        },
        chart: {
            backgroundColor: "#FAFAFA",
            type: 'bar'
        },
        plotOptions: {
            series: {
                dataLabels: {
                    enabled: true,
                    x: -10,
                    format: '{point.name} : ' + fx + ' {point.y:,.0f}',
                },
                pointPadding: 0.1,
                groupPadding: 0
            }
        },
        xAxis: {
            categories: tickers
        },
        title: {
            text: 'PnL Attribution (' + fx + ')'
        },
        legend: {
            enabled: false,
            align: 'right'
        },
        series: [{
            data: chart_data_list
            // chart_list format: [['ETH', -30.28], ['BTC', 62.15]]
        }]
    });
};
