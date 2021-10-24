$(document).ready(function () {

    // Data to pre-fill start and end dates
    var now = new Date();
    var fiveYrAgo = new Date();
    fiveYrAgo.setYear(now.getFullYear() - 5);
    document.getElementById('start_date').valueAsDate = fiveYrAgo;
    document.getElementById('end_date').valueAsDate = new Date();
    $('.change_monitor').on('change', change_refresh);
    $('#alerts').html("<div class='small alert alert-info alert-dismissible fade show' role='alert'>Please wait... Loading data." +
        "</div>")
    run_ajax();
});

function change_refresh() {

    // Send a notice - Refreshing data
    $('#alerts').html("<div class='small alert alert-info alert-dismissible fade show' role='alert'>Please wait... Refreshing data." +
        "</div>")
    setTimeout(function () { run_ajax(); }, 1000)
};

function run_ajax() {
    // Ajax to get the json:

    start_date = $('#start_date').val()
    end_date = $('#end_date').val()
    ticker = $("#ticker").val()
    n_dd = $("#n_dd").val()

    $.ajax({
        type: "GET",
        dataType: 'json',
        url: "/drawdown_json?ticker=" + ticker + "&start=" + start_date + "&end=" + end_date + "&n_dd=" + n_dd,
        success: function (data) {
            $('#alerts').html("")
            console.log("ajax request: OK")
            handle_ajax_data(data);
        },
        error: function (xhr, status, error) {
            $('#alerts').html("<div class='small alert alert-danger alert-dismissible fade show' role='alert'>An error occured while refreshing data." +
                "<button type='button' class='close' data-dismiss='alert' aria-label='Close'><span aria-hidden='true'>&times;</span></button></div>")
            console.log(status);
        }
    });
    // Second Ajax for chart data
    $.ajax({
        type: "GET",
        dataType: 'json',
        url: "/drawdown_json?ticker=" + ticker + "&start=" + start_date + "&end=" + end_date + "&n_dd=" + n_dd + "&chart=True",
        success: function (chart_data) {
            $('#alerts').html("")
            console.log("ajax request: OK")
            createChart(chart_data);
        },
        error: function (xhr, status, error) {
            $('#alerts').html("<div class='small alert alert-danger alert-dismissible fade show' role='alert'>An error occured while refreshing data." +
                "<button type='button' class='close' data-dismiss='alert' aria-label='Close'><span aria-hidden='true'>&times;</span></button></div>")
            console.log(status);
        }
    });


};

function handle_ajax_data(data) {
    console.log(data)
    var table_body = ""
    $.each(data, function (key_x, value) {
        table_body = table_body +
            "<tr> <th class='table-active'> " + (value.dd * 100).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "% </th>" +
            "<td style='color: green; '> " + value.start_date + "</td>" +
            "<td style='color: red; '>  " + value.end_date + "</td>" +
            "<td style='color: green; '> " + value.start_value.toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "</td>" +
            "<td style='color: red; '>  " + value.end_value.toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "</td>" +
            "<td> " + value.days_to_recovery + "</td>" +
            "<td> " + value.days_to_bottom + "</td>" +
            "<td> " + value.days_bottom_to_recovery + "</td>" +
            "</tr>"
    });
    // Create Table
    $('#table_body').html(table_body);
};



//  CHART
function createChart(data) {

    console.log(data.days)
    $('#dd_days').html(data.days.drawdown);
    $('#recovery_days').html(data.days.recovery);
    $('#cycle_days').html(data.days.trending);
    $('#total_days').html(data.days.total);

    console.log(data.plot_bands)
    // var chart_parsed = JSON.parse(data.chart_data);


    var myChart = Highcharts.stockChart('ddchart', {
        credits: {
            enabled: false
        },
        navigator: {
            enabled: false,
        },
        rangeSelector: {
            enabled: false
        },
        chart: {
            zoomType: 'x',
            backgroundColor: "#FAFAFA",
        },
        title: {
            text: 'Largest Non-Overlapping Drawdowns'
        },
        subtitle: {
            text: document.ontouchstart === undefined ?
                'Click and drag in the plot area to zoom in' : 'Pinch the chart to zoom in'
        },
        xAxis: {
            type: 'datetime',
            plotBands: data.plot_bands
        },
        yAxis: {
            startOnTick: false,
            endOnTick: false
        },
        legend: {
            enabled: true,
            align: 'right'
        },
        plotOptions: {
            area: {
                fillColor: {
                    linearGradient: {
                        x1: 0,
                        y1: 0,
                        x2: 0,
                        y2: 1
                    },
                    stops: [
                        [0, Highcharts.getOptions().colors[0]],
                        [1, Highcharts.Color(Highcharts.getOptions().colors[0]).setOpacity(0).get('rgba')]
                    ]
                },
                marker: {
                    radius: 2
                },
                lineWidth: 1,
                states: {
                    hover: {
                        lineWidth: 1
                    }
                },
                threshold: null
            }
        },


        series: [{
            name: 'Historical Prices',
            id: 'dataseries',
            data: Object.keys(data.chart_data).map((key) => [(key * 1), (data.chart_data[key])])
        }, {
            type: 'flags',
            name: 'Events',
            data: data.chart_flags,
            onSeries: 'dataseries',
            shape: 'squarepin',
            showInLegend: false
        }
        ]
    });

};