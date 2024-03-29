$(document).ready(function () {
    $(document).on('click', '#save_modal_button', function () {
        update_modal_port();
        $('#saveModal').modal('show');
    });
    $(document).on('click', '#save_modal_close', function () {
        $('#saveModal').modal('hide');
    });
    $(document).on('click', '#button_save_portfolio', function () {
        port_name = $('#portfolio_name').val();
        public_private = $('#portfolio_visibility').val();
        if (port_name.length == 0) {
            html = "<span class='text-warning'><i class='fa-solid fa-triangle-exclamation'></i>&nbsp;&nbsp;Portfolio name can't be empty</span>"
            $('#port_message').html(html);
        } else {
            // Save the portfolio
            port_data = window.portstats.portfolio;
            rebalance = window.portstats.rebalance;
            data = {
                ["port_name"]: port_name,
                ["port_data"]: port_data,
                ["port_visibility"]: public_private,
                ["rebalance"]: rebalance
            }
            json_data = JSON.stringify(data)

            $.ajax({
                type: "POST",
                contentType: 'application/json',
                dataType: "json",
                data: json_data,
                url: base_url() + 'orangenomics/port_actions',
                success: function (data_back) {
                    if (data_back == 'success') {
                        send_message(`Porfolio ${port_name} saved`, 'success');
                    } else {
                        send_message(`Saving Portfolio returned an error: ${data_back}`, 'warning');
                    }
                },
                error: function (xhr, status, error) {
                    console.log(status);
                    console.log(error);
                    send_message(`An error occured while saving portfolio. message: ${status} | ${error} | ${xhr.responseText}`, 'danger')
                }
            });
            $('#saveModal').modal('hide');
        }
    });

    // Load Portfolio Modal
    $(document).on('click', '#load_modal_button', function () {
        filter = $('#portfolio_filter').val();
        update_load_list(filter);
        $('#loadModal').modal('show');
    });
    $(document).on('click', '#load_modal_close', function () {
        $('#loadModal').modal('hide');
    });
    $(document).on('click', '#button_load_portfolio', function () {
        // update loader for this portfolio
        $('#button_load_portfolio').html("Loading...")
        $('#button_load_portfolio').prop("disabled", true);
        $('#loadModal').modal('hide');
        $('#loading_modal').modal('show');
        $('#load_message').html("Loading Portfolio. Please Wait...")
        setTimeout(function () {
            load_portfolio();
            $('#loading_modal').modal('hide');
        }, 800);

    });
    // Rerun filter for portfolios
    $('#portfolio_filter').keyup(function () {
        filter = $('#portfolio_filter').val().toUpperCase();
        update_load_list(filter);
    });
    $(document).on('change', '#loader_select', function () {
        sel_port = $('#loader_select').val();
        data = ajax_getter(base_url() + 'orangenomics/port_actions?action=get_portfolio&port_id=' + sel_port);
        allocation = data.allocation;
        var port_table = ''
        port_table += `<div class="progress text-60-small" style="height: 60px;">`
        backgrounds = [
            'bg-info', 'bg-success', 'bg-warning', 'bg-danger'
        ]
        counter = 0;
        allocation.forEach(function (item, index) {
            ticker = item[0].toUpperCase();
            weight = parseFloat(item[1]) * 100
            port_table += `
                    <div    class="progress-bar ${backgrounds[counter]}"
                            role="progressbar"
                            style="width: ${weight}%;"
                            aria-valuemin="0"
                            aria-valuemax="100">
                            ${ticker}<br>${formatNumber(weight, 2)}%</div>
                `
            counter += 1;
            counter > backgrounds.length ? counter = 0 : counter = counter;
        });
        port_table += `</div>`;
        port_table += `<span class='text-small text-light'>Created on: <span class='float-end'>${formatDate(new Date(data.allocation_inputon))}</span><br>`;
        port_table += `Rebalance Frequency: <span class='float-end'>${data.rebalance.toUpperCase()}</span><br></span>`;

        $('#portfolio_details').html(port_table);


    });
});

