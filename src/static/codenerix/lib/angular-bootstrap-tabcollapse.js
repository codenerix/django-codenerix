var tabs = function ($scope) { $scope.tabbed=(findBootstrapEnvironment()!='xs'); };
$(function(){
    $('#collapsabletabs').tabCollapse({});
    $('#collapsabletabs').on('show-tabs.bs.tabcollapse', function(){
        var scope = angular.element('#tabs').scope();
        scope.tabbed=true;
        scope.$apply();
    });
    $('#collapsabletabs').on('shown-accordion.bs.tabcollapse', function(){
        var scope = angular.element('#tabs').scope();
        scope.tabbed=false;
        scope.$apply();
    });
});
