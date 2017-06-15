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

 'use strict';

// Add the remove method to the Array structure
Array.prototype.remove = function(from, to) {
    var rest = this.slice((to || from) + 1 || this.length);
    this.length = from < 0 ? this.length + from : from;
    return this.push.apply(this, rest);
};

function multi_dynamic_select_dict(arg, form){
    var dict = {};
    angular.forEach(arg, function(value, key){
        dict[value] = form+"."+value;
    });
    return dict;
}

// delete item form sublist in details view
function del_item_sublist(id, msg, url, scope, $http){
    id = String(id);
    if (confirm(msg)){
        
        $http.post( url, {}, {} )
        .success(function(answer, stat) {
            // Check the answer
            if (stat==200 || stat ==202) {
                // Reload details window
                if (scope.base_window != undefined){
                    scope.base_window.dismiss('cancel');
                }
                scope.base_reload[0](scope.base_reload[1],scope.base_reload[2]);
                // If the request was accepted go back to the list
            } else {
                // Error happened, show an alert
                console.log("ERROR "+stat+": "+answer)
                console.log(answer);
                alert("ERROR "+stat+": "+answer)
            }
        })
        .error(function(data, status, headers, config) {
            if (cnf_debug){
                alert(data);
            }else{
                alert(cnf_debug_txt)
            }
        });
            
        var functions = function(scope) {};
        var callback = function(scope) {
            scope.det_window.dismiss('cancel');
            scope.det_reload[0](scope.det_reload[1]);
        };
    }
}

function openmodal($scope, $timeout, $uibModal, size, functions, callback) {
    var ngmodel=null;
    // Define the modal window
    $scope.build_modal = function (inline) {
        if (inline) {
            $scope.inurl=null;
            $scope.inhtml=inline;
        } else {
            $scope.inurl=$scope.ws;
            $scope.inhtml=null;
        }
        
        var modalInstance = $uibModal.open({
            template: $scope.inhtml,
            templateUrl: $scope.inurl,
            controller:  ['$scope', '$rootScope', '$http', '$window', '$uibModal', '$uibModalInstance', '$state', '$stateParams', '$templateCache', 'Register', 'ws', function ($scope, $rootScope, $http, $window, $uibModal, $uibModalInstance, $state, $stateParams, $templateCache, Register, ws) {
                // Save URL
                $scope.url=ws;
                $templateCache.remove(ws);
                
                // Set submit function
                $scope.submit = function (form, next) {
                    // Submit the form
                    formsubmit($scope, $rootScope, $http, $window, $state, $templateCache, $uibModalInstance, null, ws, form, 'here', 'addmodal');
                };
                
                $scope.msg = function(msg){
                    alert(msg);
                }
                
                $scope.delete = function(msg,url) {
                    if (confirm(msg)) {
                        // Build url
                        if (url==undefined) {
                            url = ws+"/../delete";
                        }
                        // Clear cache
                        $templateCache.remove(url);
                        // User confirmed
                        $http.post( url, {}, {} )
                        .success(function(answer, stat) {
                            // Check the answer
                            if (stat==202) {
                                // Everything OK, close the window
                                $uibModalInstance.close(answer);
                            } else {
                                // Error happened, show an alert
                                console.log("ERROR "+stat+": "+answer)
                                alert("ERROR "+stat+": "+answer)
                            }
                        })
                        .error(function(data, status, headers, config) {
                            if (cnf_debug){
                                alert(data);
                            }else{
                                alert(cnf_debug_txt)
                            }
                        });
                     }
                };
                
                // Set cancel function
                $scope.cancel = function () { $uibModalInstance.dismiss('cancel'); };
                
                // Enable dynamic select 
                $scope.http = $http;
                dynamic_fields($scope);
                angularmaterialchip($scope);
                if (typeof(codenerix_extensions)!="undefined") {codenerix_extensions($scope, $timeout);}

                // Add linked element
                $scope.linked=function (ngmodel, appname, modelname, formobj, formname, id, wsbaseurl) {
                    inlinked($scope, $rootScope, $http, $window, $uibModal, $state, $stateParams, $templateCache, Register, ws, null, ngmodel, appname, modelname, formobj, formname, id, wsbaseurl, $timeout);
                }

                // Functions
                if (functions!=undefined) {
                    functions($scope);
                }
            }],
            size: size,
            resolve: {
                ws:         function () { return $scope.ws;         },
            },
        });
        
        modalInstance.build_modal=$scope.build_modal;
        
        modalInstance.result.then(function (answer) {
            if (answer) {
                
                // Execute call back is requested
                if (callback!=undefined) {
                    callback($scope);
                }
                
                // Select the new created item
                if (ngmodel) {
                    // Select the new option
                    formobj[ngmodel].$setViewValue(answer['__pk__']);
                    // Change dirty/pristine for the input
                    formobj[ngmodel].$pristine = false;
                    formobj[ngmodel].$dirty = true;
                    // Change dirty/pristine for the form
                    formobj.$pristine = false;
                    formobj.$dirty = true;
                }
                // Check if reload is declared, and call it if exists
                if ($scope.reload!=undefined) {
                    $scope.reload();
                }
            }
        });
        return modalInstance;
    }
    return $scope.build_modal();
};


function modal_manager($scope, $timeout, $uibModal, $templateCache, $http, scope) {
    // Add new alternative flight
    scope.add = function (url) {
        // Base window
        $scope.ws=url+"/add";
        
        // Base Window functions
        var functions = function(scope) {};
        var callback = function(scope) {
            // Close our window
            if (scope.base_window) {
                scope.base_window.dismiss('cancel');
            }
            
            // If base_reload specified
            if (scope.base_reload){
                // Arguments are dinamically added
                scope.base_reload[0].apply(this,scope.base_reload.slice(1));
            }
        };
        
        // Start modal window
        openmodal($scope, $timeout, $uibModal, 'lg', functions, callback);
    };
    
    scope.removefile = function(id, msg, id_parent) {
        if (confirm(msg)){
            if (typeof(id_parent)=="undefined"){
                var url = $scope.wsbase+"/../"+id+"/delete";
                 $scope.ws = $scope.wsbase;
            }else{
                var url = $scope.wsbase+"/"+id+"/delete";
                $scope.ws= $scope.wsbase+id_parent;
            }
            
            $http.post( url, {}, {} )
            .success(function(answer, stat) {
                // Check the answer
                if (stat==200 || stat==202) {
                    // Reload details window
                    if ($scope.base_window != undefined){
                        $scope.base_window.dismiss('cancel');
                    }
                    $scope.base_reload[0]($scope.base_reload[1],$scope.base_reload[2]);
                    // If the request was accepted go back to the list
                } else {
                    // Error happened, show an alert
                    console.log("ERROR "+stat+": "+answer)
                    alert("ERROR "+stat+": "+answer)
                }
            })
            .error(function(data, status, headers, config) {
                if (cnf_debug){
                    alert(data);
                }else{
                    alert(cnf_debug_txt)
                }
            });

            // Base Window functions
            var functions = function(scope) {};
            var callback = function(scope) {};
            // Start modal window
            openmodal($scope, $timeout, $uibModal, 'lg', functions);//, callback);

        }
    };

    // DEPRECATED: 2017-02-14
    scope.change_alternative = function(id, msg){
        if (confirm(msg)){
            var url = $scope.ws+"/"+id+"/changealternative";
            
            $http.post( url, {}, {} )
            .success(function(answer, stat) {
                // Check the answer
                if (stat==200 || stat==202) {
                    // Reload details window
                    if ($scope.base_window != undefined){
                        $scope.base_window.dismiss('cancel');
                    }
                    $scope.base_reload[0]($scope.base_reload[1],$scope.base_reload[2]);
                    // If the request was accepted go back to the list
                } else {
                    // Error happened, show an alert
                    console.log("ERROR "+stat+": "+answer)
                    alert("ERROR "+stat+": "+answer)
                }
            })
            .error(function(data, status, headers, config) {
                if (cnf_debug){
                    alert(data);
                }else{
                    alert(cnf_debug_txt)
                }
            });

            // Base Window functions
            var functions = function(scope) {};
            var callback = function(scope) {};
            // Start modal window
            openmodal($scope, $timeout, $uibModal, 'lg', functions);//, callback);

        }
    }
    
    // Get details
    scope.details = function(id) {
        // Base window
        $scope.ws=$scope.wsbase+id;
        $scope.initialws = $scope.ws;
        // Base Window functions
        var functions = function(scope) {
            // Get details for existing alternative flight
            scope.edit = function(ar) {
                // Base window
                $scope.ws=$scope.initialws+"/edit";
                
                // Base Window functions
                var functions = function(scope) {
                };
                var callback = function(scope) {
                    // Reload list window
                    if ($scope.base_window != undefined){
                        /*
                        following line is going to be executed in the case this 
                        manager is created in a modal window 
                        */
                        scope.base_window.dismiss('cancel');
                    }
                    scope.base_reload[0]($scope.base_reload[1],$scope.base_reload[2]);
                    // Reload details window
                    scope.det_window.dismiss('cancel');
                    scope.det_reload[0](scope.det_reload[1]);
                };
                
                // Start modal window
                openmodal($scope, $timeout, $uibModal, 'lg', functions, callback);
            };
            scope.gotoback = function() {
                $scope.det_window.dismiss('cancel');
            };
            
            $scope.msg = function(msg){
                alert(msg);
            }
            
            scope.delete = function(msg) {
                if (confirm(msg)) {
                    // Clear cache
                    $templateCache.remove($scope.ws);
                    // User confirmed
                    var url = $scope.ws+"/delete";
                    $http.post( url, {}, {} )
                    .success(function(answer, stat) {
                        // Check the answer
                        if (stat==202) {
                            // Reload details window
                            if ($scope.base_window != undefined){
                                /*
                                following line is going to be executed in the case this 
                                manager is created in a modal window 
                                */
                                $scope.base_window.dismiss('cancel');
                            }
                            $scope.base_reload[0]($scope.base_reload[1],$scope.base_reload[2]);
                            // If the request was accepted go back to the list
                            $scope.det_window.dismiss('cancel');
                        } else {
                            // Error happened, show an alert
                            console.log("ERROR "+stat+": "+answer)
                            alert("ERROR "+stat+": "+answer)
                        }
                    })
                    .error(function(data, status, headers, config) {
                        if (cnf_debug){
                            alert(data);
                        }else{
                            alert(cnf_debug_txt)
                        }
                    });;
                 }
            };
        };
        
        // Prepare for refresh
        $scope.det_reload=[scope.details,id];
        $scope.det_window=openmodal($scope, $timeout, $uibModal, 'lg', functions);
    };

    // DEPRECATED: 2017-02-14
    // Get details OCR
    scope.details_ocr = function(id) {
        // Base window
        $scope.ws=$scope.wsbase+id+"/ocr";
        $scope.initialws = $scope.ws;
        // Base Window functions
        var functions = function(scope) {
            scope.gotoback = function() {
                $scope.det_window.dismiss('cancel');
            };
        };
        
        // Prepare for refresh
        $scope.det_reload=[scope.details,id];
        $scope.det_window=openmodal($scope, $timeout, $uibModal, 'lg', functions);
    };

    // Get details 
    scope.list_modal_detail = function(id, $event) {
        // Base window
        $scope.ws=$scope.wsbase+"modal";
        $scope.initialbase = $scope.wsbase;
        $scope.initialws = $scope.ws;

        var functions = function(scope) {
        };
        // Prepare for refresh
        $scope.det_reload=[scope.details,id];
        $scope.det_window=openmodal($scope, $timeout, $uibModal, 'lg', functions);
        //$event.stopPropagation();
    };
    // Get details customers
    scope.details_view = function(id, $event) {
        // Base window
        $scope.ws=$scope.wsbase+id+"/view";
        $scope.initialbase = $scope.wsbase+id;
        $scope.initialws = $scope.ws;
        // Base Window functions
        var functions = function(scope) {
            scope.gotoback = function() {
                $scope.det_window.dismiss('cancel');
            };

            scope.edit = function(ar) {
                // Base window
                $scope.ws=$scope.initialbase+"/edit";
                
                // Base Window functions
                var functions = function(scope) {
                };
                var callback = function(scope) {
                    // Reload list window
                    if ($scope.base_window != undefined){
                        /*
                        following line is going to be executed in the case this 
                        manager is created in a modal window 
                        */
                        scope.base_window.dismiss('cancel');
                    }
                    scope.base_reload[0]($scope.base_reload[1],$scope.base_reload[2]);
                    // Reload details window
                    scope.det_window.dismiss('cancel');
                    scope.det_reload[0](scope.det_reload[1]);
                };
                
                // Start modal window
                openmodal($scope, $timeout, $uibModal, 'lg', functions, callback);
            };
        };
        
        // Prepare for refresh
        $scope.det_reload=[scope.details,id];
        $scope.det_window=openmodal($scope, $timeout, $uibModal, 'lg', functions);
    };
};