function load_portfolio() {
    sel_port = $('#loader_select').val();
    var data = ajax_getter(base_url() +
        'orangenomics/port_actions?action=get_portfolio&port_id=' +
        sel_port + '&loader=true');
    window.portfolio = data.allocation;
    try {
        init_portfolio(data.allocation);
    } catch (error) {
        // In this case, the page is not the portfolio
        // page. Best to redirect to the analysis.
        p = encodeURIComponent(JSON.stringify(data.allocation))
        r = encodeURIComponent(JSON.stringify(data.rebalance))
        url = base_url() + 'orangenomics/analyze?portfolio=' + p + '&rebalance=' + r
        window.location.href = url
    }
    $('#rebalance').removeAttr('disabled');
    $('#rebalance').val(data.rebalance)
    $('#button_load_portfolio').prop("disabled", false);
    $('#button_load_portfolio').html("Load Portfolio")
}


function update_load_list(filter) {
    url = base_url() + 'orangenomics/port_actions?action=get_portfolios&filter=' + filter;
    data = ajax_getter(url);
    // Update the list
    private = data.private;
    public = data.public;
    var output = [];
    if (private != null && private.length > 0) {
        output.push('<option disabled>Your Portfolios</option>')
        $.each(private, function (key, value) {
            output.push('<option value="' + value.id + '">' + value.portfolio_name + '</option>');
        });
        output.push('<option disabled>   </option>')
    }

    if (public != null && public.length > 0) {
        output.push('<option disabled>Top 10 Public Portfolios</option>')
        var counter = 0;
        $.each(public, function (key, value) {
            output.push('<option value="' + value.id + '">' + value.portfolio_name + '</option>');
            counter += 1;
            if (counter == 9) {
                return false; // break
            }
        });
    }

    $('#loader_select').html(output.join(''));

};

function update_modal_port() {
    element = '#port_table';
    try {
        total = window.portstats.portfolio_total;
    } catch (error) {
        // This means it's not running on portfolio list page
        window.portfolio = getUrlParameter('portfolio');
        window.portfolio = JSON.parse(window.portfolio);
        rebalance = getUrlParameter('rebalance');
        rebalance = JSON.parse(rebalance);
        $("#button_save_portfolio").removeAttr('disabled');
        total = 1;
        window.portstats = {
            'portfolio_total': 1,
            'portfolio': window.portfolio,
            'rebalance': rebalance
        };
    }
    if (total != 1) {
        $("#button_save_portfolio").attr('disabled', 'disabled');
        $(element).html("<span class='text-warning'><i class='fa-solid fa-triangle-exclamation'></i>&nbsp;&nbsp;Portfolio weights must sum to 100%</span>");
    } else {
        $("#button_save_portfolio").removeAttr('disabled');
        var port_table = `Portfolio Allocation<br>`;
        port_table += `<div class="progress text-60-small" style="height: 60px;">`
        backgrounds = [
            'bg-info', 'bg-success', 'bg-warning', 'bg-danger'
        ]
        counter = 0;
        window.portfolio.forEach(function (item, index) {
            ticker = item[0].toUpperCase();
            weight = parseFloat(item[1]) * 100
            port_table += `
                    <div    class="progress-bar ${backgrounds[counter]}"
                            role="progressbar"
                            style="width: ${weight}%;"
                            aria-valuemin="0"
                            aria-valuemax="100">
                            ${ticker}<br>${formatNumber(weight, 2)}%</div>
                `
            counter += 1;
            counter > backgrounds.length ? counter = 0 : counter = counter;
        });
        port_table += `</div>`;
        $(element).html(port_table);
    }
}


function send_message(message, bg = 'info') {
    if (message == 'clear') {
        $(message_element).html("");
        $(message_element).hide("medium");
        return
    }
    var uniqid = Date.now();
    message_element = '#message_alert_area';
    new_html = `
    <div class="col">
        <div id='${uniqid}' class="alert alert-${bg} alert-dismissible" role="alert" data-alert="alert">
            <strong>${message}</strong>
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    </div>
    `;
    $(message_element).html(new_html);
    $(message_element).show("medium");
}


