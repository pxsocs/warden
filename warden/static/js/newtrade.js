$(document).ready(function () {
  calccf();

});

$(function () {
  $('#submit_button').click(function () {
    $('#submit_button').prop('value', 'Please wait. Including transaction and generating new NAV. This can take a while. Wait...');
  });
});

$(function () {
  $("#tradeaccount").autocomplete({
    source: function (request, response) {
      $.ajax({
        url: "/aclst?",
        dataType: "json",
        data: {
          term: request.term
        },

        success: function (data) {
          response($.map(data, function (item) {
            return {
              label: item,
              value: item
            }
          }));
        }

      });
    },
    minLength: 0
  });
});


$(function () {
  $("#tickerauto").autocomplete({
    source: function (request, response) {
      $.ajax({
        url: "/assetlist?json=true&q=&",
        dataType: "json",
        data: {
          term: request.term
        },

        success: function (data) {
          console.log(data)
          response($.map(data, function (item) {
            return {
              label: item.symbol + " | " + item.name,
              value: item.symbol,
            }
          }));
        }
      });
    },
    minLength: 2
  });
});



function calccf() {

  var q = 0
  var p = 0
  var f = 0

  q = parseFloat($('#quant').val());
  p = parseFloat($('#price').val());
  f = parseFloat($('#fees').val());

  fin = (q * p) + f
  if (isNaN(fin)) {
    fin = 0
  }

  // fin = fin.value().toLocaleString('en-US', { style: 'decimal', maximumFractionDigits : 2, minimumFractionDigits : 2 })
  $('#cash').val(fin.toLocaleString('en-US', { style: 'decimal', maximumFractionDigits: 2, minimumFractionDigits: 2 }));

}

$(function () {
  $('#trade_select, #trade_price, #trade_fees, #trade_quantity, #trade_operation').change(function () {
    calccf();
  });
});
