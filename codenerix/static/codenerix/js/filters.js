/*
 *
 * django-codenerix
 *
 * Copyright 2017 Centrologic Computational Logistic Center S.L.
 *
 * Project URL : http://www.codenerix.com
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

 angular.module('codenerixFilters', [])

.filter('codenerix', function() {
  return function(input, kind) {
    if ((kind==null) || (kind==undefined)) {
        // No kind defined
        return input;
    } else if (kind=='skype') {
        return "<a ng-click='$event.stopPropagation();' href='tel:"+input+"'>"+input+"</a>";
    } else if (kind=='image') {
        return "<img src='"+input+"'  />";
    } else {
        console.error("AngularJS filter 'codenerix' got a wrong kind named '"+kind+"'");
        return input;
    }
  };
})

.filter('nicenull', function() {
  return function(input) {
    return input ? input : '---';
  };
})

.filter('choice_match', function() {
    return function(input, source) {
        var answer=input+"*";
        angular.forEach(source,function(e) {
            if (e[0]==input) {
                answer=e[1];
                return;
            }
        });
        return answer;
    };
})
.filter('split', function() {
    return function(input, splitChar, splitIndex) {
        // do some bounds checking here to ensure it has that index
        return input.split(splitChar)[splitIndex];
    }
})
.filter('highlightRow', function() {
    return function(input, txt) {
        var result = '';
        if (txt!==undefined){
            txt = String(txt).trim()
            var index = 0;
            var search = -1;
            var search_old = -1;
            var len = txt.length;

            var txt_m = txt.toUpperCase();
            var input_m = input.toUpperCase()

            if (len!=0 && txt!="" && input.length>0){
                while ((search=input_m.indexOf(txt_m, index) )!=-1){
                    if (search==search_old){
                        break;
                    }
                    result=result+input.substring(index, search);
                    result=result+'<span class="standout">'+input.substring(result.length, result.length+len)+'</span>';
                    index=search+len;
                    search_old = search;
                }
            }
        }
        if (result == ''){
            result = input;
        }else if(index<input.length){
            result=result+input.substring(search_old+len);
        }
        return result;
    }
})

.filter('highlightSelect', function() {
    function escapeRegexp(queryToEscape) {
        return queryToEscape.replace(/([.?*+^$[\]\\(){}|-])/g, '\\$1');
    };
    
    return function(matchItem, query) {
        return query && matchItem ? matchItem.replace(new RegExp(escapeRegexp(query), 'gi'), '<span class="ui-select-highlight">$&</span>') : matchItem;
    };
})

.filter('weekday', function() {
    return function(input) {
        
        var result = '---';
        
        if (input == 1)
            result = 'Monday'
        else if (input == 2)
            result = 'Tuesday'
        else if (input == 3)
            result = 'Wednesday'
        else if (input == 4)
            result = 'Thursday'
        else if (input == 5)
            result = 'Friday'
        else if (input == 6)
            result = 'Saturday'
        else if (input == 7)
            result = 'Sunday'
        
        return result;
    };
})
.filter('abs', function () {
    return function(val) {
        return Math.abs(val);
    }
})
.filter('length', function () {
    return function(dict) {
        var count=0;
        angular.forEach(dict,function(value,key) {
            count++;
        });
        return count;
    }
})
.filter('base64_encode', function () {
    return function(val) {
        return btoa(val);
    }
})
.filter('base64_decode', function () {
    return function(val) {
        return atob(val);
    }
})
.filter('htmlToPlaintext', function() {
    return function(text) {
        return angular.element(text).text();
        //return  text ? String(text).replace(/<[^>]+>/gm, '') : '';
    };
  }
);
