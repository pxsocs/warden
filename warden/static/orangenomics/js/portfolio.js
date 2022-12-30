var portstats = {
    'portfolio': [],
    'portfolio_total': 0,
    'number_of_assets': 0,
    'start_date': 0,
    'end_date': Infinity,
    'ticker_names': [],
    'rebalance': "never",
}

// Consider making this list = all digital assets excluding BTC
const shitcoins = ['ETH', 'LTC', 'XRP', 'BCH',
    'EOS', 'XLM', 'TRX', 'ADA', 'NEO', 'IOTA', 'DOGE',
    'DASH', 'XVG']

$(document).ready(function () {
    $('#ticker_results').hide();
    $('#portfolio_results').hide();
    initialize_tooltips();

    // if there's a change in a weight field
    $(document).on('change', '.weight_input', function () {
        var element = this
        var table = $(this).closest('table')
        // Get weight from input
        var weight_field = $(this).parent().parent().find('.weight_input')
        weight = weight_field.val()
        // parse the percentage input
        weight = parsePercentage(weight)
        weight_field.val(weight)
        portfolio_update()
    });

    // Portfolio reweight is clicked
    $(document).on('click', '#reweight', function () {
        portfolio_reweight();
        portfolio_update();
    });

    // Portfolio rebalance is changed
    $(document).on('change', '#rebalance', function () {
        window.portstats.rebalance = $('#rebalance').val();
    });

    // Start Date is changed
    $(document).on('change', '#start_date', function () {
        window.portstats.start_date = $('#start_date').val();
    });

    // End Date is changed
    $(document).on('change', '#end_date', function () {
        window.portstats.end_date = $('#end_date').val();
    });


    // Go to next step
    $(document).on('click', '#analyze', function () {
        portfolio_reweight();
        portfolio_update();
        ready = run_checks();
        p = encodeURIComponent(JSON.stringify(window.portstats.portfolio))
        t = encodeURIComponent(JSON.stringify(window.portstats.ticker_names))
        s = encodeURIComponent(JSON.stringify(window.portstats.start_date))
        e = encodeURIComponent(JSON.stringify(window.portstats.end_date))
        r = encodeURIComponent(JSON.stringify(window.portstats.rebalance))
        if (ready == true) {
            $('#loading_modal').modal('show');
            url = base_url() + 'orangenomics/analyze?portfolio=' + p + '&tickers=' + t + '&start_date=' + s + '&end_date=' + e + '&rebalance=' + r
            window.location.href = url
        }
    });



    // remove asset button is clicked
    $(document).on('click', '.remove_asset', function () {
        var element = this
        var table_size = $('#portfolio_body >tr').length;
        // Make sure at least one line is left
        if (table_size > 2) {
            var table = $(this).closest('table')
            // Get ticker from input
            var ticker_field = $(this).parent().parent().find('.ticker_input')
            ticker = ticker_field.val()
            // remove asset from portfolio
            portfolio.splice(portfolio.indexOf(ticker), 1)
            // remove row from table
            $(this).parent().parent().remove()
            // update total
            table.find('.total_portfolio').html(update_total())
            portfolio_update()
        }

    });

    // add asset button is clicked
    $(document).on('click', '.add_asset', function () {
        tbody = $("#portfolio_body")
            .find('tr:last').prev()
            .after(empty_portfolio_line)
    });

    // If asset info is clicked
    $(document).on('click', '.asset_info', function () {
        $('#ticker_results').show("fast");
        var ticker = $(this).parent().parent().parent().find('.ticker_input').val()
        ticker = ticker.toUpperCase();
        $('#ticker_results').html(`
        <div class="d-flex align-items-center">
        <strong class='text-small'>loading ${ticker} data...</strong>
        <div class="spinner-border spinner-border-sm text-warning ms-auto" role="status" aria-hidden="true"></div>
        </div>
        `)

        var element = this
        setTimeout(
            function () {
                get_ticker_info(ticker, element);
            }, 500);
    });

    // Ticker field is changed
    $(document).on('change', '.ticker_input', function () {
        $('#ticker_results').show("fast");
        var ticker = $(this).val();
        ticker = ticker.toUpperCase();
        var name_field = $(this).parent().parent().find('.name_input')
        name_field.val('loading...')
        // HTML: loading ticker
        $('#ticker_results').html(`
        <div class="d-flex align-items-center">
        <strong class='text-small'>loading ${ticker} data...</strong>
        <div class="spinner-border spinner-border-sm text-warning ms-auto" role="status" aria-hidden="true"></div>
        </div>
        `)
        var element = this
        // Get weight from input
        var weight_field = $(this).parent().parent().find('.weight_input')
        weight = weight_field.val()
        // parse the percentage input
        weight = parsePercentage(weight)
        weight_field.val(weight)
        // Need to wait until animation is over - otherwise doesn't show
        setTimeout(
            function () {
                get_ticker_info(ticker, element);
            }, 500);
        portfolio_update();
    });
});


function update_portfolio_stats() {
    $('#portfolio_results').show();
    portfolio = table_to_portfolio()
    interval_msg = 500;

    const interval = setInterval(function () {
        target = '#portfolio_results';
        html = `<div class="text-light text-end text-small">Portfolio Summary</div>`;
        html += `
        <table class="table-condensed style="padding-top:5px;">
            <tbody>
                <tr>
                    <th>assets</th>
                    <td class='text-end'>${formatNumber(window.portstats.number_of_assets, 0)}</td>
                </tr>
                <tr>
                    <th>allocated</th>
                    <td class='text-end'>${formatNumber(window.portstats.portfolio_total * 100, 2)}%</td>
                </tr>
                <tr>
                    <th>unallocated</th>
                    <td class='text-end'>${formatNumber((1 - window.portstats.portfolio_total) * 100, 2)}%</td>
                </tr>
                <tr>
                    <th>data range</th>`

        if (window.portstats.start_date != 0) {
            html += `
                    <td class='text-end'>${formatDate(new Date(window.portstats.start_date))} -- ${formatDate(new Date(window.portstats.end_date))}</td>`
        } else {
            html += `<td class='text-end text-warning'>not available</td>`
        }

        html += `</tr>
                </tbody>
                </table>
                `;

        $(target).html(html);
    }, interval_msg);
    initialize_tooltips();
}

