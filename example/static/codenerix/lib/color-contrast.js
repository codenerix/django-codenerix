'use strict';

angular.module('colorContrast', [])
  .directive('colorContrast', function () {
    
    var DARK = '000000';
    
    var LIGHT = 'FFFFFF';
    
    // 24 WAYS - http://24ways.org/2010/calculating-color-contrast/
    function getContrastYIQ(hexcolor){
    	var r = parseInt(hexcolor.substr(0,2),16);
    	var g = parseInt(hexcolor.substr(2,2),16);
    	var b = parseInt(hexcolor.substr(4,2),16);
    	var yiq = ((r*299)+(g*587)+(b*114))/1000;
    	return (yiq >= 128) ? DARK : LIGHT;
    };

    function stripNumberSign(color){
        if(color[0] === "#") {
            color = color.substring(1, color.length);
        }
        return color;
    };
    
    return {
      restrict: 'A',
      link: function postLink(scope, element, attrs) {
        attrs.$observe('colorContrast', function(color) {
          if (color) {
            color = stripNumberSign(color);
            element.css("background-color", "#" + color);
            element.css("color", "#" + getContrastYIQ(color));
          }
        });
      }
    };
    
  });
