(function($) {
    $(function() {
        // Copy the highlight class onto the nearest td
        $('.results .highlight').each(function() {
            var $el = $(this);
            $el.closest('td').addClass($el.attr("class"));
            $el.removeClass();
        });
        $('.form-row .highlight').each(function() {
            var $el = $(this);
            $el.closest('.form-row').addClass($el.attr("class"));
            $el.removeClass();
        });
    });
})(jQuery);