(function ($) {
    $.fn.animateNumbers = function (stop, commas, duration, ease) {
        return this.each(function () {
            var $this = $(this);
            var start = parseInt($this.text().replace(/,/g, ""));
            commas = (commas === undefined) ? true : commas;
            $({ value: start }).animate({ value: stop }, {
                duration: duration == undefined ? 1000 : duration,
                easing: ease == undefined ? "swing" : ease,
                step: function () {
                    $this.text(Math.floor(this.value));
                    if (commas) { $this.text($this.text().replace(/(\d)(?=(\d\d\d)+(?!\d))/g, "$1,")); }
                },
                complete: function () {
                    if (parseInt($this.text()) !== stop) {
                        $this.text(stop);
                        if (commas) { $this.text($this.text().replace(/(\d)(?=(\d\d\d)+(?!\d))/g, "$1,")); }
                    }
                }
            });
        });
    };
})(jQuery);

// Formatter for numbers use
// prepend for currencies, for positive / negative, include prepend = +
// Small_pos signals to hide result - this is due to small positions creating
// unrealistic breakevens (i.e. too small or too large)
function formatNumber(amount, decimalCount = 2, prepend = '', postpend = '', small_pos = 'False', up_down = false, red_green = false, zero_replace = '0.00') {
    if (((amount == 0) | (amount == null)) | (small_pos == 'True')) {
        return zero_replace;
    }
    try {
        var string = ''
        string += (amount).toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: decimalCount, minimumFractionDigits: decimalCount })
        if ((prepend == '+') && (amount > 0)) {
            string = "+" + string
        } else if ((prepend == '+') && (amount <= 0)) {
            string = string
        } else {
            string = prepend + string
        }

        if (up_down == true) {
            if (amount > 0) {
                postpend = postpend + '&nbsp;<img src="static/images/btc_up.png" width="10" height="10"></img>'
            } else if (amount < 0) {
                postpend = postpend + '&nbsp;<img src="static/images/btc_down.png" width="10" height="10"></img>'
            }
        }
        if (red_green == true) {
            if (amount > 0) {
                string = "<span style='color: green'>" + string + "<span>"
            } else if (amount < 0) {
                string = "<span style='color: red'>" + string + "<span>"
            }
        }

        return (string + postpend)
    } catch (e) {
        console.log(e)
    }
};


function formatDate(date) {
    var year = date.getFullYear();

    var month = (1 + date.getMonth()).toString();
    month = month.length > 1 ? month : '0' + month;

    var day = date.getDate().toString();
    day = day.length > 1 ? day : '0' + day;

    return month + '/' + day + '/' + year;
}

function formatDateTime(date) {
    var hours = date.getHours();
    var minutes = date.getMinutes();
    var ampm = hours >= 12 ? 'pm' : 'am';
    hours = hours % 12;
    hours = hours ? hours : 12; // the hour '0' should be '12'
    minutes = minutes < 10 ? '0' + minutes : minutes;
    var strTime = hours + ':' + minutes + ' ' + ampm;
    return (date.getMonth() + 1) + "/" + date.getDate() + "/" + date.getFullYear() + "  " + strTime;
}

var getUrlParameter = function getUrlParameter(sParam) {
    var sPageURL = window.location.search.substring(1),
        sURLVariables = sPageURL.split('&'),
        sParameterName,
        i;

    for (i = 0; i < sURLVariables.length; i++) {
        sParameterName = sURLVariables[i].split('=');

        if (sParameterName[0] === sParam) {
            return sParameterName[1] === undefined ? true : decodeURIComponent(sParameterName[1]);
        }
    }
};




