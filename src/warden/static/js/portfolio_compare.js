$(document).ready(function () {

    // Data to pre-fill start and end dates
    var now = new Date();
    var oneYrAgo = new Date();
    oneYrAgo.setYear(now.getFullYear() - 1);

    document.getElementById('start_date').valueAsDate = oneYrAgo;
    document.getElementById('end_date').valueAsDate = new Date();

    $('.change_monitor').on('change', change_refresh);
    run_ajax();
});

function change_refresh() {
    $('#alerts').html("<div class='small alert alert-info alert-dismissible fade show' role='alert'>Please wait... Refreshing data." +
        "</div>")
    setTimeout(function () { run_ajax(); }, 1000)
};

function run_ajax() {
    // Ajax to get the json:
    // portfolio_compare_json?tickers=BTC,ETH,AAPL&start=%272019-05-10%27&end=%272019-05-20%27
    tickers = $('#tickers').val()
    start_date = $('#start_date').val()
    end_date = $('#end_date').val()

    $.ajax({
        type: "GET",
        dataType: 'json',
        url: "/portfolio_compare_json?method=chart&tickers=" + tickers + "&start=" + start_date + "&end=" + end_date,
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
};

function handle_ajax_data(data) {
    // Var to return message alerts for ticker errors
    var failed_message = "";
    // Prepare data for chart
    // The ajax return functions sends a string that needs to be read as a json
    var parsed_data = (jQuery.parseJSON(data.data));
    var chart_data_list = [];
    var nav_dict = {};
    // These are all HighChart inputs - first for NAV, then loop through tickers
    nav_dict['name'] = 'Portfolio (base 100)';
    nav_dict['yAxis'] = 0;
    nav_dict['type'] = 'line';
    nav_dict['color'] = '#8CADE1'; // Portfolio line is orange and thicker
    nav_dict['lineWidth'] = 5;
    nav_dict['turboThreshold'] = 0;
    nav_dict['data'] = Object.keys(parsed_data['NAV_norm']).map((key) => [((key * 1)), parsed_data['NAV_norm'][key]]);
    chart_data_list.push(nav_dict);

    // Looping through Tickers (only ones that downloaded ok)
    $.each(data.messages, function (key_x, value) {
        if (value == "ok") {
            // Prep data for chart
            tmp_dict = {};
            tmp_dict['name'] = key_x;
            tmp_dict['type'] = 'line';
            tmp_dict['turboThreshold'] = 0;
            // The line below maps in a format that HighCharts can understand. the *1 is necessary for some weird reason.
            tmp_dict['data'] = Object.keys(parsed_data[key_x + '_norm']).map((key) => [((key * 1)), parsed_data[key_x + '_norm'][key]]);
            tmp_dict['yAxis'] = 0;
            chart_data_list.push(tmp_dict);
        } else {
            failed_message = failed_message + " " + (key_x) + " (" + value + ") ";
        }
    });


    // Return alert with error message for tickers not found
    if (failed_message != "") {
        failed_message = "Some tickers returned errors: " + failed_message;
        $('#alerts').html("<div class='small alert alert-warning alert-dismissible fade show' role='alert'>" + failed_message +
            "</div>")
        // Hide alert after 4500ms
        $("#alerts").fadeTo(4500, 500).slideUp(500, function () {
            $("#alerts").slideUp(500);
        });
    };
    // Get data from metadata
    meta_data_all = ((data.meta_data));
    $('#table_start').html(data.table.meta.start_date);
    $('#table_end').html(data.table.meta.end_date);
    $('#table_days').html(data.table.meta.number_of_days + " (" + data.table.meta.count_of_points + ")");

    // Now, generate the table with meta data for each ticker

    // First the Portfolio Data
    var html_table = "  <tr class='table-success'> \
                        <td class='text-left'> NAV</td>\
                        <td class='text-center redgreen'>" + (data.table.NAV.return * 100).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "%</td>\
                        <td class='text-center'> - </td>\
                        <td class='text-center'>" + (data.table.NAV.ann_std_dev * 100).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "%</td>\
                        <td class='text-center redgreen'>" + (data.table.NAV.return / data.table.NAV.ann_std_dev).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "</td>\
                        <td class='text-center redgreen'>" + (data.table.NAV.avg_return * 100).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "%</td>\
                        <td class='text-right'>" + (data.table.NAV.start).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "</td>\
                        <td class='text-right'>" + (data.table.NAV.end).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "</td>\
                    </tr>";


    $.each(data.messages, function (key_x, value) {
        console.log(key_x);
        if (value == "ok") {
            html_table = html_table +
                "  <tr> \
                        <td class='text-left'>"+ key_x + "</td>\
                        <td class='text-center redgreen'>" + (data.table[key_x]['return'] * 100).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "%</td>\
                        <td class='text-center redgreen'>" + (data.table[key_x]['comp2nav'] * 100).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + " %</td>\
                        <td class='text-center'>" + (data.table[key_x]['ann_std_dev'] * 100).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "%</td>\
                        <td class='text-center redgreen'>" + (data.table[key_x]['return'] / data.table[key_x]['ann_std_dev']).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "</td>\
                        <td class='text-center redgreen'>" + (data.table[key_x]['avg_return'] * 100).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "%</td>\
                        <td class='text-right'>" + (data.table[key_x]['start']).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "</td>\
                        <td class='text-right'>" + (data.table[key_x]['end']).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "</td>\
                    </tr>";
        };
    });

    $('#table_body').html(html_table);
    // Format Red and Green Numbers (negative / positive)
    $("td.redgreen").removeClass('red_negpos');
    $("td.redgreen").addClass('green_negpos');
    $("td.redgreen:contains('-')").removeClass('green_negpos');
    $("td.redgreen:contains('-')").addClass('red_negpos');

    // Create Correlation Table
    $('#corr_table').html(data.corr_html);

    // Format colors depending on value
    // Define the ending colour, which is white
    xr = 255; // Red value
    xg = 255; // Green value
    xb = 255; // Blue value

    // Define the starting colour for positives
    yr = 157; // Red value 243
    yg = 188; // Green value 32
    yb = 156; // Blue value 117

    n = 100; // Declare the number of groups

    $('#corr_table').each(function () {
        $(this).find('th').each(function () {
            $(this).css('background-color', '#c5c7c9');
        })
        $(this).find('td').each(function () {
            var val = parseFloat($(this).text(), 10);
            var pos = parseInt((Math.round((val / 1) * 100)).toFixed(0));
            red = parseInt((xr + ((pos * (yr - xr)) / (n - 1))).toFixed(0));
            green = parseInt((xg + ((pos * (yg - xg)) / (n - 1))).toFixed(0));
            blue = parseInt((xb + ((pos * (yb - xb)) / (n - 1))).toFixed(0));
            clr = 'rgb(' + red + ',' + green + ',' + blue + ')';
            $(this).css({ backgroundColor: clr });

        })
    })



    createChart(chart_data_list);

};

//  CHART
function createChart(data) {
    console.log(data)
    var myChart = Highcharts.stockChart('compchart', {
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
            text: 'Portfolio NAV compared to other assets'
        },
        subtitle: {
            text: document.ontouchstart === undefined ?
                'Click and drag in the plot area to zoom in' : 'Pinch the chart to zoom in'
        },
        xAxis: {
            type: 'datetime'
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

        series: data
    });

};