// Function to help on refresh process
function refresh($scope, $timeout, Register, callback, internal) {
    // console.log("Refreshing "+$scope.elementid);
    if (($scope.data!=undefined) && ($scope.data.filter!=undefined) && ($scope.data.table!=undefined)) {
        // Update search
        $scope.query.search = $scope.data.filter.search;
        $scope.query.search_filter_button = $scope.data.meta.search_filter_button;
        // Update filters
        $scope.query.filters={};
        angular.forEach($scope.data.filter.subfilters, function(token){
            var value;
            if (token.kind=='select') {
                value=parseInt(token.choosen,10);
            } else if (token.kind=='multiselect') {
                value=token.choosen;
            } else if (token.kind=='multidynamicselect'){
                var id = null;
                angular.forEach(token.choosen, function(val, key){
                    if (!isNaN(val)){
                        id = val;
                    }
                });
                value=$scope.multidynamicseleted;
            } else if (token.kind=='daterange') {
                if (token.value && (token.value.startDate || token.value.endDate)) {
                    value=token.value
                } else {
                    value=null;
                }
            } else {
                value=token.value;
            }
            $scope.query.filters[token.key]=value;
        });
        if ($scope.data.meta.search_filter_button) {
            angular.forEach($scope.data.filter.subfiltersC, function(token){
                var value;
                if (token.kind=='select') {
                    value=parseInt(token.choosen,10);
                } else if (token.kind=='daterange') {
                    if (token.value && (token.value.startDate || token.value.endDate)) {
                        value=token.value
                    } else {
                        value=null;
                    }
                } else {
                    value=token.value;
                }
                $scope.query.filters[token.key]=value;
            });
        }
        
        // Update ordering
        $scope.query.ordering=$scope.data.table.head.ordering;
    }
    // Update elementid
    $scope.query.elementid = $scope.elementid;
    // Refresh now
    var wrapper_callback = function () {
        if (
                   (typeof($scope.tempdata.meta)!='undefined')
                && (typeof($scope.tempdata.meta.printer)!='undefined')
                && ($scope.tempdata.meta.printer!=null)
                ) {
            if ($scope.tempdata.table.printer.message != ''){
                alert($scope.tempdata.table.printer.message);
            }else{
                // Decode base 64
                var sliceSize = 512;
                var byteCharacters = atob($scope.tempdata.table.printer.file);
                var byteArrays = [];

                for (var offset = 0; offset < byteCharacters.length; offset += sliceSize) {
                    var slice = byteCharacters.slice(offset, offset + sliceSize);
                    var byteNumbers = new Array(slice.length);
                    for (var i = 0; i < slice.length; i++) {
                        byteNumbers[i] = slice.charCodeAt(i);
                    }
                    var byteArray = new Uint8Array(byteNumbers);
                    byteArrays.push(byteArray);
                }

                var blob = new Blob(byteArrays, {type: $scope.tempdata.meta.content_type});
                // FIN: Decode base 64
                var downloadLink = angular.element('<a></a>');
                downloadLink.attr('href',window.URL.createObjectURL(blob));
                downloadLink.attr('download', $scope.tempdata.table.printer.filename);
                downloadLink[0].click();
            }
            $scope.query.printer = null;
        }else{
            $scope.data = $scope.tempdata;
            // Callback passed as an argument
            if (callback!=undefined) {
                callback();
            }
            
            // Callback preinstalled in the scope
            if ((internal!==true) && ($scope.refresh_callback!=undefined)) {
                $scope.refresh_callback();
            }
        }
    };
    // Call the service for the data
    $scope.tempdata = Register.query({'json':$scope.query}, wrapper_callback);
}