function heat_color(object, inverse = false) {
    // Get all data values from our table cells making sure to ignore the first column of text
    // Use the parseInt function to convert the text string to a number

    // Let's create a heatmap on all heatmap values
    // Function to get the max value in an Array
    Array.max = function (array) {
        return Math.max.apply(Math, array);
    };

    // Function to get the min value in an Array
    Array.min = function (array) {
        return Math.min.apply(Math, array);
    };

    var counts_positive = []
    var counts_negative = []

    var tbody = $(object).getElementsByTagName('tbody')[0];
    var cells = tbody.getElementsByTagName('td');

    for (var i = 0, len = cells.length; i < len; i++) {
        if (parseInt(cells[i].innerHTML, 10) > 0) {
            counts_positive.push(parseInt(cells[i].innerHTML, 10));
        }
        else if (parseInt(cells[i].innerHTML, 10) < -0) {
            counts_negative.push(parseInt(cells[i].innerHTML, 10));
        }
    }

    // run max value function and store in variable
    var max = Array.max(counts_positive);
    var min = Array.min(counts_negative) * (-1);

    n = 100; // Declare the number of groups

    // Define the ending colour, which is white
    xr = 250; // Red value
    xg = 250; // Green value
    xb = 250; // Blue value

    // Define the starting colour for positives
    yr = 165; // Red value 243
    yg = 255; // Green value 32
    yb = 165; // Blue value 117

    if (inverse == true) {
        // Define the starting colour for negatives
        yr = 80; // Red value 243
        yg = 130; // Green value 32
        yb = 200 // Blue value 117
    }

    // Define the starting colour for negatives
    nr = 255; // Red value 243
    ng = 120; // Green value 32
    nb = 120; // Blue value 117

    // Loop through each data point and calculate its % value
    $(object).each(function () {
        if (parseInt($(this).text()) > 0) {
            var val = parseInt($(this).text());
            var pos = parseInt((Math.round((val / max) * 100)).toFixed(0));
            red = parseInt((xr + ((pos * (yr - xr)) / (n - 1))).toFixed(0));
            green = parseInt((xg + ((pos * (yg - xg)) / (n - 1))).toFixed(0));
            blue = parseInt((xb + ((pos * (yb - xb)) / (n - 1))).toFixed(0));
            clr = 'rgb(' + red + ',' + green + ',' + blue + ')';
            $(this).closest('td').css({ backgroundColor: clr });
        }
        else {
            var val = parseInt($(this).text()) * (-1);
            var pos = parseInt((Math.round((val / max) * 100)).toFixed(0));
            red = parseInt((xr + ((pos * (nr - xr)) / (n - 1))).toFixed(0));
            green = parseInt((xg + ((pos * (ng - xg)) / (n - 1))).toFixed(0));
            blue = parseInt((xb + ((pos * (nb - xb)) / (n - 1))).toFixed(0));
            clr = 'rgb(' + red + ',' + green + ',' + blue + ')';
            $(this).closest('td').css({ backgroundColor: clr });
        }
    });
}


function sleep(milliseconds) {
    var start = new Date().getTime();
    for (var i = 0; i < 1e7; i++) {
        if ((new Date().getTime() - start) > milliseconds) {
            break;
        }
    }
}


function export_table(table_id) {
    var titles = [];
    var data = [];

    /*
     * Get the table headers, this will be CSV headers
     * The count of headers will be CSV string separator
     */
    $('#' + table_id + ' th').each(function () {
        var cellData = $(this).text();
        var cleanData = escape(cellData);
        var cleanData = cellData.replace(/,/g, "");
        var cleanData = cleanData.replace(/\s+/g, "  ");
        titles.push(cleanData);
    });

    /*
     * Get the actual data, this will contain all the data, in 1 array
     */
    $('#' + table_id + ' td').each(function () {
        var cellData = $(this).text();
        var cleanData = escape(cellData);
        var cleanData = cellData.replace(/,/g, "");
        var cleanData = cleanData.replace(/\s+/g, "  ");
        data.push(cleanData);
    });


    /*
     * Convert our data to CSV string
     */
    var CSVString = prepCSVRow(titles, titles.length, '');
    CSVString = prepCSVRow(data, titles.length, CSVString);

    /*
     * Make CSV downloadable
     */
    var downloadLink = document.createElement("a");
    var blob = new Blob(["\ufeff", CSVString]);
    var url = URL.createObjectURL(blob);
    downloadLink.href = url;
    downloadLink.download = "download_" + table_id + "_data.csv";

    /*
     * Actually download CSV
     */
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
};

