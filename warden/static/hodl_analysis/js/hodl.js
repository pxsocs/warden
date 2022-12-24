$(document).ready(function () {
    console.log("-------------------------------");
    console.log("00000080   01 04 45 54 68 65 20 54  69 6D 65 73 20 30 33 2F   ..EThe Times 03/");
    console.log("00000090   4A 61 6E 2F 32 30 30 39  20 43 68 61 6E 63 65 6C   Jan/2009 Chancel");
    console.log("000000A0   6C 6F 72 20 6F 6E 20 62  72 69 6E 6B 20 6F 66 20   lor on brink of ");
    console.log("000000B0   73 65 63 6F 6E 64 20 62  61 69 6C 6F 75 74 20 66   second bailout f");
    console.log("000000C0   6F 72 20 62 61 6E 6B 73  FF FF FF FF 01 00 F2 05   or banksÿÿÿÿ..ò.");
    console.log("-------------------------------");
    console.log("FREEDOM FROM GOVERNMENT SLAVERY");
    console.log("-------------------------------");
    $body = $("body");

    $(document).on({
        ajaxStart: function () { $body.addClass("loading"); },
        ajaxStop: function () { $body.removeClass("loading"); }
    });

    retrieve_data();
    $('.monitor_chg').on('change', doAdelay);
});

function doAdelay() {
    // This is not working properly. Should wait a few seconds to wait for user input before running the ajax
    setTimeout(function () { return true; }, 30000);
    retrieve_data()
};

function retrieve_data() {
    var ticker = $('#ticker').val()
    var start_date = $('#start_date').val()
    var end_date = $('#end_date').val()
    var frequency = $('#frequency').val()
    var period_exclude = $('#period_exclude').val()
    var fx = $('#fx').val()

    $.ajax({
        type: "GET",
        dataType: 'json',
        url: "/hodl_analysis/stats_json?ticker=" + ticker + "&force=False&fx=" + fx + "&start_date=" + start_date + "&end_date=" + end_date + "&frequency=" + frequency + "&period_exclude=" + period_exclude,
        error: function () {
            clean_data();
            $('#error_msg').html("Something went wrong. Try again.");
        },
        success: function (data) {
            createcharts(data.histogram, data.histogram_dates)
            createbarchart(data.bar_chart_returns.data, data.bar_chart_returns.categories)
            if (data.status == "error") {
                clean_data();
                $('#error_message').html("Something went wrong when requesting data. Is that a valid ticker?");
            } else {
                $('#error_message').html(" ");
                text_data = "Requested prices for " + data.ticker + " from " + data.start_date + " to " + data.end_date;
                $('#text_summary').html(text_data);
                text_data_0 = "Range of available data: from " + data.set_initial_time + " to " + data.set_final_time
                $('#text_summary_0').html(text_data_0);
                text_data_2 = "Aggregating the returns in " + data.frequency + " day blocks and excluding the " + data.period_exclude + " top blocks of " + data.frequency + " day intervals."
                $('#text_summary_2').html(text_data_2);
                $('#ticker_start_value').html((data.ticker_start_value).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 4, minimumFractionDigits: 4 }) + " " + data.fx);
                $('#ticker_end_value').html((data.ticker_end_value).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 4, minimumFractionDigits: 4 }) + " " + data.fx);
                $('#period_tr').html((data.period_tr * 100).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + " %");
                missed_txt = "on the top " + data.period_exclude + " periods of " + data.frequency + " days";
                $('#missed').html(missed_txt);
                $('#nlargest_tr').html((data.nlargest_tr * 100).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + " %");
                $('#exclude_nlargest_tr').html((data.exclude_nlargest_tr * 100).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + " %");
                difference = (data.exclude_nlargest_tr - data.period_tr)
                $('#difference').html((difference * 100).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + " %");
                $('#n_largest').html(data.nlargest);
                var start_date = new Date(data.start_date);
                var end_date = new Date(data.end_date);
                var n_days = new Date(end_date - start_date);
                n_days = n_days / 1000 / 60 / 60 / 24;
                var missed_days = (data.frequency * data.period_exclude);
                var pct_missed = (missed_days / n_days) * 100;
                var return_missed = (data.nlargest_tr / data.period_tr) * 100

                n_days = n_days.toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 0, minimumFractionDigits: 0 });
                missed_days = missed_days.toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 0, minimumFractionDigits: 0 });
                pct_missed = pct_missed.toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 });
                return_missed = return_missed.toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 });

                returns_msg = "Out of a total of " + n_days + " days, you would have missed " + missed_days + " days or " + pct_missed + "% of the time."
                $('#returns_msg').html(returns_msg);

                missed_msg = "By not being allocated " + pct_missed + "% of the time, you would have missed " + return_missed + "% of the returns during this period"
                $('#missed_msg').html(missed_msg);

                $('#mean_daily_return_period').html((data.mean_daily_return_period * 100).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + " %");
                $('#mean_nperiod_return').html((data.mean_nperiod_return * 100).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + " %");
                $('#nlargest_mean').html((data.nlargest_mean * 100).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + " %");
            }
        }
    });

};

