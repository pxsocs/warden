// Modified from Source:
// https://www.jqueryscript.net/animation/Number-Count-Up-Down-Animation-jQuery.html#google_vignette

'use strict';

(function ($) {
    $.fn.animate_number = function (_options) {
        var defaults = {
            start_value: 0
            , end_value: 100
            , duration: 2000  // Milliseconds
            , before: null
            , after: null
            , prepend: ''
            , postpend: ''
            , decimals: 2
        }

            , options = $.extend(defaults, _options)

            , UPDATES_PER_SECOND = 60
            , ONE_SECOND = 1000  // Milliseconds
            , MILLISECONDS_PER_FRAME = ONE_SECOND / UPDATES_PER_SECOND
            , DIRECTIONS = { DOWN: 0, UP: 1 }
            , ONE_THOUSAND = 1000

            , $element = $(this)
            , interval = Math.ceil(options.duration / MILLISECONDS_PER_FRAME)
            , current_value = options.start_value
            , increment_value = (options.end_value - options.start_value) / interval
            , direction = options.start_value < options.end_value ? DIRECTIONS.UP : DIRECTIONS.DOWN
            ;

        function format_thousand(_value) {
            formatNumber(_value, decimals, prepend, postpend);
        }


        function animate() {
            if (current_value !== options.end_value) {
                var new_value = current_value + increment_value;

                if (direction === DIRECTIONS.UP) {
                    current_value = new_value > options.end_value ? options.end_value : new_value;
                } else {
                    current_value = new_value < options.end_value ? options.end_value : new_value;
                }

                new_value = formatNumber(new_value, options.decimals, options.prepend, options.postpend);

                $element.html(new_value);
                requestAnimationFrame(animate);
            } else {
                if (typeof options.after === 'function') {
                    options.after($element, current_value);
                }
            }
        }

        if (typeof options.before === 'function') {
            options.before($element);
        }

        animate();
    };
}(jQuery));