/*
* Convert data array to CSV string
* @param arr {Array} - the actual data
* @param columnCount {Number} - the amount to split the data into columns
* @param initial {String} - initial string to append to CSV string
* return {String} - ready CSV string
*/
function prepCSVRow(arr, columnCount, initial) {
    var row = ''; // this will hold data
    var delimeter = ';'; // data slice separator, in excel it's `;`, in usual CSv it's `,`
    var newLine = '\n'; // newline separator for CSV row

    /*
     * Convert [1,2,3,4] into [[1,2], [3,4]] while count is 2
     * @param _arr {Array} - the actual array to split
     * @param _count {Number} - the amount to split
     * return {Array} - splitted array
     */
    function splitArray(_arr, _count) {
        var splitted = [];
        var result = [];
        _arr.forEach(function (item, idx) {
            if ((idx + 1) % _count === 0) {
                splitted.push(item);
                result.push(splitted);
                splitted = [];
            } else {
                splitted.push(item);
            }
        });
        return result;
    }
    var plainArr = splitArray(arr, columnCount);
    // don't know how to explain this
    // you just have to like follow the code
    // and you understand, it's pretty simple
    // it converts `['a', 'b', 'c']` to `a,b,c` string
    plainArr.forEach(function (arrItem) {
        arrItem.forEach(function (item, idx) {
            row += item + ((idx + 1) === arrItem.length ? '' : delimeter);
        });
        row += newLine;
    });
    return initial + row;
}

// -----------------------------------------------------------------
// HighCharts --- Create Simple charts templates
// -----------------------------------------------------------------

// PIE CHART
// receives: pie_chart (data) in format:
//          [{
//          'name': string,
//          'y': float,
//          'color': hex color
//          }, {....}]
// series_name
// target_div
function draw_pie_chart(pie_chart, series_name, target_div) {
    Highcharts.chart(target_div, {
        colors: ['#058DC7', '#50B432', '#DDDF00', '#ED561B', '#24CBE5', '#64E572',
            '#FF9655', '#FFF263', '#6AF9C4'],
        chart: {
            type: 'pie',
            backgroundColor: 'transparent'
        },
        exporting: {
            enabled: false
        },
        credits: {
            enabled: false,
            text: "",
        },
        title: {
            text: null
        },
        tooltip: {
            pointFormat: '{series.name}: <b>{point.percentage:.2f}%</b>'
        },
        accessibility: {
            point: {
                valueSuffix: '%'
            }
        },
        plotOptions: {
            pie: {
                allowPointSelect: true,
                cursor: 'pointer',
                dataLabels: {
                    position: 'center',
                    distance: 20,
                    enabled: true,
                    backgroundColor: 'transparent',
                    borderRadius: 5,
                    borderWidth: 2,
                    borderColor: 'grey',
                    connectorColor: '#fff',
                    format: '{point.name}: {point.percentage:.2f}%',
                    style: {
                        fontSize: '6px',
                        color: 'white'
                    },
                },
            }
        },
        legend: {
            enabled: false
        },
        series: [{
            innerSize: '40%',
            colorByPoint: true,
            name: series_name,
            data: pie_chart
        }]
    });
}


