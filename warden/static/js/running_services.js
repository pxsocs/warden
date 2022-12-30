$(document).ready(function () {
    var intervalId = window.setInterval(function () {
        run_ajax()
    }, 1000);
});

function run_ajax() {
    const currentTimeStamp = new Date().getTime();
    table_header = `
    <table class='table table-sm table-striped small-text' id='list_table_json'>
        <thead>
          <tr>
            <th></th>
            <th class='text-start'>Service</th>
            <th class='text-start'>Location</th>
            <th class='text-end'>Last time reached</th>
            <th></th>
          </tr>
        </thead>
    <tbody>
    `
    table_footer = "</tbody></table>"
    $.ajax({
        type: "GET",
        dataType: 'json',
        url: "/get_pickle?filename=services_found&serialize=False",
        success: function (data) {
            $('#output').html('')
            if ((data == '') || (data == 'file not found')) {
                $('#output').html(
                    "<div class='small alert alert-warning' role='alert'>No running services found" +
                    "</div>"
                )
            } else {
                var event_data = '';
                $.each(data, function (index, value) {
                    time_ago = timeDifference(currentTimeStamp, parseFloat(value['last_update'] * 1000))
                    difference = (currentTimeStamp - parseFloat(value['last_update'] * 1000)) / 1000
                    if (difference < 180) {
                        icon = "<i style='color: green' class='far fa-lg fa-check-circle'></i>"
                    } else if (difference < 400) {
                        icon = "<i style='color: orange' class='fas fa-lg fa-exclamation-triangle'></i>"
                    } else {
                        icon = "<i style='color: red' class='far fa-lg fa-stop-circle'></i>"
                    }

                    /*console.log(value);*/
                    event_data += '<tr>';
                    event_data += "<td class='text-center'>" + icon + '</td>';
                    event_data += "<td class='text-start'>" + value['service'] + '</td>';
                    event_data += "<td class='text-start'><a href='" + value['url'] + "' target='_blank'>" + value['url'] + "</a></td>";
                    event_data += "<td class='text-end'>" + time_ago + '</td>';
                    event_data += "<td class='text-end'><a href='/host_list?delete=" + encodeURIComponent(value['url']) + "'><i style='color: red' class='far fa-trash-alt'></i></a> </td>";
                    event_data += '</tr>';
                });
                $("#output").html(table_header + event_data + table_footer)

            }

        },
        error: function (xhr, status, error) {
            $('#output').html(
                "<div class='small alert alert-danger' role='alert'>An error occured while getting service list..." +
                "</div>"
            )
        }
    });
}

