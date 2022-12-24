$(document).ready(function () {
    $("#signup_box").hide();


    $("#back_button").click(function () {
        $("#signup_box").hide("slow");
        $("#login_box").show("slow");
    });

    $("#create_account").click(function () {
        $("#signup_box").show("slow");
        $("#login_box").hide("slow");
    });

    $("#login_anon").click(function () {
        window.location.href = "/"
    });

});