// Draws a basic chart with limited customization
// chart_types: line, bar, etc... These are the highchart chart types
// chart_data in format :
//              [{
//              name: name,
//              data: data
//              }]
function draw_simple_chart(chart_type, bins, chart_data, name, title, subtitle, target_div) {
    Highcharts.chart(target_div, {
        chart: {
            type: chart_type
        },
        title: {
            text: title
        },
        subtitle: {
            text: subtitle
        },
        xAxis: {
            categories: bins,
            title: {
                text: null
            }
        },
        yAxis: {
            min: 0,
            title: {
                text: name,
                align: 'high'
            },
            labels: {
                overflow: 'justify'
            }
        },
        tooltip: {
            valueSuffix: ''
        },
        plotOptions: {
            bar: {
                dataLabels: {
                    enabled: true
                }
            }
        },
        legend: {
            enabled: false,
        },
        credits: {
            enabled: false
        },
        series: chart_data
    });
}


// Returns a csv from an array of objects with
// values separated by commas and rows separated by newlines
function CSV(array) {

    var result = ''
    for (var key in array) {
        if (array.hasOwnProperty(key)) {
            result += key + "," + array[key] + "\n";
        }
    }
    return result;

}

// Save txt into filename
function download(filename, text) {
    var pom = document.createElement('a');
    pom.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(text));
    pom.setAttribute('download', filename);

    if (document.createEvent) {
        var event = document.createEvent('MouseEvents');
        event.initEvent('click', true, true);
        pom.dispatchEvent(event);
    }
    else {
        pom.click();
    }
}

function updateURLParameter(url, param, paramVal) {
    var TheAnchor = null;
    var newAdditionalURL = "";
    var tempArray = url.split("?");
    var baseURL = tempArray[0];
    var additionalURL = tempArray[1];
    var temp = "";

    if (additionalURL) {
        var tmpAnchor = additionalURL.split("#");
        var TheParams = tmpAnchor[0];
        TheAnchor = tmpAnchor[1];
        if (TheAnchor)
            additionalURL = TheParams;

        tempArray = additionalURL.split("&");

        for (var i = 0; i < tempArray.length; i++) {
            if (tempArray[i].split('=')[0] != param) {
                newAdditionalURL += temp + tempArray[i];
                temp = "&";
            }
        }
    }
    else {
        var tmpAnchor = baseURL.split("#");
        var TheParams = tmpAnchor[0];
        TheAnchor = tmpAnchor[1];

        if (TheParams)
            baseURL = TheParams;
    }

    if (TheAnchor)
        paramVal += "#" + TheAnchor;

    var rows_txt = temp + "" + param + "=" + paramVal;
    return baseURL + "?" + newAdditionalURL + rows_txt;
}


function copyTable(el) {
    var body = document.body, range, sel;
    if (document.createRange && window.getSelection) {
        range = document.createRange();
        sel = window.getSelection();
        sel.removeAllRanges();
        try {
            range.selectNodeContents(el);
            sel.addRange(range);
        } catch (e) {
            range.selectNode(el);
            sel.addRange(range);
        }
    } else if (body.createTextRange) {
        range = body.createTextRange();
        range.moveToElementText(el);
        range.select();
    }
    document.execCommand("Copy");
}


function timeDifference(current, previous, just_now_precision_seconds = 30) {

    var msPerMinute = 60 * 1000;
    var msPerHour = msPerMinute * 60;
    var msPerDay = msPerHour * 24;
    var msPerMonth = msPerDay * 30;
    var msPerYear = msPerDay * 365;

    var elapsed = current - previous;

    if (isNaN(parseFloat(elapsed))) {
        return ("Never")
    }

    if (elapsed < msPerMinute) {
        if (elapsed < just_now_precision_seconds) {
            return "Just Now"
        } else {
            return Math.round(elapsed / 1000) + ' seconds ago';
        }
    }

    else if (elapsed < msPerHour) {
        return Math.round(elapsed / msPerMinute) + ' minutes ago';
    }

    else if (elapsed < msPerDay) {
        return Math.round(elapsed / msPerHour) + ' hours ago';
    }

    else if (elapsed < msPerMonth) {
        return 'approximately ' + Math.round(elapsed / msPerDay) + ' days ago';
    }

    else if (elapsed < msPerYear) {
        return 'approximately ' + Math.round(elapsed / msPerMonth) + ' months ago';
    }

    else {
        return 'approximately ' + Math.round(elapsed / msPerYear) + ' years ago';
    }
}



