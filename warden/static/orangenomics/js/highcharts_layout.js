
// Load the fonts
Highcharts.createElement('link', {
    href: 'https://fonts.googleapis.com/css?family=Roboto:400,700',
    rel: 'stylesheet',
    type: 'text/css'
}, null, document.getElementsByTagName('head')[0]);

Highcharts.theme = {
    colors: ['#DDDF00', '#058DC7', '#50B432', '#ED561B', '#24CBE5', '#64E572',
        '#FF9655', '#FFF263', '#6AF9C4'],
    chart: {
        backgroundColor: null,
        style: {
            fontFamily: "Arial",
            color: "#333333",
            fontSize: "12px",
            fontWeight: "normal",
            fontStyle: "normal",
        },
        plotBackgroundColor: null,
        alignTicks: true,
        inverted: false,
        panning: false,
        plotShadow: false,
        spacingBottom: 10,
        spacingLeft: 10,
        spacingRight: 10,
        spacingTop: 10
    },
    title: {
        style: {
        }
    },
    tooltip: {
        borderWidth: 0,
        backgroundColor: null,
    },
    legend: {
        itemStyle: {
            fontSize: '10px'
        }
    },
    xAxis: {
        gridLineWidth: 1,
        labels: {
            style: {
            }
        }
    },
    yAxis: {
        minorTickInterval: 'auto',
        title: {
            style: {
            }
        },
        labels: {
            style: {
            }
        }
    },
    colorAxis: {
        uniqueNames: true
    },
    pane: {
        background: []
    },
    responsive: {
        "rules": []
    },
    scrollbar: {
        enabled: false
    }
};


// Apply the theme
Highcharts.setOptions(Highcharts.theme);
