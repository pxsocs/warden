$(document).ready(function () {
    // Format Red and Green Numbers (negative / positive)
    $("td.redgreen").removeClass('red_negpos');
    $("td.redgreen").addClass('green_negpos');
    $("td.redgreen:contains('-')").removeClass('green_negpos');
    $("td.redgreen:contains('-')").addClass('red_negpos');
    // Request data for Ticker comparison with Ajax request
    run_ajax();

    // Monitor changes
    $('.change_monitor').on('change', run_ajax);

    // Let's create a heatmap on all heatmap values
    // Function to get the max value in an Array
    Array.max = function (array) {
        return Math.max.apply(Math, array);
    };

    // Function to get the min value in an Array
    Array.min = function (array) {
        return Math.min.apply(Math, array);
    };

    heat_color('.heatmap');

});


function run_ajax() {
    ticker = $('#b_ticker').val()
    console.log(ticker)
    $('#alerts').html("<div class='small alert alert-info alert-dismissible fade show' role='alert'>Please wait... Refreshing data." +
        "</div>")
    var loader_html = " <div class='spinner-border text-secondary' role='status'> \
                        <span class='sr-only'>Loading...</span> \
                        </div>"

    $('#bench_diff_table').html(loader_html);
    $('#bench_table').html(loader_html);
    console.log("Change Detected - running Ajax")

    $.ajax({
        type: "GET",
        dataType: 'json',
        url: "/heatmapbenchmark_json?ticker=" + ticker,
        success: function (data) {
            $('#alerts').html("")
            console.log("ajax request: OK");
            handle_ajax_data(data);
        },
        error: function (xhr, status, error) {
            $('#alerts').html("<div class='small alert alert-danger alert-dismissible fade show' role='alert'>An error occured while refreshing data. Check the ticker and try again." +
                "<button type='button' class='close' data-dismiss='alert' aria-label='Close'><span aria-hidden='true'>&times;</span></button></div>")
            console.log(status);
        }
    });
}

function handle_ajax_data(data) {
    console.log(data)
    // Now that data was returned, let's create the tables
    var benchmark_table = "     <table class='table small table-condensed'> \
                                    <thead class='thead-light'> \
                                    <tr class='table-active'> \
                               <th></th>"

    // Create table for benchmark
    $.each(data.cols, function (key_x, value) {
        if (value == "eoy") {
            value = "Year"
        }
        benchmark_table = benchmark_table +
            "<th class='text-center'>" + value + "</th>"
    });

    benchmark_table = benchmark_table + "</tr></thead><tbody>"

    $.each(data.years.reverse(), function (key_x, value) {
        benchmark_table = benchmark_table +
            "<tr> <th class='table-active'> " + value + " </th>"
        $.each(data.cols, function (key_a, value_col) {
            if (value_col == "eoy") {
                benchmark_table = benchmark_table +
                    "<td class='text-right table-secondary redgreen'>" +
                    (data.heatmap[value_col][value] * 100).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 1, minimumFractionDigits: 1 }) + "%"
            } else {
                if (data.heatmap[value_col][value] != 0) {
                    benchmark_table = benchmark_table +
                        "<td class='text-right heatmap'>" +
                        (data.heatmap[value_col][value] * 100).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 1, minimumFractionDigits: 1 }) + "%"
                } else {
                    benchmark_table = benchmark_table +
                        "<td class='text-center emptycell'>"
                }
            }
            benchmark_table = benchmark_table + "</td>"
        });
        benchmark_table = benchmark_table + "</tr>"
    });
    benchmark_table = benchmark_table + "</tbody></table>"

    $('#bench_table').html(benchmark_table);


    // Create Table for difference between the 2 assets
    benchmark_table = "     <table class='table small table-condensed'> \
                                    <thead class='thead-light'> \
                                    <tr class='table-active'> \
                               <th></th>"

    $.each(data.cols, function (key_x, value) {
        if (value == "eoy") {
            value = "Year"
        }
        benchmark_table = benchmark_table +
            "<th class='text-center'>" + value + "</th>"
    });

    benchmark_table = benchmark_table + "</tr></thead><tbody>"

    $.each(data.years, function (key_x, value) {
        benchmark_table = benchmark_table +
            "<tr> <th class='table-active'> " + value + " </th>"
        $.each(data.cols, function (key_a, value_col) {
            if (value_col == "eoy") {
                benchmark_table = benchmark_table +
                    "<td class='text-right table-secondary redgreen'>" +
                    (data.heatmap_diff[value_col][value] * 100).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 1, minimumFractionDigits: 1 }) + "%"
            } else {
                if (data.heatmap[value_col][value] != 0) {
                    benchmark_table = benchmark_table +
                        "<td class='text-right heatmap'>" +
                        (data.heatmap_diff[value_col][value] * 100).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 1, minimumFractionDigits: 1 }) + "%"
                } else {
                    benchmark_table = benchmark_table +
                        "<td class='text-center emptycell'>"
                }
            }
            benchmark_table = benchmark_table + "</td>"
        });
        benchmark_table = benchmark_table + "</tr>"
    });
    benchmark_table = benchmark_table + "</tbody></table>"
    $('#bench_diff_table').html(benchmark_table);

    // Format Red and Green Numbers (negative / positive)
    $("td.redgreen").removeClass('red_negpos');
    $("td.redgreen").addClass('green_negpos');
    $("td.redgreen:contains('-')").removeClass('green_negpos');
    $("td.redgreen:contains('-')").addClass('red_negpos');
    heat_color('.heatmap')

}