function get_ticker_info(ticker, element) {
    url = base_url() + 'historical_data?ticker=' + ticker;
    console.log(url);
    data = ajax_getter(url)
    if (data.empty == true) {
        $('#ticker_results').html(`<span class='text-warning text-small'><i class="fa-solid fa-lg fa-triangle-exclamation"></i>&nbsp;&nbsp;no data found for ticker ${ticker}</span>`)
        $(element).parent().parent().find('.name_input').val("ticker not found")
        return
    }
    // Check if shitcoin
    if (shitcoins.includes(ticker)) {
        shitcoin_html = `<i class="fa-solid fa-poop fa-lg text-brown" data-bs-toggle="tooltip"
                        data-bs-placement="right"
                        title="WARNING: history does not side with altcoins. Include them at portfolio at own risk."></i>`
    } else {
        shitcoin_html = ''
    }
    html = `<div class="text-light text-end text-small">search results: <span class="text-orange">${ticker}</span></div>`;
    // Create table with results
    html += `
        <table class="table-condensed style="padding-top:5px;">
            <tbody>
                <tr>
                    <th>asset name</th>
                    <td class='text-end'>${data.ticker_info[0]['name']}&nbsp;<span class='text-small text-muted'>(${data.ticker_info[0]['symbol']})&nbsp;${shitcoin_html}</span></td>
                </tr>
                <tr>
                    <th>latest price</th>
                    <td class='text-end'>${formatNumber(data.latest_price, 2)} <span class='text-small text-muted'>(in ${data.ticker_info[0]['fx']})</span></td>
                </tr>
                <tr>
                    <th></th>
                    <td class='text-end'>${data.ticker_info[0]['notes']}</td>
                </tr>
                <tr>
                    <th>data range</th>
                    <td class='text-end'>${formatDate(new Date(data.first_date))} -- ${formatDate(new Date(data.latest_date))}</td>
                </tr>
                <tr>
                    <th></th>
                    <td class='text-end'><div class="text-small text-muted">(${data.num_days} data points)</div></td>
                </tr>

                <tr>
                    <th>api source</th>
                    <td class='text-end'><a href='${data.source_url}' target='_blank'>${data.source}</a></td>
                </tr>
            </tbody>
        </table>
    `;

    $('#ticker_results').html(html);
    // Update ticker from input
    $(element).val(data.ticker_info[0]['symbol'])
    // include name on portfolio list
    $(element).parent().parent().find('.name_input').val(data.ticker_info[0]['name'])
    // // update portfolio metadata
    start_date = new Date(data.first_date)
    if (start_date > window.portstats.start_date) {
        window.portstats.start_date = start_date
        $('#start_date').removeAttr('disabled');
        $('#start_date').val(start_date.toISOString().split('T')[0])
    }
    end_date = new Date(data.latest_date)
    if (end_date < window.portstats.end_date) {
        window.portstats.end_date = end_date
        $('#end_date').removeAttr('disabled');
        $('#rebalance').removeAttr('disabled');
        $('#end_date').val(end_date.toISOString().split('T')[0])
    }
    initialize_tooltips();

};

function portfolio_update() {
    p = table_to_portfolio()
    total = 0
    p.forEach(function (item, index) {
        total += parseFloat(item[1])
    });
    window.portstats.portfolio = p
    window.portstats.portfolio_total = total
    window.portstats.number_of_assets = p.length

    // Update Stats
    update_portfolio_stats()

    // Update Total
    update_total()

    // update Names & tickers
    window.portstats.ticker_names = table_to_names()

};

function portfolio_reweight() {
    p = window.portstats.portfolio
    element = $('#portfolio_body')
    p.forEach(function (item, index) {
        weight = parseFloat((p[index][1] / window.portstats.portfolio_total))
        window.portstats.portfolio[index][1] = weight
        element.find('tr').eq(index).find('.weight_input').val(formatNumber(weight * 100, 2) + '%')
    });

}


function run_checks() {
    // Check if total = 100
    if (Math.round(window.portstats.portfolio_total * 100) / 100 != 1) {
        send_message('total portfolio weight is not 100%', 'warning');
        return (false)
    }

    // Check if ticker name is not "ticker not found"
    // or empty
    // Check if there is a weight
    $('#portfolio_body tr').each(function (index, item) {
        // checks for ticker
        ticker = $(item).find('.ticker_input').val()
        if ((ticker == '') || (ticker == 'ticker not found')) {
            $(item).closest('tr').addClass('bg-error')
            send_message('one or more tickers are invalid', 'warning');
            return (false)
        }

        asset = $(item).find('.name_input').val()
        if ((asset == '') || (asset == 'ticker not found')) {
            $(item).closest('tr').addClass('bg-error')
            send_message('one or more tickers are invalid', 'warning');
            return (false)
        }

        weight = $(item).find('.weight_input').val()
        if ((weight == '') || (weight == 'NaN%')) {
            $(item).closest('tr').addClass('bg-error')
            send_message('check weights', 'warning');
            return (false)
        }
    });

    // passed all checks
    return (true)
}