function formsubmit($scope, $rootScope, $http, $window, $state, $templateCache, $uibModalInstance, listid, url, form, next, kind) {
    // Build in data
    var in_data = { };
    var form_name = form.$name;

    angular.forEach($scope.field_list, function(field){
        // normal input html
        if ($scope[field] != undefined){
            in_data[field]=$scope[field];
        // for multiselect (angular material chip)
        }else if ($scope.amc_select[field] != undefined){
            var datas_temp=[];
            angular.forEach($scope.amc_select[field], function (el){
                datas_temp.push(el.id);
            });
            in_data[field] = datas_temp;
        }
    });

    /*  
        2016-07-15
        Se quita porque los angular material chip no son elementos html por lo que no estan en el formulario
        2016-10-17
        Se vuelve a descomentar para ser compatible con las directivas dinamicas (iberosime) y con los multiselect dinamicos
    */
    angular.forEach( form , function ( formElement , fieldName ) {
        // If the fieldname starts with a '$' sign, it means it's an Angular property or function. Skip those items.
        if ( fieldName[0] === '$' ) {
            return;
        } else {
            if (fieldName != form_name) {
                if (typeof(formElement.$viewValue) == "object"){
                    var value = [];
                    angular.forEach(formElement.$viewValue, function(val, key){
                        if (typeof(val.id) !== 'undefined'){
                            value.push(val.id);
                        }
                    });
                    if (value.length == 0)
                        value = formElement.$viewValue;
                    in_data[fieldName]=value;
                }else{
                    in_data[fieldName]=formElement.$viewValue;
                }
            }
        }
    });

    // Clear cache
    $templateCache.remove(url);
    // POST
    $http.post( url, in_data, { headers: {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'} } )
    .success(function(answer, stat) {
        // If the request was accepted
        if (stat==202) {
            // Go back to the list
            if (next=='here') {
                if (kind=='add') {
                    // Jump to the edit form
                    $state.go('formedit'+listid,{'pk':answer.pk});
                } else if ((kind=='addmodal') || (kind=='editmodal')) {
                    // Set the primary key and let it finish execution
                    $uibModalInstance.close(answer);
                } else {
                    // Reset all elements status
                    angular.forEach( form , function ( formElement , fieldName ) {
                        // If the fieldname starts with a '$' sign, it means it's an Angular property or function. Skip those items.
                        if ( fieldName[0] === '$' ) {
                            return;
                        } else {
                            formElement.$pristine = true;
                            formElement.$dirty = false;
                        }
                    });
                    // Reset form status
                    form.$pristine = true;
                    form.$dirty = false;
                }
                // Reload page
                $state.reload($state.current);
            } else if (next=='new') {
                $state.go('formadd'+listid);
                $state.transitionTo('formadd'+listid, {}, { reload: true, inherit: true, notify: true });
            } else if (next=='details') {
                $state.go('details'+listid,{'pk':answer.__pk__});
            } else {
                $state.go('list'+listid);
            }
        } else if (stat==200) {
            if (answer['error']) {
                $scope.error=answer['error'];
            } else {
                if (next=='here') {
                    $uibModalInstance.close();
                    $uibModalInstance.build_modal(answer);
                } else {
                    var templateUrl=$state.current.templateUrl;
                    $state.current.template=answer;
                    // $state.transitionTo($state.current, $state.$current.params, { reload: true, inherit: true, notify: true });
                    $state.transitionTo($state.current, {}, { reload: true, inherit: true, notify: true });
                    $state.current.templateUrl=templateUrl;
                }
            }
        } else {
            console.log("ERROR "+stat+": "+answer)
            $window.alert("Internal error detected (Error was: "+answer+")")
        }
    });
}


// Linked elements behavior when they are called by a link() call from a click on a plus symbol
function inlinked($scope, $rootScope, $http, $window, $uibModal, $state, $stateParams, $templateCache, Register, ws, listid, ngmodel, appname, modelname, formobj, formname, id, wsbaseurl, $timeout) {
    // Get incoming attributes
    $scope.ngmodel=ngmodel;
    $scope.appname=appname;
    $scope.modelname=modelname;
    $scope.formobj=formobj;
    $scope.formname=formname;
    
    // Build ws callback
    if (id) {
        $scope.ws="/"+appname+"/"+modelname+"/"+id+"/editmodal";
    } else {
        $scope.ws="/"+appname+"/"+modelname+"/addmodal";
    }
    $templateCache.remove($scope.ws);
    
    // Define the modal window
    $scope.build_modal = function (inline) {
        if (inline) {
            $scope.inurl=null;
            $scope.inhtml=inline;
        } else {
            $scope.inurl=$scope.ws;
            $scope.inhtml=null;
        }
        var modalInstance = $uibModal.open({
            template:  $scope.inhtml,
            templateUrl: $scope.inurl,
            controller:  ['$scope', '$rootScope', '$http', '$window', '$uibModal', '$uibModalInstance', '$state', '$stateParams', '$templateCache', 'Register', 'ws', function ($scope, $rootScope, $http, $window, $uibModal, $uibModalInstance, $state, $stateParams, $templateCache, Register, ws) {
                // Autostart multiadd
                if (id) {
                    var action="editmodal"
                    multiedit($scope, $rootScope, $timeout, $http, $window, $uibModal, $state, $stateParams, $templateCache, Register, 0, ws);
                } else {
                    var action="addmodal"
                    multiadd($scope, $rootScope, $timeout, $http, $window, $uibModal, $state, $stateParams, $templateCache, Register, 0, ws);
                }
                
                // Set submit function
                $scope.submit = function (form, next) {
                    // Submit the form control
                    formsubmit($scope, $rootScope, $http, $window, $state, $templateCache, $uibModalInstance, listid, ws, form, 'here', action);
                };
                // Set cancel function
                $scope.cancel = function () { $uibModalInstance.dismiss('cancel'); };
            }],
            size: "lg",
            resolve: {
                Register:   function () { return $scope.Register;   },
                ws:         function () { return $scope.ws;         },
            },
        });
        modalInstance.build_modal=$scope.build_modal;
        
        modalInstance.result.then(function (answer) {
            // Select the new created item
            if (answer) {
                var options = $scope.options[ngmodel];
                if (answer['__pk__']) {
                    // Select the new created item
                    if (ngmodel) {
                        var set_view_value = true;
                        if (options == undefined){
                            // multiselect
                            options = $scope.amc_items[ngmodel]
                            set_view_value = false;
                        }
                        var inlist = false;
                        angular.forEach(options, function(key, value){
                            // Update element
                            if (options[value]["id"] == answer["__pk__"]){
                                options[value]["label"] = answer["__str__"];
                                inlist = true;
                            }
                        });
                        if (!inlist){
                            // Attach the new element
                            options.push({'id': answer["__pk__"], 'label': answer["__str__"]});
                        }
                        /*
                         * WORKING ON IT! 
                        console.log(answer['__pk__']);
                        console.log(options);
                        console.log(formobj[ngmodel]);
                        // ------------------------------------------******************
                        // Select the new option
                        formobj[ngmodel].$setViewValue(null);
                        formobj[ngmodel].$setViewValue(answer['__pk__']);
                        // Change dirty/pristine for the input
                        formobj[ngmodel].$pristine = false;
                        formobj[ngmodel].$dirty = true;
                        */
                        
                        if (set_view_value){
                            // Select the new option
                            formobj[ngmodel].$setViewValue(answer['__pk__']);
                            // Change dirty/pristine for the input
                            formobj[ngmodel].$pristine = false;
                            formobj[ngmodel].$dirty = true;
                        }
                        // Change dirty/pristine for the form
                        formobj.$pristine = false;
                        formobj.$dirty = true;
                    }
                    
                    //refresh info of fields associate by pk
                    if (wsbaseurl!=undefined){
                        var url = wsbaseurl + answer['__pk__'];
                        $http.get(url,{},{})
                        .success(function(answer, stat) {
                            angular.forEach(answer, function(val, key){
                                $scope[key] = val;
                                //formobj[key] = val;
                            });
                        });
                    }
                }
            }
        });
    };
    $scope.build_modal();
};

function dynamic_fields(scope) {
    // Memory for dynamic fields
    scope.dynamicFieldsMemory = {};

    scope.multidynamicseleted = [];

    scope.removeSelected = function(list){
        var temp=[];
        angular.forEach(scope.multidynamicseleted, function(val, key){
            if (list.indexOf(val.id)>=0){
                temp.push(val);
            }
        });
        scope.multidynamicseleted = temp;
    };

    scope.saveSelected = function(list, value){
        var id = null;
        angular.forEach(value, function(val, key){
            if (!isNaN(val)){
                id = val;
            }
        });
        var remove=null;
        if (id !== null){
            var i=1;
            angular.forEach(scope.multidynamicseleted, function(val, key){
                if (val.id == id){
                    var h = scope.multidynamicseleted.splice(i, 1);
                    remove = true;
                }
                i = i + 1;
            });
            if (remove != true){
                angular.forEach(list, function(val, key){
                    if (val.id == id){
                        scope.multidynamicseleted.push({'label': val.label, 'id': val.id});
                    }
                });
            }
        }
        if (id == null || scope.multidynamicseleted.length==0){
            scope.multidynamicseleted = [];
        }
        return false;
    };
    // Control how the selected ui-select field works with pristine/dirty states
    scope.selectedOptionSelect = function(input, value, ngchange) {
        if (!input.$dirty) {
            input.$dirty=input.$viewValue!=value;
        }
        if (input.$pristine) {
            input.$pristine=input.$viewValue==value;
        }
        input.$setViewValue(input.$modelValue);
        // Process the selected item
        if (scope.valuegetforeingkey[input.$name] != undefined && 'rows' in scope.valuegetforeingkey[input.$name]){
            
            // Function to process new value set
            var set_new = function(scope, key, answer, value) {
                // Set new value
                if (scope[scope.form_name] != undefined && scope[scope.form_name][key] != undefined){
                    var element = scope[scope.form_name][key];
                    if (typeof(value) == "object"){
                        var info = [];
                        info['id']= value[0];
                        info['label']= value[1];
                        scope.options[key].push(info);
                        element.$setViewValue(value[0]);
                    }else{
                        element.$setViewValue(value);
                    }
                    element.$render();
                    if (ngchange!==undefined) {
                        // Evaluate the expresion
                        scope.$eval(ngchange);
                    }
                }

                if ('_clear_' in answer){
                    angular.forEach(answer['_clear_'], (function(v, key){
                        scope[scope.form_name][v].$setViewValue('');
                        scope[scope.form_name][v].$render();
                    }));
                }
                if ('_readonly_' in answer){
                    scope.dynamicFieldsMemory.autocomplete.readonly = answer['_readonly_'];
                    angular.forEach(scope.dynamicFieldsMemory.autocomplete.readonly, (function (key){
                        scope['readonly_'+key] = true;
                    }));
                }
            }
            
            // For each field
            angular.forEach(scope.valuegetforeingkey[input.$name].rows, (function (value2, key){
            
                if (value2['id'] == input.$modelValue){
                    scope.resetAutoComplete();
                    angular.forEach(value2, (function (value3, key){
                        var async = true;
                        if (key && key!="label" && key!="id" && key[0]!='$') {
                            var keysp = key.split(":")
                            if (keysp.length>=2) {
                                key = keysp[0];
                                var kind = keysp[1];
                                if (kind=='__JSON_DATA__') {
                                    try {
                                        value3={'__JSON_DATA__':angular.fromJson(value3)};
                                    } catch(e) {
                                        console.log("ERROR: "+e);
                                    }
                                } else if (kind=='__SCOPE_CALL__') {
                                    value3 = scope.$eval(value3);
                                } else if (kind=='__SERVICE_CALL__') {
                                    async = false;
                                    jQuery.ajax({
                                         url: value3,
                                         success: function (answer) {
                                            value3 = answer['value'];
                                            // Set new value
                                            set_new(scope, key, value2, value3);
                                         },
                                         async: false
                                    });
                                }
                            }
                            // Set new value
                            if (async) {
                                set_new(scope, key, value2, value3);
                            }
                        }
                    }));
                    return;
                }
            }));
        }
    };
    
    scope.multi_dynamic_select_dict = function(arg, formname){
        return multi_dynamic_select_dict(arg, formname);
    };

    // Manage dynamic foreignkeys selects working with ui-select
    scope.valuegetforeingkey = {};
    scope.getForeignKeys = function(http,baseurl,options,filter,modelname,modelvalue,search,deepness) {

        if ((search.length>=deepness) || (search=='*')) {
            var filter2 = {}
            angular.forEach(filter, function(value, key){
                if (typeof(value)=="object"){
                    filter2[key] = value.$viewValue;
                }else{
                    filter2[key] = value;
                }
            });
            // Prepare URL
            var url = baseurl+search+'?filter='+angular.toJson(filter2)
            
            // Send the request
            http.get(url,{},{})
            .success(function(answer, stat) {
                scope.valuegetforeingkey[modelname] = answer;
                if ('clear' in answer){
                    answer= answer['rows'];
                }
                options[modelname] = answer;
            });
        } else if (modelvalue==undefined) {
            options[modelname]=[{
                "id": null,
                "label": "---------"
                }];
        }
    };
    
    // Manage dynamic input working with md-autocomplete
    scope.dynamicFieldsMemory.autocomplete = {};
    scope.dynamicFieldsMemory.autocompletetmp = {};
    scope.dynamicFieldsMemory.autocomplete.clear = [];
    scope.dynamicFieldsMemory.autocompletetmp.clear = [];
    scope.dynamicFieldsMemory.autocomplete.readonly = [];
    scope.dynamicFieldsMemory.autocompletetmp.readonly = [];
    scope.dynamicFieldsMemory.autocomplete.clear_tmp = [];
    scope.dynamicFieldsMemory.autocomplete.readonly_tmp = [];
    scope.resetAutoComplete = function() {
        // Clear fields
        if (scope.dynamicFieldsMemory.autocomplete.clear) {
            angular.forEach(scope.dynamicFieldsMemory.autocomplete.clear, (function (key){
                // Set new value
                scope[key]="";
            }));
            scope.dynamicFieldsMemory.autocomplete.clear = [];
        }
        // Readonly fields
        if (scope.dynamicFieldsMemory.autocomplete.readonly) {
            angular.forEach(scope.dynamicFieldsMemory.autocomplete.readonly, (function (key){
                scope['readonly_'+key]=false;
            }));
            scope.dynamicFieldsMemory.autocomplete.readonly = [];
        }
    };
    
    scope.getAutoComplete = function(http,baseurl,filter,search,deepness) {
        if ((search.length>=deepness) || (search=='*')) {
            var filter2 = {}
            angular.forEach(filter, function(value, key){
                if (typeof(value)=="object"){
                    filter2[key] = value.$viewValue;
                }else{
                    filter2[key] = value;
                }
            });
            
            // Prepare URL
            var url = baseurl+search+'?filter='+angular.toJson(filter2)
            
            // Send the request
            return http.get(url,{},{})
                .then(function(answer){
                    // Remember what to clear and what to set readonly
                    scope.dynamicFieldsMemory.autocomplete.clear_tmp = answer.data.clear;
                    scope.dynamicFieldsMemory.autocomplete.readonly_tmp = answer.data.readonly;
                    // Return answer
                    return answer.data.rows
                });
        }
    };
    
    // Set dynamic values that came from an autofield
    // Note: Only refresh input NOT OTHER TAG HTML (We believe that angular is not aware about the new DOM and that Django-Angular is only compiling the inputs so Angular is aware only about them)
    scope.autoFillFields = function ($item, $model, $label, $event) {
        // Copy structures
        if (scope.dynamicFieldsMemory.autocomplete.clear_tmp) {
            scope.dynamicFieldsMemory.autocomplete.clear = scope.dynamicFieldsMemory.autocomplete.clear_tmp;
            scope.dynamicFieldsMemory.autocomplete.clear_tmp = [];
        }
        if (scope.dynamicFieldsMemory.autocomplete.readonly_tmp) {
            scope.dynamicFieldsMemory.autocomplete.readonly = scope.dynamicFieldsMemory.autocomplete.readonly_tmp;
            scope.dynamicFieldsMemory.autocomplete.readonly_tmp = [];
        }
        // Set readonly
        angular.forEach(scope.dynamicFieldsMemory.autocomplete.readonly, (function (key){ scope['readonly_'+key]=true; }));
        // Process the selected item
        angular.forEach($item, (function (value, key){
            if (key!="label") {
                // Set new value
                scope[key]=value;
            }
        }));
    };

}

// Codenerix libraries
var codenerix_libraries = [
    'ui.bootstrap',
    'ui.router',
    'ui.select',
    'ui.bootstrap.datetimepicker',
    //'chieffancypants.loadingBar',
    'colorpicker.module',
    'colorContrast',
    'ngAnimate',
    'ngCookies',
    'ngSanitize',
    'ngTouch',
    'ngMaterial',
    'ng.django.forms',
    'angular-loading-bar',
    'nsPopover',
    'codenerixControllers',
    'codenerixServices',
    'codenerixFilters',
    'codenerixNotify',
    'naif.base64',
    'fileValidation',
    'daterangepicker',
    'textAngular',
    'vcRecaptcha',
    'checklist-model',
    'ngQuill',
];

/*
function answer_rendered(element,$q) {
    var deferred = $q.defer(),
    intervalKey,
    counter = 0, 
    maxIterations = 50;
    
    intervalKey = setInterval(function () {
        var jel = element[0].children.length;               // Javascript first usable row (second on the list)
        if (jel>2) {
            deferred.resolve(element);
            clearInterval(intervalKey);
        } else if (counter >= maxIterations) {
            deferred.reject("no element found");
            clearInterval(intervalKey);
        }
        counter++;
    }, 100);
    
    return deferred.promise;
}

answer_rendered(element,$q).then(function (element) {
        scope.refresh_vtable();
}, function (message) {
        console.log(message);
});
*/

var codenerix_directive_vtable = ['codenerixVtable', ['$window','$timeout','$q','Register', function($window, $timeout, $q, Register) {
    return {
        restrict : 'A',
        transclude: true,
        replace: false,
        template : "<tr><td ng-repeat='column in data.table.head.columns' ng-style=\"{height: codenerix_vtable.top+'px'}\" style='margin:0px;padding:0px;border:1px solid #fff;' id='codenerix_vtable_top'></td></tr>"+
                   "<tr ng-repeat=\"row in data.table.body\" id='row{{row.pk}}' ng-click=\"detail(row.pk)\" ui-view>"+
                   "<tr><td ng-repeat='column in data.table.head.columns' ng-style=\"{height: codenerix_vtable.bottom+'px'}\" style='margin:0px;padding:0px;border:1px solid #fff;'></td></tr>",
        link: function(scope, element, attrs) {
            if (scope.data!=undefined && scope.data.meta!=undefined && scope.data.meta.vtable!=undefined && scope.data.meta.vtable) {
                // console.log("Codenerix VTable: Load");
                
                // Initialize scope
                // scope.query.page=1;
                // scope.query.rowsperpage=1;
                if (scope.$parent.$parent.listid!=undefined) {
                    scope = scope.$parent.$parent;
                } else if (scope.$parent.listid!=undefined) {
                    scope = scope.$parent;
                } else {
                    console.error("Couldn't align 'scope' variable with its $parent's");
                }
                scope.codenerix_vtable={};
                scope.codenerix_vtable.top=0;
                scope.codenerix_vtable.bottom=0;
                scope.codenerix_vtable.last_scroll=(new Date).getTime();
                
                // Install refresh auto callback
                scope.refresh_callback = function () {
                    if (scope.data!=undefined && scope.data.meta!=undefined && scope.data.meta.vtable!=undefined && scope.data.meta.vtable) {
                        // console.log("Codenerix VTable: Refresh detected");
                        // Ensure refresh_vtable after render
                        $timeout(scope.codenerix_vtable.refresh, 0);
                    //} else {
                    //    console.log("Codenerix VTable: Refresh detected but no VTABLE");
                    }
                };
                
                // Remove all watchers on scroll event
                scope.$on('$destroy', function () {
                    angular.element($window).off('scroll');
                });
                // Install scroll watcher
                angular.element($window).on("scroll", function() {
                    if (scope.data!=undefined && scope.data.meta!=undefined && scope.data.meta.vtable!=undefined && scope.data.meta.vtable) {
                        // console.log("Codenerix VTable: Scroll detected");
                        // Ensure refresh_vtable after render
                        var new_last_scroll = (new Date).getTime();
                        scope.codenerix_vtable.last_scroll=new_last_scroll;
                        $timeout(scroll_refresh(scope, new_last_scroll), 300);
                        // Save changes in the scope
                        scope.$apply();
                    }
                });
                
                // Refresh VTable system
                scope.codenerix_vtable.refresh = function (cache, callback) {
                    // console.log("Codenerix VTable: Refresh VTable");
                    
                    // === FUTURE HELPERS === ================================================
                    // var row_position = jel.getBoundingClientRect().top; // Offset position to Screen Top
                    
                    // === GEOMETRY DECISIONS === ============================================
                    // Get geometry and details
                    var jel = element[0].children[1];               // Javascript first usable row (second on the list)
                    var row_height = jel.scrollHeight;              // Row height
                    var row_total = scope.data.meta.row_total;      // Total rows in the last answer
                    var window_height = $window.innerHeight;        // Window height
                    
                    // Multiplier for pagesize (1:default)
                    // - 1: many stops for caching, fast loading
                    // - 4: few stops for caching, long time loading
                    var page_size_multiplier = 1;
                    // Size of the window in number of rows
                    var rowsperpage = Math.ceil(window_height/row_height)*page_size_multiplier;
                    
                    if (row_total>0) {
                        
                        // Calculate geometry details
                        var cache = 4;                                  // Cache size is 4 (firstpage + 4 pages)
                        var scroll_height = row_total*row_height;       // Get scroll height
                        var scroll_position = $window.scrollY;          // Get scroll position
                        var proportion = scroll_position/scroll_height; // Get proportion
                        var row_to_show = proportion * row_total;       // Row that we should show
                        var page_to_show = Math.floor(row_to_show/rowsperpage)+ 1; // Page to show
                        var vpagefirst = page_to_show - 1;              // First page to bring
                        var vpagelast = vpagefirst + cache;             // Last page to bring (firstpage + cache pages)
                        if (vpagefirst<1) { vpagefirst=1; }             // Protect first page not to be out of range
                        var vpagetotal = vpagelast - vpagefirst;        // Total pages to bring
                        
                        // === DEBUG === =========================================================
                        // Prepare DEBUG message
                        // var msg ="Codenerix VTable: Debug"
                        // msg+="\n\tfirst: "+vpagefirst;
                        // msg+="\n\tbring: "+vpagetotal;
                        // msg+="\n\trows:  "+rowsperpage;
                        
                        // Show DEBUG message
                        // console.log(msg);
                        
                        // === MEMORY === ========================================================
                        if ((cache!==true)
                            || (vpagefirst!=scope.codenerix_vtable.vpagefirst)
                            || (vpagetotal!=scope.codenerix_vtable.pages_to_bring)
                            || (rowsperpage!=scope.codenerix_vtable.rowsperpage)) {
                            scope.codenerix_vtable.vpagefirst=vpagefirst;
                            scope.codenerix_vtable.pages_to_bring=vpagetotal;
                            scope.codenerix_vtable.rowsperpage=rowsperpage;
                            
                            // === QUERY === =========================================================
                            // Set new query filters
                            scope.query.page = vpagefirst;
                            scope.query.pages_to_bring=vpagetotal;
                            scope.query.rowsperpage = rowsperpage;
                            // Refresh table with internal state set to 'true' to avoid recursion
                            refresh(scope, $timeout, Register, function () {
                                // === REDRAW === ========================================================
                                // Set top and bottom depending on the result
                                scope.codenerix_vtable.top = rowsperpage*(vpagefirst-1)*row_height;
                                scope.codenerix_vtable.bottom = (row_total-(vpagelast*rowsperpage))*row_height;
                                // === CALLBACK === ======================================================
                                // Callback passed as an argument
                                if (callback!=undefined) {
                                    callback();
                                }
                            }, true);
                            // Save changes in the scope
                            scope.$apply();
                        }
                    }
                };
                
                // Force refresh the table with the availabe information
                $timeout(scope.codenerix_vtable.refresh, 0);
            }
        },
    };
}]];

var codenerix_directive_autofocus = ['codenerixAutofocus', ['$timeout', function($timeout) {
    return {
        restrict: 'AC',
        link: function(_scope, _element) {
            $timeout(function(){
                _element[0].focus();
            }, 0);
        }
    };
}]];


var codenerix_run=['$http','$rootScope','$cookies',
    function ($http,$rootScope,$cookies) {
        // Add automatic CSRFToken
        $http.defaults.headers.post['X-CSRFToken'] = $cookies.csrftoken;
        $http.defaults.headers.common['X-CSRFToken'] = $cookies.csrftoken;
        // Set internal XSRFToken
        $http.defaults.xsrfHeaderName = 'X-CSRFToken';
        $http.defaults.xsrfCookieName = 'csrftoken';
        // Redirect if login required
        $rootScope.$on('event:auth-loginRequired', function () { window.location = '/'; });
    }
];

var codenerix_config1=['cfpLoadingBarProvider', function(cfpLoadingBarProvider) {
    // cfpLoadingBarProvider.includeSpinner = false;
    cfpLoadingBarProvider.spinnerTemplate = '<div id="loading-bar-spinner"><div class="bubblingG"><span id="bubblingG_1"></span><span id="bubblingG_2"></span><span id="bubblingG_3"></span></div></div>';
    cfpLoadingBarProvider.latencyThreshold = 0;
}];

var codenerix_config2 = ['$httpProvider', function($httpProvider) {
    $httpProvider.defaults.headers.common['X-Requested-With'] = 'XMLHttpRequest';
}];

// Add a new library to codenerix_libraries if it doesn't exists yet
function codenerix_addlib(name) {
    if (typeof(name) === "string") {
        if (codenerix_libraries.indexOf(name)==-1) {
            codenerix_libraries.push(name);
        } else {
            console.info("Library '"+name+"' already in codenerix");
        }
    } else {
        console.error("codenerix_addlib() is expecting a string")
    }
}
// Add a new libraries to codenerix_libraries if it doesn't exists yet
function codenerix_addlibs(names) {
    if (Object.prototype.toString.call(names) === '[object Array]') {
        angular.forEach(names, function(name, key) {
            codenerix_addlib(name);
        });
    } else {
        console.error("codenerix_addlibs() is expecting an Array")
    }
}
// Remove a library from codenerix_libraries if it does exists
function codenerix_dellib(name) {
    if (typeof(name) === "string") {
        var index = codenerix_libraries.indexOf(name);
        if (index!=-1) {
            codenerix_libraries.remove(index);
        } else {
            console.info("Library '"+name+"' not found in codenerix");
        }
    } else {
        console.error("codenerix_dellib() is expecting a string")
    }
}
// Add a new libraries to codenerix_libraries if it doesn't exists yet
function codenerix_dellibs(names) {
    if (Object.prototype.toString.call(names) === '[object Array]') {
        angular.forEach(names, function(name, key) {
            codenerix_dellib(name);
        });
    } else {
        console.error("codenerix_dellibs() is expecting an Array")
    }
}

// Function to wrap refresh_vtable calls so scroll will not stress the system with massive events
function scroll_refresh(scope, new_last_scroll) {
    return function () {
        if (scope.codenerix_vtable.last_scroll==new_last_scroll) {
            scope.codenerix_vtable.refresh(true);
        };
    }
}

// Define get_static if no other method exists
if (typeof(get_static)=="undefined") {
    var get_static = function (path) {
        if (typeof(static_url)!="undefined") {
            var result =static_url+path;
        } else {
            var result = "/static/"+path;
        }
        return result;
    };
}

function codenerix_builder(libraries, routes) {
    /*
     * libraries:
     *      - It is a list of mosules to be added or removed from the loader of the controller.
     *      - The loader will set by default the modules to load that are set in the 'codenerix_libraries' variable
     *      - Use 'module' to add a module to the loader
     *      - Use '-module' to remove a module from the loader
     *      - Example: [ '-codenerixServices', 'newModule' ]
     *
     * routes: { dictionary of routes to add or remove from the routing system }
     *         { 'state': [ 'url', 'template path', 'controller' ], 
     *           'state': null }
     *          Description:
     *              state: state name
     *              url: Angular url
     *              template path: URI path to the template
     *              controller: name of the controller to use for this state
     *          Predefined states:
     *              - States: list0, list0.rows, formadd0, formedit0, details0
     *              - If you assign <null> to the state then the state is not added to the routing system. Ex: { 'list0':null }
     *              - If you set <null> to any element in the list URL/Template/Controller will not be added to the route in the router:
     *                  Ex: { 'list0': [ '/urlbase', null, 'newController'] }
     *              - If you set <undefined> to any element in the list URL/Template/Controller predefined value will be used.
     *                  Ex: { 'list0': [ '/urlbase', null, 'newController'] }
     *          Customized states:
     *              - You can add any custom state to the router dictionary
     *              - If you set <null> to any element in the list URL/Template/Controller will not be added to the route in the router:
     *                  Ex: { 'customState': [ '/custom_url', null, 'customController'] }
     *
     * Notes:
     *      - If libraries is not set (it is undefined), libraries will become an empty list [] by default
     *      - If router not set (different than undefined), the routing system will be initialized and the default URL will be '/'
     */
    
    // Check libraries
    if (libraries===undefined) {
        libraries=[];
    }
    // Prepare libraries
    angular.forEach(libraries, function(name, key) {
        if (name[0]=='-') {
            name=name.substring(1);
            codenerix_dellib(name);
        } else {
            codenerix_addlib(name);
        }
    });
    
    // Build the base module
    var module = angular.module('codenerixApp', codenerix_libraries)
    
    // Default configuration
    .config(codenerix_config1)
    .config(codenerix_config2)
    
    // Set Codenerix directives
    .directive(codenerix_directive_vtable[0], codenerix_directive_vtable[1])
    .directive(codenerix_directive_autofocus[0], codenerix_directive_autofocus[1])
    
    // Set routing system
    .run(codenerix_run);
    
    // Decide about routing
    if (routes!==null) {
        // Create the routing system
        module.config(['$stateProvider', '$urlRouterProvider',
            function($stateProvider, $urlRouterProvider) {
                $stateProvider
                $urlRouterProvider.otherwise('/');
            }
        ]);
        
        // Check if we should use default routes
        if (routes===undefined) {
            routes={}
        }
        // Build known
        var known=Array();
        known.push(['list0',            '/',        get_static('codenerix/partials/list.html'),                                   'ListCtrl']);
        if (typeof(static_partial_row)!='undefined') {
            known.push(['list0.rows',   null,       static_partial_row,                                          null]);
        }
        if (typeof(ws_entry_point)!='undefined') {
            known.push(['formadd0',     '/add',     function(params) { return '/'+ws_entry_point+'/add'; },                 'FormAddCtrl']);
            known.push(['formedit0',    '/:pk/edit',function(params) { return '/'+ws_entry_point+'/'+params.pk+'/edit'; },  'FormEditCtrl']);
            known.push(['details0',     '/:pk',     function(params) { return '/'+ws_entry_point+'/'+params.pk; },          'DetailsCtrl']);
            
            var tag='';
            var controller='';
            if (typeof(tabs_js)!='undefined') {
                angular.forEach(tabs_js, function(tab, i){
                    if (tab.auto) {
                        controller='SubListCtrl';
                    } else {
                        controller='SubListStaticCtrl';
                    }
                    known.push(['details0.sublist'+tab.internal_id+'', '/sublist'+tab.internal_id+'/:listid/', get_static('codenerix/partials/list.html'), controller]);
                    if (typeof(tab.static_partial_row)!="undefined"){
                        known.push(['details0.sublist'+tab.internal_id+'.rows', null, tab.static_partial_row, null]);
                    }
                });
            }
            known.push(['details0.sublist', '/sublist/0/', get_static('codenerix/partials/list.html'), 'SubListCtrl']);
        }
        
        // Process known routes
        angular.forEach(known, function(name, key) {
            // Get configuration
            var state=name[0];
            var url=name[1];
            var template=name[2];
            var ctrl=name[3];
            
            // Process each route
            if (state in routes) {
                if (routes[state]===null) {
                    // Remove actual state, we will not process it
                    state=null;
                } else {
                    // Get information
                    var url2        = routes[state][0];
                    var template2   = routes[state][1];
                    var ctrl2       = routes[state][2];
                    // Set configuration
                    if (url2!==undefined)        { url=url2; };
                    if (template2!==undefined)   { template=template2; };
                    if (ctrl2!==undefined)       { ctrl=ctrl2; };
                }
                // Remove the key from routes
                delete routes[state];
            }
            
            // Check if we have an state to process (the user maybe defined it as null, what means it wants to remove this state)
            if (state!==null) {
                // Build the state dictionary
                var state_dict={};
                if (url!==null) {        state_dict['url']=url;              }
                if (template!==null) {   state_dict['templateUrl']=template; }
                if (ctrl!==null) {       state_dict['controller']=ctrl;      }
                
                // Attach the new state
                module.config(['$stateProvider', '$urlRouterProvider',
                    function($stateProvider, $urlRouterProvider) {
                        $stateProvider.state(state, state_dict);
                    }
                ]);
            }
        });
        
        // Process new routes
        angular.forEach(routes, function(config, state) {
            if (config!==null) {
                // Get configuration
                var url = config[0];
                var template = config[1];
                var ctrl = config[2];
                
                // Build the state dictionary
                var state_dict={};
                if (url!==null) {        state_dict['url']=url;              }
                if (template!==null) {   state_dict['templateUrl']=template; }
                if (ctrl!==null) {       state_dict['controller']=ctrl;      }
                
                // Attach the new state
                module.config(['$stateProvider', '$urlRouterProvider',
                    function($stateProvider, $urlRouterProvider) {
                        $stateProvider.state(state, state_dict);
                    }
                ]);
            }
        });
    }
    
    // Add factory
    module.factory("ListMemory",function(){return {};});
    
    // Return the just built module
    return module;
}

function multilist($scope, $rootScope, $timeout, $location, $uibModal, $templateCache, $http, $state, Register, ListMemory, listid, ws, callback, sublist) {
    // Move to inside state to get double view resolved
    if ((callback==undefined) && (!sublist)) {
        $state.go('list'+listid+'.rows');
    }
    $scope.listid=listid;
    // Startup memory
    var l = ListMemory;
    if ((l.mem!=undefined) && (l.mem[listid])) {
        // We have already a memory from what happened here
        $scope.query=l.mem[listid];
    } else {
        // Enviroment
        $scope.ws=ws;
        $scope.wsbase=ws+"/";
        $scope.page=1;
        $scope.pages_to_bring=1;
        $scope.rowsperpage=1;
        $scope.filters=[];
        $scope.ordering=[];
        $scope.options={};
        $scope.year=null;
        $scope.month=null;
        $scope.day=null;
        $scope.hour=null;
        $scope.minute=null;
        $scope.second=null;
        $scope.context={};
        
        // Prepare query
        $scope.query = {
            "listid":listid,
            "elementid":null,
            "search":"",
            "page":1,
            "pages_to_bring":1,
            "rowsperpage":50,
            "filters":{},
            "ordering":[],
            "year":null,
            "month":null,
            "day":null,
            "hour":null,
            "minute":null,
            "second":null,
            "context":{},
            "printer": null,
        };
    }

    // Remember http
    $scope.http=$http;
    // Set dynamic foreign fields controller functions
    dynamic_fields($scope);
    angularmaterialchip($scope);
    if (typeof(codenerix_extensions)!="undefined") {codenerix_extensions($scope, $timeout);}
    
    // Memory
    if (l.mem==undefined) {
        l.mem={};
    }
    l.mem[listid]=$scope.query;

    if (sublist){
        $scope.refresh_callback = function(){
            $scope.$apply();
        }
    }
    
    // Edit/detail link
    $scope.set_elementid = function(value, name) {
        if ($rootScope.elementid==value) {
            $rootScope.elementid=null;
            $rootScope.elementname=null;
        } else {
            $rootScope.elementid=value;
            $rootScope.elementname=name;
        }
    };
    $scope.addnew = function () {
        if ($scope.data.meta.linkadd) {
            if (!sublist) {
                $state.go('formadd'+listid);
            } else {
                // Base window
                $scope.ws=ws+"/addmodal";
                
                // Base Window functions
                var functions = function(scope) {};
                var callback = function(scope) {
                    // Close our window
                    if (scope.base_window) {
                        scope.base_window.dismiss('cancel');
                    }
                    $state.go($state.current, {listid:scope.listid});
                    refresh(scope, $timeout, Register, undefined);
                };
                
                // Start modal window
                openmodal($scope, $timeout, $uibModal, 'lg', functions, callback);
            }
        }
    };
    $scope.detail = function (pk) {
        if ($scope.data.meta.linkedit) {
            if (!sublist) {
                if ($scope.data.meta.show_details) {
                    // Showing details
                    if ($scope.data.meta.show_modal) {
                        // Show in a modal window
                        modal_manager($scope, $timeout, $uibModal, $templateCache, $http, scope);
                        $scope.details(pk);
                    } else {
                        // Show like always
                        $state.go('details'+listid, {'pk':pk});
                    }
                } else {
                    // Edit normally
                    $state.go('formedit'+listid, {'pk':pk});
                }
            } else {
                // Base window
                if ($scope.data.meta.show_details) {
                    $scope.ws=ws+"/"+pk+"/modal";
                } else {
                    $scope.ws=ws+"/"+pk+"/editmodal";
                }
                
                // Base Window functions
                var functions = function(scope) {};
                var callback = function(scope) {
                    // Close our window
                    if (scope.base_window) {
                        scope.base_window.dismiss('cancel');
                    }
                    $state.go($state.current, {listid:scope.listid});
                    refresh(scope, $timeout, Register, undefined);
                };
                
                // Start modal window
                openmodal($scope, $timeout, $uibModal, 'lg', functions, callback);
            }
        }
    };
    // Extra help functions
    $scope.refresh = function () { refresh($scope, $timeout, Register, callback); }
    $scope.isList = function (obj) { return obj instanceof Array; };
    $scope.getKey = function (string) { return string.split("__")[1]; };
    $scope.date_change = function(name) {
        var found=false;
        angular.forEach(['second','minute','hour','day','month','year'], function(key){
            if (!found) {
                $scope.query[key]=null;
                if (name==key) { found=true; }
            }
        });
        refresh($scope, $timeout, Register, callback);
    };
    $scope.date_select = function (name, value) {
        $scope.query[name]=value;
        refresh($scope, $timeout, Register, callback);
    };
    $scope.rows_change = function (value) {
        $scope.query.rowsperpage=value;
        refresh($scope, $timeout, Register, callback);
    };
    $scope.page_change = function (value) {
        $scope.query.page=value;
        refresh($scope, $timeout, Register, callback);
    };

    $scope.reset_filter = function (){
        $scope.data.meta.search_filter_button = false;

        $scope.data=undefined;
        // Prepare query
        $scope.query = {
            "listid":listid,
            "elementid":null,
            "search":"",
            "page":1,
            "rowsperpage":50,
            "filters":{},
            "ordering":[],
            "year":null,
            "month":null,
            "day":null,
            "hour":null,
            "minute":null,
            "second":null,
            "context":{},
            "printer": null,
        };
        refresh($scope, $timeout, Register, callback);
    };

    $scope.print_excel = function(){
        $scope.query.printer = 'xls';
        refresh($scope, $timeout, Register, callback);
    };
    
    // Get details 
    $scope.list_modal = function(id) {
        // Base window
        id = String(id);
        $scope.wsbase = ws+"/";
        
        $scope.ws=$scope.wsbase+id+"/modal";
        $scope.initialbase = $scope.wsbase;
        
        $scope.id_parent = null;
        //$scope.initialws = $scope.ws;

        var functions = function(scope) {
            scope.init = function(id_parent){
                id = String(id);
                id_parent = String(id_parent);
                if ($scope.id_parent==null){
                    $scope.id_parent = id_parent;
                }
            }
            
            // DEPRECATED: 2017-02-14
            scope.createrelationfile = function(){
                var url = $scope.initialbase+$scope.id_parent+"/add"
                $scope.add(url);
            }

            // DEPRECATED: 2017-02-14
            scope.removefile = function(id, msg, id_parent) {
                id = String(id);
                id_parent = String(id_parent);
                if ($scope.id_parent==null){
                    $scope.id_parent = id_parent;
                }
                if (confirm(msg)){
                    var url = $scope.wsbase+id_parent+"/"+id+"/delete";
                    $scope.ws= $scope.wsbase+id_parent+"/modal";
                        
                    
                    $http.post( url, {}, {} )
                    .success(function(answer, stat) {
                        // Check the answer
                        if (stat==200 || stat ==202) {
                            // Reload details window
                            if ($scope.base_window != undefined){
                                $scope.base_window.dismiss('cancel');
                            }
                            $scope.base_reload[0]($scope.base_reload[1],$scope.base_reload[2]);
                            // If the request was accepted go back to the list
                        } else {
                            // Error happened, show an alert
                            console.log("ERROR "+stat+": "+answer)
                            console.log(answer);
                            alert("ERROR "+stat+": "+answer)
                        }
                    })
                    .error(function(data, status, headers, config) {
                        if (cnf_debug){
                            alert(data);
                        }else{
                            alert(cnf_debug_txt)
                        }
                    });
                        
                    // Base Window functions
                    var functions = function(scope) {};
                    var callback = function(scope) {
                        //scope.cb_window.dismiss('cancel');
                        //scope.cb_reload[0](scope.cb_reload[1]);
                        scope.det_window.dismiss('cancel');
                        scope.det_reload[0](scope.det_reload[1]);
                    };
                    // Start modal window
                    openmodal($scope, $timeout, $uibModal, 'lg', functions, callback);
                }
            };

            scope.edit = function(id, id_parent) {
                id = String(id);
                id_parent = String(id_parent);
                if ($scope.id_parent==null){
                    $scope.id_parent = id_parent;
                }
                // Base window
                $scope.ws=$scope.initialbase+id_parent+"/"+id+"/edit";
                
                // Base Window functions
                var functions = function(scope) {};
                var callback = function(scope) {
                    // Reload list window
                    if ($scope.base_window != undefined){
                        /*
                        following line is going to be executed in the case this 
                        manager is created in a modal window 
                        */
                        scope.base_window.dismiss('cancel');
                    }
                    scope.base_reload[0]($scope.base_reload[1],$scope.base_reload[2]);
                    // Reload details window
                    scope.det_window.dismiss('cancel');
                    scope.det_reload[0](scope.det_reload[1]);
                };
                
                // Start modal window
                openmodal($scope, $timeout, $uibModal, 'lg', functions, callback);
            };

            // DEPRECATED: 2017-02-14
            // Get details OCR
            scope.details_ocr = function(id) {
                id = String(id);
                // Base window
                $scope.ws=$scope.wsbase+id+"/ocr";
                $scope.initialws = $scope.ws;
                // Base Window functions
                var functions = function(scope) {
                    scope.gotoback = function() {
                        $scope.det_window.dismiss('cancel');
                    };
                };
                
                // Prepare for refresh
                $scope.det_reload=[scope.details,id];
                $scope.det_window=openmodal($scope, $timeout, $uibModal, 'lg', functions);
            };

            scope.details_view = function(id, $event) {
                // Base window
                $scope.ws=$scope.wsbase+id+"/view";
                $scope.initialws = $scope.ws;
                // Base Window functions
                var functions = function(scope) {
                    scope.gotoback = function() {
                        $scope.det_window.dismiss('cancel');
                    };

                    scope.edit = function(ar) {
                        // Base window
                        $scope.ws=$scope.wsbase+$scope.id_parent+"/"+id+"/edit";
                        
                        // Base Window functions
                        var functions = function(scope) {
                        };
                        var callback = function(scope) {
                            // Reload list window
                            if ($scope.base_window != undefined){
                                /*
                                following line is going to be executed in the case this 
                                manager is created in a modal window 
                                */
                                scope.base_window.dismiss('cancel');
                            }
                            scope.base_reload[0]($scope.base_reload[1],$scope.base_reload[2]);
                            // Reload details window
                            scope.det_window.dismiss('cancel');
                            scope.det_reload[0](scope.det_reload[1], scope.det_reload[2]);
                        };
                        
                        // Start modal window
                        openmodal($scope, $timeout, $uibModal, 'lg', functions, callback);
                    };
                };
                
                // Prepare for refresh
                $scope.det_reload=[scope.details_view, id, $event];
                $scope.det_window=openmodal($scope, $timeout, $uibModal, 'lg', functions);
                $event.stopPropagation();
            };
            modal_manager($scope, $timeout, $uibModal, $templateCache, $http, $scope);

            scope.addrecord = function(){
                var url = $scope.initialbase+$scope.id_parent+"/addfile"
                $scope.add(url);
            };
            scope.removerecord = function(id, msg){
                //var url = $scope.initialbase+$scope.id_parent+"/addfile"
                var url = $scope.wsbase+"/"+id+"/delete";
                del_item_sublist(id, msg, url, $scope, $http);
                //$scope.add(url);
            };
        };
        var callback = function(scope) {
            //scope.cb_reload[0](scope.cb_reload[1]);
        };
        // Prepare for refresh
        $scope.base_reload=[$scope.list_modal,id];
        $scope.base_window=openmodal($scope, $timeout, $uibModal, 'lg', functions);//, callback);

    };

    // DEPRECATED: 2017-02-14
    $scope.removedocinput = function(id, msg){
        if (confirm(msg)){
            var url = $scope.wsbase+id+"/delete";
            //$scope.ws= $scope.wsbase+id_parent+"/modal";
                
            
            $http.post( url, {}, {} )
            .success(function(answer, stat) {
                // Check the answer
                if (stat==200 || stat ==202) {
                    refresh($scope,$timeout,Register, callback);
                } else {
                    // Error happened, show an alert
                    console.log("ERROR "+stat+": "+answer)
                    console.log(answer);
                    alert("ERROR "+stat+": "+answer)
                }
            })
            .error(function(data, status, headers, config) {
                if (cnf_debug){
                    alert(data);
                }else{
                    alert(cnf_debug_txt)
                }
            });
        }
    };
    // DEPRECATED: 2017-02-14
    $scope.relationdocinput = function(id){
        id = String(id);
        $scope.wsbase = ws+"/";
        // Base window
        $scope.ws=$scope.wsbase+id+"/relationship";
        $scope.relationship(id);
    };
    // DEPRECATED: 2017-02-14
    $scope.relationdocoutput = function(id){
        id = String(id);
        $scope.wsbase = ws+"/";
        // Base window
        $scope.ws=$scope.wsbase+id+"/relationship";
        $scope.relationship(id);
    };
    // DEPRECATED: 2017-02-14
    $scope.relationship = function(id){
        
        $scope.initialws = $scope.ws;
        // Base Window functions
        var functions = function(scope) {
            scope.gotoback = function() {
                $scope.det_window.dismiss('cancel');
            };
        };
        
        // Prepare for refresh
        $scope.base_reload=[$scope.relationship, id];
        $scope.base_window=openmodal($scope, $timeout, $uibModal, 'lg', functions);

    };
    //
    $scope.open_details = function(id, id_parent) {
        id = String(id);
        id_parent = String(id_parent);
        $scope.wsbase = ws+"/";
        // Base window
        $scope.ws=$scope.wsbase+id+"/view/True";
        $scope.initialbase = $scope.wsbase+id_parent+"/"+id;
        
        $scope.initialws = $scope.ws;
        $scope.id_parent = id_parent;
        // Base Window functions
        var functions = function(scope) {
            scope.gotoback = function() {
                $scope.det_window.dismiss('cancel');
            };

            scope.edit = function(ar) {
                // Base window
                $scope.ws=$scope.initialbase+"/edit";
                
                // Base Window functions
                var functions = function(scope) {};
                var callback = function(scope) {
                    // Reload details window
                    $scope.det_window.dismiss('cancel');
                    $scope.det_reload[0]($scope.det_reload[1]);
                };
                
                // Start modal window
                openmodal($scope, $timeout, $uibModal, 'lg', functions, callback);
            };
        };
        
        // Prepare for refresh
        $scope.det_reload=[$scope.details_view, id, id_parent];
        $scope.det_window=openmodal($scope, $timeout, $uibModal, 'lg', functions);
    };

    $scope.switch_order = function (id) {
        if (id){
            var actual, max, absvalue, sign;
            actual=$scope.data.table.head.ordering[id];
            if (actual==undefined) {
                actual=0;
            }
            // Find the value and check if it is a quick change
            if (actual>0) {
                // Invert order, keep the rest
                $scope.data.table.head.ordering[id]=-actual;
            } else {
                // Find the max ordering
                max=0;
                angular.forEach($scope.data.table.head.ordering,function(value) {
                    absvalue=Math.abs(value)
                    if (absvalue>max) {
                        max=absvalue;
                    }
                });
                
                // If it is a new ordering element, set to max+1
                if (actual==0) {
                    $scope.data.table.head.ordering[id]=max+1;
                } else {
                    // The element is going out from the list, recount the list
                    if (actual==max) {
                        // Good luck, this is the last element from the list, remove ordering and we are done
                        $scope.data.table.head.ordering[id]=0;
                    } else {
                        // This is an object in the middel of the list recount the list and remove the object
                        angular.forEach($scope.data.table.head.ordering,function(value, key) {
                            if (value>0) {
                                sign=1;
                            } else {
                                sign=-1;
                            }
                            absvalue=Math.abs(value);
                            actual=Math.abs(actual);
                            if (absvalue<actual) {
                                $scope.data.table.head.ordering[key]=sign*absvalue;
                            } else if (absvalue>actual) {
                                $scope.data.table.head.ordering[key]=sign*(absvalue-1);
                            }
                        });
                        $scope.data.table.head.ordering[id]=0;
                    }
                }
            }
            // Refresh
            refresh($scope,$timeout,Register, callback);
        }
    };

    $scope.refreshlist = function(listid){
        $state.go($state.current, {listid:listid});
        refresh($scope, $timeout, Register, undefined);
    };

    $scope.removerecord = function(id, msg){
        $scope.base_reload = [$scope.refreshlist, $scope.listid, 0];
        var url = ws+"/"+id+"/delete";
        del_item_sublist(id, msg, url, $scope, $http);
    };
    // First query
    refresh($scope,$timeout,Register, callback);
};

function multiadd($scope, $rootScope, $timeout, $http, $window, $uibModal, $state, $stateParams, $templateCache, Register, listid, ws) {
    // Set our own url
    var url = ws+"/add";
    $scope.options={};
    
    // Remember http
    $scope.http=$http;
    
    // Clear cache
    $templateCache.remove(url);
    
    // Add datetimepicker function
    $scope.onTimeSet = function (newDate, oldDate) {
        console.log(newDate);
        console.log(oldDate);
    }
    
    // Add linked element
    $scope.linked=function (ngmodel, appname, modelname, formobj, formname, id, wsbaseurl) {
        inlinked($scope, $rootScope, $http, $window, $uibModal, $state, $stateParams, $templateCache, Register, ws, listid, ngmodel, appname, modelname, formobj, formname, id, wsbaseurl, $timeout);
    }
    
    // Set dynamic foreign fields controller functions
    dynamic_fields($scope);
    angularmaterialchip($scope);
    if (typeof(codenerix_extensions)!="undefined") {codenerix_extensions($scope, $timeout);}
    
    // Go to list
    $scope.gotoback = function() {
        $state.go('list'+listid);
    };
    
    // Update this element
    $scope.submit = function(form, next) {
        formsubmit($scope, $rootScope, $http, $window, $state, $templateCache, null, listid, url, form, next, 'add');
    };

    var fields = [];
    $scope.preUpdateField = function(field_o, field_d) {
        fields[field_o] = $scope[field_o];
        fields[field_d] = $scope[field_d];
    };
    $scope.UpdateField = function(field_o, field_d) {
        if (typeof($scope[field_d]) == "undefined" || $scope[field_d] == "" || fields[field_o] == fields[field_d]){
            $scope[field_d] = $scope[field_o];
        }
        fields[field_o] = $scope[field_o];
        fields[field_d] = $scope[field_d];
    };

    // DEPRECATED: 2017-02-14
    // calc date arrival and duration 
    // change duration
    $scope.changeDurationFlight = function() {
        var duration;
        var duration_time;
        var duration_tuple = changeDurationFlightC($scope);
        duration = duration_tuple[0];
        duration_time = duration_tuple[1];
        if (duration!=false){
            $scope.ArrivalForm.ArrivalForm_date = duration;
            $scope.ArrivalForm.ArrivalForm_date_time = duration_time;
        }
    };
    // DEPRECATED: 2017-02-14
    // change estimate date (departure and arrival)
    $scope.changeEstimatedDateFlight = function(){
        changeEstimatedDateFlight($scope);
    };
    // DEPRECATED: 2017-02-14
    $scope.changeActualDateFlight = function(){
        changeActualDateFlight($scope);
    };
};

function multidetails($scope, $rootScope, $timeout, $http, $window, $uibModal, $state, $stateParams, $templateCache, Register, listid, ws) {
    // Set our own url
    var url = ws+"/"+$stateParams.pk;
    
    // Clear cache
    $templateCache.remove(url);
    
    // Check if autostate has been disabled by the caller
    if (typeof(tabs_js)!='undefined' && tabs_js.length != 0){
        $state.go('details0.sublist'+listid+'.rows');
    }
    
    // Go to list
    $scope.gotoback = function() {
        $state.go('list'+listid);
    };
    
    // Delete this element
    $scope.edit = function() {
        // Clear cache
        $templateCache.remove(url);
        // Go to edit state
        $state.go('formedit'+listid,{pk:$stateParams.pk});
    };
    
    $scope.msg = function(msg){
        alert(msg);
    };

    // Delete this element
    $scope.delete = function(msg) {
        if (confirm(msg)) {
            // Clear cache
            $templateCache.remove(url);
            // User confirmed
            var url = ws+"/"+$stateParams.pk+"/delete";
            $http.post( url, {}, {} )
            .success(function(answer, stat) {
                // Check the answer
                if (stat==202) {
                    // If the request was accepted go back to the list
                    $state.go('list'+listid);
                } else {
                    // Error happened, show an alert
                    console.log("ERROR "+stat+": "+answer)
                    alert("ERROR "+stat+": "+answer)
                }
            })
            .error(function(data, status, headers, config) {
                if (cnf_debug){
                    alert(data);
                }else{
                    alert(cnf_debug_txt)
                }
            });
         }
    };
};

function multiedit($scope, $rootScope, $timeout, $http, $window, $uibModal, $state, $stateParams, $templateCache, Register, listid, ws) {
    // Set our own url
    var url = ws+"/"+$stateParams.pk+"/edit";
    $scope.options={};
    
    // Rembmer http
    $scope.http=$http;
    
    // Clear cache
    $templateCache.remove(url);
    
    // Add linked element
    $scope.linked=function (ngmodel, appname, modelname, formobj, formname, id, wsbaseurl) {
        inlinked($scope, $rootScope, $http, $window, $uibModal, $state, $stateParams, $templateCache, Register, ws, listid, ngmodel, appname, modelname,formobj, formname, id, wsbaseurl, $timeout);
    }
    
    // Set dynamic foreign fields controller functions
    dynamic_fields($scope);
    angularmaterialchip($scope);
    if (typeof(codenerix_extensions)!="undefined") {codenerix_extensions($scope, $timeout);}
    
    // Go to list
    $scope.gotoback = function() {
        // Clear cache
        $templateCache.remove(url);
        // Go to list
        $state.go('list'+listid);
        // $state.go('details'+listid,{pk:$stateParams.pk});
    };
    
    // Go to details
    $scope.gotodetails = function() {
        // Clear cache
        $templateCache.remove(url);
        // Go to list
        $state.go('details'+listid,{pk:$stateParams.pk});
    };
    
    // Reload this form
    $scope.reload = function(msg) {
        if (confirm(msg)) {
            // Clear cache
            $templateCache.remove(url);
            // Reload page
            $state.reload($state.current);
        }
    };

    // DEPRECATED: 2017-02-14
    // calc date arrival and duration 
    // change duration
    $scope.changeDurationFlight = function() {
        //changeDurationFlight($scope);
        var duration;
        var duration_time;
        var duration_tuple = changeDurationFlightC($scope);
        duration = duration_tuple[0];
        duration_time = duration_tuple[1];
        if (duration!=false && typeof($scope.ArrivalForm)!="undefined"){
            $scope.ArrivalForm.ArrivalForm_date = duration;
            $scope.ArrivalForm.ArrivalForm_date_time = duration_time;
        }
    };
    // DEPRECATED: 2017-02-14
    $scope.init = function (){
        angular.element(document).ready(function () {
            setTimeout(function (){
                $scope.changeEstimatedDateFlight();
            }, 1);
        });
    };
    // DEPRECATED: 2017-02-14
    //$scope.init();
    // change estimate date (departure and arrival)
    $scope.changeEstimatedDateFlight = function(){
        changeEstimatedDateFlight($scope);
    };
    // DEPRECATED: 2017-02-14
    $scope.changeEstimatedDateFlight = function(){
        changeActualDateFlight($scope);
    };
    // DEPRECATED: 2017-02-14
    $scope.changeActualDateFlight = function(){
        changeActualDateFlight($scope);
    };
    
    $scope.msg = function(msg){
        alert(msg);
    }
    // Delete this element
    $scope.delete = function(msg) {
        if (confirm(msg)) {
            // Clear cache
            $templateCache.remove(url);
            // User confirmed
            var url = ws+"/"+$stateParams.pk+"/delete";
            $http.post( url, {}, {} )
            .success(function(answer, stat) {
                // Check the answer
                if (stat==202) {
                    // If the request was accepted go back to the list
                    $state.go('list'+listid);
                } else {
                    // Error happened, show an alert
                    console.log("ERROR "+stat+": "+answer)
                    alert("ERROR "+stat+": "+answer)
                }
            })
            .error(function(data, status, headers, config) {
                if (cnf_debug){
                    alert(data);
                }else{
                    alert(cnf_debug_txt)
                }
            });
         }
    };
    
    // Update this element
    $scope.submit = function(form, next) {
        formsubmit($scope, $rootScope, $http, $window, $state, $templateCache, null, listid, url, form, next, 'edit');
    };

    var fields = [];
    $scope.preUpdateField = function(field_o, field_d) {
        fields[field_o] = $scope[field_o];
        fields[field_d] = $scope[field_d];
    };
    $scope.UpdateField = function(field_o, field_d) {
        if (typeof($scope[field_d]) == "undefined" || $scope[field_d] == "" || fields[field_o] == fields[field_d]){
            $scope[field_d] = $scope[field_o];
        }
        fields[field_o] = $scope[field_o];
        fields[field_d] = $scope[field_d];
    };
};


// DEPRECATED: 2017-02-14
 // calc date arrival and duration 
 // change duration
function changeDurationFlightC($scope){
    if ($scope.FlightForm_status != flightForm_status_takeof){
        if (typeof($scope.FlightForm)=="undefined"){
            var duration = $scope.FlightFormConfirm.FlightFormConfirm_duration;
        }else{
            var duration = $scope.FlightForm.FlightForm_duration;
        }
        if (typeof($scope.FlightForm)!="undefined" &&
            typeof($scope.FlightForm.FlightForm_departure_time)!="undefined" &&
            typeof($scope.FlightForm.FlightForm_departure_time_time)!="undefined" &&
            $scope.FlightForm.FlightForm_departure_time != "" && 
            $scope.FlightForm.FlightForm_departure_time_time != "" && 
            duration != "" && typeof(duration)!="undefined"){
                var fecha = $scope.FlightForm.FlightForm_departure_time.split("-");
                var hora_int = $scope.FlightForm.FlightForm_departure_time_time;
                var hora = [];
                if (typeof(hora_int) != "undefined"){
                    if (hora_int.length == 3){
                        hora.push(hora_int[0]);
                        hora.push(hora_int.substring(1,3));
                    }else{
                        hora.push(hora_int.substring(0,2));
                        hora.push(hora_int.substring(2,4));
                    }
                }

                var arrival = new Date(fecha[0], fecha[1]-1, fecha[2],hora[0],parseInt(hora[1])+parseInt(duration));
                var f = arrival.getFullYear() + '-' + ("0" + (arrival.getMonth() + 1)).slice(-2)+'-'+("0" + arrival.getDate()).slice(-2);
                var h = ("0" + arrival.getHours() ).slice(-2)+''+ ("0" + arrival.getMinutes() ).slice(-2);
                return [f, h];

        }
        else if (typeof($scope.DepartureForm)!="undefined" &&
            typeof($scope.DepartureForm.DepartureForm_date)!="undefined" &&
            $scope.DepartureForm.DepartureForm_date != "" && 
            duration != "" && typeof(duration)!="undefined"){
                var fecha = $scope.DepartureForm.DepartureForm_date.split("-");
                var hora_int = $scope.DepartureForm.DepartureForm_date_time;
                var hora = [];
                if (typeof(hora_int) != "undefined"){
                    if (hora_int.length == 3){
                        hora.push(hora_int[0]);
                        hora.push(hora_int.substring(1,3));
                    }else{
                        hora.push(hora_int.substring(0,2));
                        hora.push(hora_int.substring(2,4));
                    }
                }

                var arrival = new Date(fecha[0], fecha[1]-1, fecha[2],hora[0],parseInt(hora[1])+parseInt(duration));
                var f = arrival.getFullYear() + '-' + ("0" + (arrival.getMonth() + 1)).slice(-2)+'-'+("0" + arrival.getDate()).slice(-2);
                var h = ("0" + arrival.getHours() ).slice(-2)+''+ ("0" + arrival.getMinutes() ).slice(-2);
                return [f, h];
                // En Chrome y IE no funciona la siguiente linea por culpa de toLocaleFormat
                //return [arrival.toLocaleFormat("%Y-%m-%d"), arrival.toLocaleFormat("%H%M")];
        }else{
            return [false, false];
        }
    }
}
// DEPRECATED: 2017-02-14
// change estimate date (departure and arrival)
function changeEstimatedDateFlight($scope){
    if ($scope.FlightForm_status != flightForm_status_takeof){
        if (typeof($scope.ArrivalForm)!="undefined" &&
            typeof($scope.DepartureForm)!="undefined" &&
            typeof($scope.DepartureForm.DepartureForm_date)!="undefined" &&
            typeof($scope.ArrivalForm.ArrivalForm_date)!="undefined" &&
                $scope.DepartureForm.DepartureForm_date != "" && $scope.ArrivalForm.ArrivalForm_date != ""){

                var div = $scope.DepartureForm.DepartureForm_date;
                var fecha = div.split("-");
                var hora_int = $scope.DepartureForm.DepartureForm_date_time;
                var hora = [];
                if (typeof(hora_int)!="undefined"){
                    if (hora_int.length == 3){
                        hora.push(hora_int[0]);
                        hora.push(hora_int.substring(1,3));
                    }else{
                        hora.push(hora_int.substring(0,2));
                        hora.push(hora_int.substring(2,4));
                    }
                    var depa = new Date(fecha[0], fecha[1]-1, fecha[2],hora[0],hora[1]);

                    div = $scope.ArrivalForm.ArrivalForm_date;
                    hora_int = $scope.ArrivalForm.ArrivalForm_date_time;
                    
                    if (typeof(hora_int)!="undefined"){
                        fecha = div.split("-");
                        var hora = [];
                        if (hora_int.length == 3){
                            hora.push(hora_int[0]);
                            hora.push(hora_int.substring(1,3));
                        }else{
                            hora.push(hora_int.substring(0,2));
                            hora.push(hora_int.substring(2,4));
                        }
                        var arr = new Date(fecha[0], fecha[1]-1, fecha[2],hora[0],hora[1]);
                        var duration = (arr.getTime()/1000/60) -( depa.getTime()/1000/60);
                        if (typeof($scope.FlightForm)=="undefined"){
                            $scope.FlightFormConfirm.FlightFormConfirm_duration = duration;
                        }else{
                            $scope.FlightForm.FlightForm_duration = duration;
                        }
                    }
                }
        }
    }
}

function multisublist($scope, $uibModal, $templateCache, $http, $timeout) {

    modal_manager($scope, $timeout, $uibModal, $templateCache, $http, $scope);
    
    $scope.reload = undefined;
    $scope.onClickTab = function (url) {
        $templateCache.remove(url);
        $scope.currentTab = url;
        $scope.ws=url;
        $scope.wsbase=url + "/";
        
        modal_manager($scope, $timeout, $uibModal, $templateCache, $http, $scope);
        
        $scope.base_reload = [$scope.refreshTab,url];
    };
    
    $scope.refreshTab = function(url){
        /*
        function designed to make possible content tabs can be 
        refreshed. the refresh is made with the following tab change
        simulation. but it does not work if $timeout is not used. it 
        could be due to a unknown angular behaviour.
        */
        $templateCache.remove(url);
        $scope.currentTab = "";
        $timeout(function(){
            $scope.currentTab = url;
        },1);
    };
    
    $scope.addrecord = function(url){
        $scope.add(url);
    };

    $scope.removerecord = function(id, msg){
        //var url = $scope.initialbase+$scope.id_parent+"/addfile"
        var url = $scope.wsbase+id+"/delete";
        del_item_sublist(id, msg, url, $scope, $http);
        //$scope.add(url);
    };
    
    // DEPRECATED: 2017-02-14
    $scope.createpdf = function(type){

        var url = "/documents/createpdf";
        var files = [];
        $("input[name=checkfile]:checked").each(function (){
            files.push($(this).val());
        });
        return false;
        var datas = {
                        'pk': $scope.pk,
                        'files': files,
                    };
        if (files.length>0){
            $http.post( url, datas, {} )
                .success(function(answer, stat) {
                    // Check the answer
                    if (stat==200) {
                            
                        // Everything OK, close the window
                        if (answer.result){
                            $("#alertclipboard_error").html('').hide();
                            $("#alertclipboard_ok").html(answer.msg).show();

                            // reload files
                            var alltab = $("li.ng-isolate-scope");
                            var reload1 = '';
                            var reload2 = '';

                            alltab.each(function(){
                                if (!$(this).hasClass('active')){
                                    reload1 = $(this).attr("ng-click").split("(")[1].split(")")[0].replace(/'/g, "");
                                    $(this).addClass('active');
                                }else{
                                    reload2 = $(this).attr("ng-click").split("(")[1].split(")")[0].replace(/'/g, "");
                                    $(this).removeClass('active')
                                }
                                $scope.$parent.refreshTab(reload2);
                                $scope.$parent.refreshTab(reload1);
                            });
                            alert(answer.msg);
                            
                        }else{
                            $("#alertclipboard_ok").html('').hide();
                            $("#alertclipboard_error").html(answer.msg).show();
                            var reload = $("li.ng-isolate-scope.active").attr("ng-click").split("(")[1].split(")")[0].replace(/'/g, "");
                            $scope.$parent.refreshTab(reload);
                            alert(answer.msg);
                        }
                    } else {
                        // Error happened, show an alert
                        console.log("ERROR "+stat+": "+answer)
                        alert("ERROR "+stat+": "+answer)
                    }
                })
                .error(function(data, status, headers, config) {
                    if (cnf_debug){
                        alert(data);
                    }else{
                        alert(cnf_debug_txt)
                    }
                });
        }
    };
}

// Function that prints whatever URL you give to it
function printURL(xthis,url) {
    if ("_printIframe" in xthis){
        var iframe = xthis._printIframe;
    } else {
        var iframe;
        iframe = xthis._printIframe = document.createElement('iframe');
        document.body.appendChild(iframe);
        iframe.style.display = 'none';
        iframe.onload = function() {
            setTimeout(function() {
                iframe.focus();
                iframe.contentWindow.print();
            }, 1);
        };
    }
    iframe.src = url;
}

function angularmaterialchip(scope){
    scope.amc_querySearch = querySearch;
    scope.amc_autocompleteDemoRequireMatch = true;
    scope.amc_transformChip = transformChip;
    
    // options values
    scope.amc_items = {};
    // options seleted
    scope.amc_select = {};

    /**
    * Return the proper object when the append is called.
    */
    function transformChip(chip) {
        // If it is an object, it's already a known chip
        if (angular.isObject(chip)) {
            return chip;
        }
        // Otherwise, create a new one
        return { label: chip, id: 0 }
    }
    /**
    * Search for elements.
    */
    function querySearch (query, items, id) {
        if (scope.amc_items == undefined){
            scope.amc_items = [];
        }
        if (scope.amc_select[items] == undefined){
            scope.amc_select[items] = [];
        }
        if (scope.amc_items[items] == undefined){
            scope.amc_items[items] = {};
        }
        if (query == '*'){
            var results = query ? scope.amc_items[items].slice(0,50) : [];
        }else{
            var results = query ? scope.amc_items[items].filter(createFilterFor(query)) : [];
        }
        return results;
    }
    /**
    * Create filter function for a query string
    */
    function createFilterFor(query) {
        var lowercaseQuery = angular.lowercase(query);
        return function filterFn(option) {
            var results = (angular.lowercase(option.label).indexOf(lowercaseQuery) === 0) ||
                (option.id == lowercaseQuery);
            return results;
            //return (angular.lowercase(option.label).indexOf(lowercaseQuery) === 0) || (option.id == lowercaseQuery);
        };
    }
}
