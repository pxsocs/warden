
$(document).ready(function () {
    $('#loading').show();
    $('#quote_section').hide();
    satoshi_refresh();

    $('#refresh_button').click(function () {
        $('#refresh_button').html('Please wait...');
        $('#refresh_button').prop('disabled', true);
        console.log('click')
        satoshi_refresh();
    });

});

function satoshi_refresh() {
    $.ajax({
        type: 'GET',
        url: '/satoshi_quotes_json',
        dataType: 'json',
        success: function (data) {
            // Parse data
            $('#loading').hide();
            $('#quote_section').show();
            $('#load_quote').html(data['text']);
            $('#load_source').html(data['medium']);
            $('#load_date').html(data['date']);
            $('#subject').html(data['category']);
            $('#refresh_button').html('Refresh');
            $('#refresh_button').prop('disabled', false);

        },
        error: function (xhr, status, error) {
            console.log(status);
            console.log(error);
            $('#alerts').html("<div class='small alert alert-danger alert-dismissible fade show' role='alert'>An error occured while refreshing data." +
                "<button type='button' class='close' data-dismiss='alert' aria-label='Close'><span aria-hidden='true'>&times;</span></button></div>")
            $('#refresh_button').html('Refresh Error. Try Again.');
            $('#refresh_button').prop('disabled', false);
        }

    });

}




