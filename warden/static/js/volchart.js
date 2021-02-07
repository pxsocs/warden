$(document).ready(function () {
    var rolling = $('#rolling').val()
    if (rolling == "") {
        rolling = 22
    }
    $body = $("body");


    portfolio_vol_data();
    metadata();
});


function loading() {
    var html_load = "<span class='loadanim'>&nbsp;PLEASE HOLD. GENERATING CHARTS... This can take a while.</span>"
    $('#volchart').html(html_load);
};

$(function () {
    $('#rolling').change(function () {
        rolling = $('#rolling').val();
        portfolio_vol_data();
        metadata();
    });
});


function metadata() {
    $.ajax({
        type: "GET",
        dataType: 'json',
        url: "/histvol?meta=true&rolling=" + rolling,
        success: function (data) {
            $('#metalast').html((data.last).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "%");
            $('#metamean').html((data.mean).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "%");
            $('#metamax').html((data.max).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "%");
            $('#metamin').html((data.min).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }) + "%");
            lstmean = (data.lastvsmean).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 })
            crnt = "The last vol is " + lstmean + "% from the historical mean";
            $('#metarel').html(crnt);

        }
    });

};

function portfolio_vol_data() {
    $.ajax({
        type: "GET",
        dataType: 'json',
        url: "/histvol?rolling=" + rolling,
        success: function (data) {
            createcharts(data.vol);
        }
    });
};

function createcharts(datachart) {

    data = datachart;


    var myChart = Highcharts.chart('volchart', {
        credits: {
            text: "",
            href: "/home"
        },
        chart: {
            zoomType: 'x',
            backgroundColor: "#FAFAFA",
        },
        title: {
            text: 'Portfolio Historical Annualized Volatility over time'
        },
        subtitle: {
            text: document.ontouchstart === undefined ?
                'Click and drag in the plot area to zoom in' : 'Pinch the chart to zoom in'
        },
        xAxis: {
            type: 'category',
            labels: {
                rotation: 270
            }
        },
        yAxis: {
            title: {
                text: 'Annualized Rolling Vol',
            },
            labels: {
                align: 'left'
            },
            startOnTick: false,
            endOnTick: false
        },

        legend: {
            enabled: false
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
            type: 'line',
            name: 'Vol',
            data: Object.keys(data)
                .map((key) => [(key), data[key]]),
            turboThreshold: 0
        }]
    });
};
