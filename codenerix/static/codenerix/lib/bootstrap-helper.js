function findBootstrapEnvironment() {
    var envs = ["ExtraSmall", "Small", "Medium", "Large"];
    var envValues = ["xs", "sm", "md", "lg"];
    var $el = $('<div>');
    $el.appendTo($('body'));
    for (var i = envValues.length - 1; i >= 0; i--) {
        var envVal = envValues[i];
        $el.addClass('hidden-'+envVal);
        if ($el.is(':hidden')) {
            $el.remove();
            // return envs[i]
            return envValues[i]
        }
    };
};
