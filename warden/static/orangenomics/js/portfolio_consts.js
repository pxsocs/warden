const empty_portfolio_line = `
<tr class='porfolio_line'>
      <td style='width:7%;'><span id='start_here'>
        <button class="btn btn-outline-light btn-sm asset_info">
                <i class="fa-solid text-white fa-circle-info"></i>
                </button>
      </span></td>
      <td>
        <input
          type="text"
          class="input-group input-group-sm ticker_input"
          placeholder="enter a ticker"
        />
      </td>
      <td>
        <input
          type="text"
          class="input-group input-group-sm name_input"
          placeholder=""
          disabled
        />
      </td>
      <td class="text-end">
        <input
          type="percentage"
          class="input-group input-group-sm text-end weight_input"
          placeholder="0.00%"
        />
      </td>
      <td style='width:7%;'>
        <button class="btn btn-danger btn-sm remove_asset">
          <i class="fa-solid fa-square-minus"></i>
        </button>
      </td>
    </tr>

    `;


$(document).ready(function () {
    window.portstats = {
        'portfolio_total': 1
    };
    init_portfolio();
});

// Function to run on load - if a portfolio is passed, it will build
// with this portfolio, otherwise it will include an empty line
function init_portfolio(portfolio = window.portfolio) {
    rows = ""
    // If a portfolio is passed, build the portfolio with this portfolio
    if (typeof portfolio !== 'undefined' && portfolio.length > 0) {
        // Otherwise, build the portfolio with an empty line
        rows = build_portfolio(portfolio);
    } else {
        rows = empty_portfolio_line + update_total()
    }
    window.rows = rows
    $('#portfolio_body').html(rows);
    portfolio_update();
};


function check_start() {
    started = `
                <button class="btn btn-outline-light btn-sm asset_info">
                <i class="fa-solid text-white fa-circle-info"></i>
                </button>
                `;
    not_started = `<span class='float-end next-arrow'>
                        <i class="fa-solid fa-circle-arrow-right fa-2x"></i>
                    </span>`;
    if (window.portfolio == '') {
        $('#start_here').html(not_started);
        $('#dates_input').hide();
        $('#start_input').hide();
    } else {
        if (window.portfolio[0][0] == '') {
            $('#start_here').html(not_started);
            $('#dates_input').hide();
            $('#start_input').hide();
        } else {
            $('#start_here').html(started);
            $('#start_here_text').hide();
            $('#dates_input').show();
            $('#start_input').show();
        }
    }
}

// Builds the portfolio
function build_portfolio(portfolio) {
    rows = ''
    portfolio.forEach(function (item, index) {
        // get data for this ticker
        ticker = item[0].toUpperCase();
        weight = parseFloat(item[1]) * 100
        url = 'historical_data?ticker=' + ticker;
        data = ajax_getter(url)
        if (data.empty == true) {
            rows += `<tr class='porfolio_line' ><td style='width:7%;'></td><td colspan="2">`
            rows += `<span class='text-warning text-small text-center'><i class="fa-solid fa-lg fa-triangle-exclamation"></i>&nbsp;&nbsp;no data found for ticker ${ticker}. remove from list.</span>`
            rows += `
                <td class="text-end">
                    <input
                    type="percentage"
                    class="input-group input-group-sm text-end weight_input"
                    value="${formatNumber(weight, 2)}%"
                    />
                </td>
                <td style='width:7%;'>
                    <button class="btn btn-danger btn-sm remove_asset">
                    <i class="fa-solid fa-square-minus"></i>
                    </button>
                </td>
            `
            rows += `</td></tr > `
            return
        } else {
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
                $('#end_date').val(end_date.toISOString().split('T')[0])
            }
            asset = data.ticker_info[0]['name']
            rows += `
        <tr class='porfolio_line' >
            <td style='width:7%;'>
                <button class="btn btn-outline-light btn-sm asset_info">
                <i class="fa-solid text-white fa-circle-info"></i>
                </button>
            </td>
            <td>
                <input
                type="text"
                class="input-group input-group-sm ticker_input"
                value="${ticker}"
                />
            </td>
            <td>
                <input
                type="text"
                class="input-group input-group-sm name_input"
                disabled
                value="${asset}"
                />
            </td>
            <td class="text-end">
                <input
                type="percentage"
                class="input-group input-group-sm text-end weight_input"
                value="${formatNumber(weight, 2)}%"
                />
            </td>
            <td style='width:7%;'>
                <button class="btn btn-danger btn-sm remove_asset">
                <i class="fa-solid fa-square-minus"></i>
                </button>
            </td>
            </tr >
        `;
        }
    });
    rows = rows.replace('\n', '');
    return (rows)
}

function update_total() {
    total = window.portstats.portfolio_total
    if (isNaN(total)) {
        total = 0
    }
    check_start();
    if (Math.round(total * 100) / 100 != 1) {
        msg = `total does not add to 100%. `
        msg += `portfolio will be proportionally reweighted to 100% when submitted.`
        note = `<span class='float-start text-yellow url-clean'
                    data-bs-toggle="tooltip"
                    data-bs-placement="right"
                    title="${msg}">
                    <i class="fa-solid fa-triangle-exclamation"></i> </span>`

        note += `<br><button
                    class="btn btn-warning btn-sm float-end align-self-end text-small"
                    id="reweight"
                    >
                    reweight to 100%
        </button>`
        initialize_tooltips();
    } else {
        note = ''
    }

    if (isNaN(window.portstats.portfolio_total)) {
        note = ''
    }

    total_html = `
    <td></td>
      <td>
        <button class="btn btn-success btn-sm add_asset">
          <i class="fa-solid fa-plus text-white"></i>&nbsp;&nbsp; add asset
        </button>
      </td>
      <td class="text-end text-large text-small text-light">total</td>
      <td class="text-end text-large text-small text-light" id="weights_total">
          ${formatNumber(total * 100, 2)}%
          ${note}
      </td>
      <td></td>
    `;

    // Check if a total TR already exists, if so, replace. Otherwise, add.
    // <tr class="total_portfolio"></tr>
    element = $('#portfolio_body tr.total_portfolio')
    if (element.length > 0) {
        element.html(total_html)
    } else {
        total_html = `<tr class="total_portfolio">${total_html}</tr>`
        tbody = $("#portfolio_body")
            .find('tr:last').after(total_html)
    }

}

function table_to_portfolio() {
    p = []
    $('#portfolio_body tr').each(function (index, item) {
        ticker = $(item).find('.ticker_input').val()
        weight = $(item).find('.weight_input').val()
        if (weight != undefined) {
            weight = weight.replace('%', '')
            weight = parseFloat(weight) / 100
            p.push([ticker, weight])
        };

    });
    return (p)
}


function table_to_names() {
    tickers = []
    $('#portfolio_body tr').each(function (index, item) {
        ticker = $(item).find('.ticker_input').val()
        asset = $(item).find('.name_input').val()
        tickers.push([ticker, asset])
    });
    return (tickers)
}
