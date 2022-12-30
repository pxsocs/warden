
// Load the fonts
Highcharts.createElement('link', {
	href: 'https://fonts.googleapis.com/css?family=Allerta:400,600',
	rel: 'stylesheet',
	type: 'text/css'
}, null, document.getElementsByTagName('head')[0]);

Highcharts.theme = {
	colors: ["#da5526", "#27647b", "#aecbc9", "#5757f", "#aaeeee", "#ff0066", "#eeaaee",
		"#697f98", "#60686F", "#F68930", "#333c3e"],
	chart: {

		backgroundColor: null,
		style: {
			fontFamily: "Dosis, sans-serif"
		}
	},
	title: {
		style: {
			fontSize: '16px',
			fontWeight: 'bold',
			textTransform: 'uppercase'
		}
	},
	tooltip: {
		borderWidth: 0,
		backgroundColor: 'rgba(219,219,216,0.8)',
		shadow: false
	},
	legend: {
		itemStyle: {
			fontWeight: 'bold',
			fontSize: '13px'
		}
	},
	xAxis: {
		gridLineWidth: 1,
		labels: {
			style: {
				fontSize: '12px'
			}
		}
	},
	yAxis: {
		minorTickInterval: 'auto',
		title: {
			style: {
				textTransform: 'uppercase'
			}
		},
		labels: {
			style: {
				fontSize: '12px'
			}
		}
	},
	plotOptions: {
		candlestick: {
			lineColor: '#404048'
		},
		legend: {
			layout: 'horizontal',
			floating: true,
			align: 'center',
			verticalAlign: 'top'
		}

	},


	// General
	background2: '#FAFAFA'

};


// Apply the theme
Highcharts.setOptions(Highcharts.theme);