function pkl_grabber(pickle_file, interval_ms, target_element, status_element = undefined) {
    const socket = new WebSocket("ws://" + location.host + "/pickle");
    socket.addEventListener("message", (ev) => {
        $(target_element).html(ev.data);
    });

    // Executes the function every 1000 milliseconds
    const interval = setInterval(function () {
        if (socket.readyState === WebSocket.CLOSED) {
            if (status_element != undefined) {
                $(status_element).html("<span style='color: red'>Disconnected</span>");
            }
            $(target_element).text("WebSocket Error -- Check if app is running");
        } else {
            socket.send(pickle_file);
            if (status_element != undefined) {
                $(status_element).html("<span style='color: darkgreen'>Connected</span>");
            }
        }
    }, interval_ms);
}


function base_url() {
    return location.protocol + "//" + location.host + "/";
}

function ajax_getter(url, dataType = 'json', async = false) {
    // Note that this is NOT an asynchronous request.
    return_data = "Empty Data";
    $.ajax({
        type: "GET",
        dataType: 'json',
        url: url,
        async: async,
        success: function (data) {
            return_data = data
        },
        error: function (xhr, status, error) {
            return_data = ("Error on request. status: " + status + " error:" + error);
        }
    });
    return return_data;
}

// Sort a list of objects by a certain key
function sortObj(list, key, reverse = false) {
    try {
        function compare(a, b) {
            a = a[key];
            b = b[key];
            var type = (typeof (a) === 'string' ||
                typeof (b) === 'string') ? 'string' : 'number';
            var result;
            if (type === 'string') result = a.localeCompare(b);
            else result = a - b;
            return result;
        }
        if (reverse == true) {
            return list.sort(compare).reverse();
        } else {
            return list.sort(compare);
        }

    } catch (e) {
        console.log("Error sorting list: " + e);
        return list;

    }
}

// source: https://stackoverflow.com/questions/64254355/cut-string-into-chunks-without-breaking-words-based-on-max-length
function splitString(n, str) {
    let arr = str?.split(' ');
    let result = []
    let subStr = arr[0]
    for (let i = 1; i < arr.length; i++) {
        let word = arr[i]
        if (subStr.length + word.length + 1 <= n) {
            subStr = subStr + ' ' + word
        }
        else {
            result.push(subStr);
            subStr = word
        }
    }
    if (subStr.length) { result.push(subStr) }
    return result
}


function initialize_tooltips() {
    $(".tooltip").tooltip("hide");
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    })

}

// Shorten strings
String.prototype.trimEllip = function (length) {
    beg_end = (length / 2);
    tail_str = this.substr(this.length - beg_end);
    return this.length > length ? this.substring(0, beg_end) + "..." + tail_str : this;
}


function sats_btc(sats) {
    sats = parseInt(sats);
    if (sats <= 100000000) {
        return formatNumber(sats, 0, '', ' sats')
    } else {
        sats = parseFloat(sats) / 100000000;
        return formatNumber(sats, 8, '₿ ')
    }
}

function parsePercentage(s) {
    if (s == undefined) {
        return "0.00%";
    }
    if (s.includes("%")) {
        perc = parseFloat(s.replace("%", ""))
    } else {
        perc = parseFloat(s)
    }
    perc = formatNumber(perc, 2) + "%"
    if (perc == "NaN%") {
        return "0.00%";
    }
    return perc

}



function red_green() {
    // re-apply redgreen filter (otherwise it's all assumed positive since fields were empty before ajax)
    $(".redgreen").removeClass('red_negpos');
    $(".redgreen").addClass('green_negpos');
    $(".redgreen:contains('-')").removeClass('green_negpos');
    $(".redgreen:contains('-')").addClass('red_negpos');
    // Hide NaN
    $(".redgreen:contains('NaN%')").addClass('text-white');
}
