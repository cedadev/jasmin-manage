(function($) {
    $(function() {
        // Copy the highlight class onto the nearest cell
        $('.results .highlight').each(function() {
            var $el = $(this);
            $el.closest('td').addClass($el.attr("class"));
            $el.removeClass();
        });
        // For tabular inlines, copy to the nearest cell
        $('.tabular .highlight').each(function() {
            var $el = $(this);
            console.log($el.closest('td'))
            $el.closest('td').addClass($el.attr("class"));
            $el.removeClass();
        });
        // For forms, copy to the nearest row
        $('div.form-row .highlight').each(function() {
            var $el = $(this);
            $el.closest('.form-row').addClass($el.attr("class"));
            $el.removeClass();
        });
    });
})(jQuery);