function heat_color(object) {
    // Get all data values from our table cells making sure to ignore the first column of text
    // Use the parseInt function to convert the text string to a number

    var counts_positive = $(object).map(function () {
        if (parseInt($(this).text()) > 0) {
            return parseInt($(this).text());
        };
    }).get();

    var counts_negative = $(object).map(function () {
        if (parseInt($(this).text()) < 0) {
            return parseInt($(this).text());
        };
    }).get();

    // run max value function and store in variable
    var max = Array.max(counts_positive);
    var min = Array.min(counts_negative) * (-1);

    n = 100; // Declare the number of groups

    // Define the ending colour, which is white
    xr = 255; // Red value
    xg = 255; // Green value
    xb = 255; // Blue value

    // Define the starting colour for positives
    yr = 0; // Red value 243
    yg = 135; // Green value 32
    yb = 50; // Blue value 117

    // Define the starting colour for negatives
    nr = 115; // Red value 243
    ng = 0; // Green value 32
    nb = 0; // Blue value 117

    // Loop through each data point and calculate its % value
    $(object).each(function () {
        if (parseInt($(this).text()) > 0) {
            var val = parseInt($(this).text());
            var pos = parseInt((Math.round((val / max) * 100)).toFixed(0));
            red = parseInt((xr + ((pos * (yr - xr)) / (n - 1))).toFixed(0));
            green = parseInt((xg + ((pos * (yg - xg)) / (n - 1))).toFixed(0));
            blue = parseInt((xb + ((pos * (yb - xb)) / (n - 1))).toFixed(0));
            clr = 'rgb(' + red + ',' + green + ',' + blue + ')';
            $(this).css({ backgroundColor: clr });
        }
        else {
            var val = parseInt($(this).text()) * (-1);
            var pos = parseInt((Math.round((val / max) * 100)).toFixed(0));
            red = parseInt((xr + ((pos * (nr - xr)) / (n - 1))).toFixed(0));
            green = parseInt((xg + ((pos * (ng - xg)) / (n - 1))).toFixed(0));
            blue = parseInt((xb + ((pos * (nb - xb)) / (n - 1))).toFixed(0));
            clr = 'rgb(' + red + ',' + green + ',' + blue + ')';
            $(this).css({ backgroundColor: clr });
        }
    });
}