function clean_data() {

    $('#text_summary').html(" ");
    $('#text_summary_0').html(" ");
    $('#text_summary_2').html(" ");
    $('#ticker_start_value').html("-");
    $('#ticker_end_value').html("-");
    $('#period_tr').html("-");
    $('#missed').html("-");
    $('#nlargest_tr').html("-");
    $('#exclude_nlargest_tr').html("-");
    $('#difference').html("-");
    $('#n_largest').html("-");
    $('#returns_msg').html(" ");
    $('#missed_msg').html(" ");
    $('#bar_chart_returns').html(" ");
    $('#histogramchart').html(" ");
    $('#mean_daily_return_period').html(" ");
    $('#mean_nperiod_return').html(" ");
    $('#nlargest_mean').html(" ");
};


function createcharts(datachart, datechart) {

    data = datachart;

    var myChart = Highcharts.chart('histogramchart', {
        title: {
            text: 'Histogram of daily returns'
        },
        xAxis: [{
            title: { text: 'Days' },
            alignTicks: false
        }, {
            title: { text: 'Histogram' },
            labels: {
                format: '{value:.2f}%'
            },
            alignTicks: false,
            opposite: true
        }],

        yAxis: [{
            title: { text: 'Daily Returns' },
            format: '{value:.2f}%',
            labels: {
                format: '{value:.2f}%'
            }
        },
        {
            title: { text: 'Histogram Occurences' },
            opposite: true
        }],

        series: [{
            name: 'Histogram',
            type: 'histogram',
            xAxis: 1,
            yAxis: 1,
            baseSeries: 's1',
            borderWidth: 6,
            zIndex: -1
        }, {
            name: 'Data',
            type: 'scatter',
            data: data,
            id: 's1',
            marker: {
                radius: 1.5
            }
        }]
    });

};



function createbarchart(datachart, chartcat) {

    data = datachart;

    var myChart = Highcharts.chart('bar_chart_returns', {
        credits: {
            text: "",
            href: "/home"
        },
        chart: {
            zoomType: 'x',
            backgroundColor: "#FAFAFA",
        },
        title: {
            text: 'Missed Investment Periods'
        },

        xAxis: {
            type: 'category',
            categories: chartcat,
            labels: {
                rotation: 0
            }
        },
        yAxis: {
            title: {
                text: 'Return',
            },
            labels: {
                format: '{value:.2f}%',
                overflow: 'justify'
            }
        },

        legend: {
            enabled: false
        },
        plotOptions: {
            bar: {
                dataLabels: {
                    format: '{point.y:.2f}%',
                    enabled: true
                }
            },
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
                lineWidth: 0.5,
                states: {
                    hover: {
                        lineWidth: 1
                    }
                },
                threshold: null
            }
        },

        series: [{
            type: 'bar',
            name: 'Returns',
            data: datachart,
            turboThreshold: 0
        }]
    });
};
