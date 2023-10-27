/*
 *
 * django-codenerix
 *
 * Codenerix GNU
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
    'cfp.hotkeys',
    'frapontillo.bootstrap-switch',
];

// Default configuration
if (typeof (codenerix_debug) == 'undefined') {
    var codenerix_debug = false;
}
if (typeof (codenerix_hotkeys) == 'undefined') {
    var codenerix_hotkeys = true;
}

// Add the remove method to the Array structure
Array.prototype.remove = function(from, to) {
    var rest = this.slice((to || from) + 1 || this.length);
    this.length = from < 0 ? this.length + from : from;
    return this.push.apply(this, rest);
};

function multi_dynamic_select_dict(arg, form) {
    var dict = {};
    angular.forEach(arg, function(value, key) {
        dict[value] = form + '.' + value;
    });
    return dict;
};

function subscribers_worker(scope, subsjsb64) {
    var subsjs = atob(subsjsb64);
    if (subsjs) {
        try {
            var subs = JSON.parse(subsjs);
        } catch (e) {
            var subs = null;
        }
        if (subs) {
            if (typeof (CodenerixSubscribersWebsocket) != 'undefined') {
                var ws = CodenerixSubscribersWebsocket();

                if (ws) {
                    // Define opener
                    ws.opened = function() {
                        ws.debug('Requesting config');
                        ws.send(
                            {'action': 'get_config', 'uuid': ws.uuid}, null);
                        angular.forEach(
                            subs, (function(value, key) {
                                ws.debug('Subscribe ' + key);
                                ws.send(
                                    {'action': 'subscribe', 'uuid': key}, null);
                            }));
                    };

                    // Define receiver
                    ws.recv = function(message, ref, uuid) {
                        ws.debug(
                            'Got message from \'' + uuid + '\': ' +
                            JSON.stringify(message) + ' (REF: ' + ref + ')');

                        var action = message.action;

                        if (action == 'ping') {
                            ws.debug(
                                'Sending PONG ' + message.ref + ' (ref:' + ref +
                                ')');
                            ws.send({'action': 'pong'}, ref);
                        } else if (action == 'config') {
                            ws.debug(
                                'Got config: ' + JSON.stringify(message) +
                                ' (ref:' + ref + ')');
                        } else if (action == 'subscription') {
                            if (typeof (subs[uuid]) != 'undefined') {
                                ws.debug(
                                    'Got subscription message: ' +
                                    JSON.stringify(message));
                                angular.forEach(
                                    subs[uuid], (function(configtuple, key) {
                                        // Get subscription configuration
                                        var pkgkey = configtuple[0];
                                        var config = configtuple[1];
                                        if (typeof (config) == 'undefined') {
                                            config = { 'default': '' }
                                        }

                                        // If message brings data for our field
                                        var msgdata = message.data[pkgkey];
                                        if (typeof (msgdata) != 'undefined') {
                                            // Fill the field with package
                                            // information
                                            if (typeof (config.mapper) ==
                                                'undefined') {
                                                var newvalue = msgdata;
                                            } else {
                                                var newvalue = new Function(
                                                    'value',
                                                    config.mapper)(msgdata);
                                            }
                                        } else {
                                            // Fill the field with default
                                            // information from subscription
                                            // system
                                            if (typeof (config.default) ==
                                                'undefined') {
                                                var newvalue = '';
                                            } else {
                                                if (typeof (config.default
                                                                .mapper) ==
                                                    'undefined') {
                                                    var newvalue =
                                                        config.default;
                                                } else {
                                                    var newvalue = new Function(
                                                        'value',
                                                        config.default
                                                            .mapper)();
                                                }
                                            }
                                        }
                                        scope[scope.form_name][key]
                                            .$setViewValue(newvalue);
                                        scope[scope.form_name][key].$pristine =
                                            false;
                                        scope[scope.form_name][key].$dirty =
                                            true;
                                        scope[scope.form_name][key].$render();
                                    }));
                                scope[scope.form_name].$pristine = false;
                                scope[scope.form_name].$dirty = true;
                                scope.$apply();
                            } else {
                                ws.error(
                                    'Got message from unknown UUID \'' + uuid +
                                    '\': ' + JSON.stringify(message));
                            }
                        } else if (action == 'error') {
                            if ((typeof (message.error) == 'undefined') ||
                                (message.error == null)) {
                                var error = 'No error';
                            } else {
                                var error = message.error;
                            }
                            ws.error('Got an error from server: ' + error);
                        } else {
                            ws.send_error(
                                'Unknown action \'' + action + '\'', ref);
                        }
                    };

                    ws.closed = function() {
                        if (typeof (uuid) == 'undefined') {
                            ws.warning('We are not online! ');
                        } else {
                            ws.warning('We are not online! ' + uuid);
                        }
                    };

                    // Start websocket
                    ws.start();
                }
            }
        }
    }
};

// delete item form sublist in details view
function del_item_sublist(id, msg, url, scope, $http, args) {
    // Get ID as string
    id = String(id);

    // Prepare msg
    if (typeof (args) != 'undefined') {
        angular.forEach(args, function(value, key) {
            msg = msg.replace('<' + key + '>', value);
        });
    }

    // Ask the user
    if (confirm(msg)) {
        $http.post(url, {}, {})
            .success(function(answer, stat) {
                // Check the answer
                if (stat == 200 || stat == 202) {
                    // Reload details window
                    if (scope.base_window != undefined) {
                        scope.base_window.dismiss('cancel');
                    }
                    scope.base_reload[0](
                        scope.base_reload[1], scope.base_reload[2]);
                    // If the request was accepted go back to the list
                } else {
                    // Error happened, show an alert
                    console.log('ERROR ' + stat + ': ' + answer);
                    console.log(answer);
                    alert('ERROR ' + stat + ': ' + answer);
                }
            })
            .error(function(data, status, headers, config) {
                if (cnf_debug) {
                    alert(data);
                } else {
                    alert(cnf_debug_txt)
                }
            });

        var functions = function(scope) {};
        var callback = function(scope) {
            scope.det_window.dismiss('cancel');
            scope.det_reload[0](scope.det_reload[1]);
        };
    }
};

function openmodal(
    $scope,
    $timeout,
    $uibModal,
    size,
    functions,
    callback,
    locked,
    callback_cancel,
    inline) {
    var ngmodel = null;
    // Define the modal window
    $scope.build_modal = function(inline) {
        if (inline) {
            $scope.inurl = null;
            $scope.inhtml = inline;
        } else {
            $scope.inurl = $scope.ws;
            $scope.inhtml = null;
        }

        var info = {
            template: $scope.inhtml,
            templateUrl: $scope.inurl,
            controller: [
                '$scope',
                '$rootScope',
                '$http',
                '$window',
                '$uibModal',
                '$uibModalInstance',
                '$state',
                '$stateParams',
                '$templateCache',
                'Register',
                'ws',
                function(
                    $scope,
                    $rootScope,
                    $http,
                    $window,
                    $uibModal,
                    $uibModalInstance,
                    $state,
                    $stateParams,
                    $templateCache,
                    Register,
                    ws) {
                    // Save URL
                    $scope.url = ws;
                    $templateCache.remove(ws);

                    // Set submit function
                    $scope.submit = function(form, next) {
                        // Submit the form
                        formsubmit(
                            $scope,
                            $rootScope,
                            $http,
                            $window,
                            $state,
                            $templateCache,
                            $uibModalInstance,
                            null,
                            ws,
                            form,
                            'here',
                            'addmodal');
                    };

                    $scope.internal_submit = function(answer) {
                        $uibModalInstance.close(answer);
                    };

                    $scope.msg = function(msg) {
                        alert(msg);
                    };

                    $scope.delete = function(msg, target, nurl) {
                        if (typeof (nurl) == 'undefined') {
                            var uurl = $scope.url;
                        } else {
                            var uurl = nurl;
                        }

                        if ((target == 'delete') ||
                            (typeof (target) == 'undefined')) {
                            if (confirm(msg)) {
                                // Clear cache
                                $templateCache.remove(uurl);
                                // Get url
                                if (typeof (nurl) == 'undefined') {
                                    var uurl = uurl + '/../delete';
                                } else {
                                    var uurl = nurl;
                                }
                                console.log(uurl);
                                $http.post(uurl, {}, {})
                                    .success(function(answer, stat) {
                                        // Check the answer
                                        if (stat == 202) {
                                            // Everything OK, close the window
                                            $uibModalInstance.close(answer);
                                        } else {
                                            // Error happened, show an alert
                                            console.log(
                                                'ERROR ' + stat + ': ' + answer)
                                            alert(
                                                'ERROR ' + stat + ': ' + answer)
                                        }
                                    })
                                    .error(function(
                                        data, status, headers, config) {
                                        if (cnf_debug) {
                                            alert(data);
                                        } else {
                                            alert(cnf_debug_txt)
                                        }
                                    });
                            }
                        }
                    };

                    // Set cancel function
                    $scope.cancel = function() {
                        if (callback_cancel != undefined) {
                            callback_cancel($scope);
                        }
                        $uibModalInstance.dismiss('cancel');
                    };

                    // Enable dynamic select
                    $scope.http = $http;
                    dynamic_fields($scope);
                    angularmaterialchip($scope);
                    if (typeof (codenerix_extensions) != 'undefined') {
                        codenerix_extensions($scope, $timeout);
                    }

                    // Set dynamic scope filling with subscribers
                    $scope.subscribers = function(subsjsb64) {
                        subscribers_worker($scope, subsjsb64)
                    };

                    // Add linked element
                    $scope.linked = function(
                        base_url,
                        ngmodel,
                        appname,
                        modelname,
                        formobj,
                        formname,
                        id,
                        wsbaseurl) {
                        inlinked(
                            $scope,
                            $rootScope,
                            $http,
                            $window,
                            $uibModal,
                            $state,
                            $stateParams,
                            $templateCache,
                            Register,
                            ws,
                            null,
                            ngmodel,
                            base_url,
                            appname,
                            modelname,
                            formobj,
                            formname,
                            id,
                            wsbaseurl,
                            $timeout);
                    };

                    // Functions
                    if (functions != undefined) {
                        functions($scope);
                    }
                         }
            ],
            size: size,
            resolve: {
                         ws: function() {
                    return $scope.ws;
                }, },
        }

        if (locked != undefined || locked == true) {
            info['backdrop'] = 'static';
            info['keyboard'] = false;
        }

        var modalInstance = $uibModal.open(info);

        modalInstance.build_modal = $scope.build_modal;

        modalInstance.result.then(function(answer) {
            if (answer) {
                // Execute call back is requested
                if (callback != undefined) {
                    callback($scope, answer);
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
                if ($scope.reload != undefined) {
                    $scope.reload();
                }
            }
        });
        return modalInstance;
    };
    return $scope.build_modal(inline);
};

// Open a quick window wich will execute an action and will inform the user
// about the result in a nice way
function quickmodal(
    $scope,
    $timeout,
    $uibModal,
    size,
    action,
    functions,
    callback,
    callback_cancel) {
    var static_url = $scope.data.meta.url_static;

    var template =
        '<div class=\'modal-body text-center h1\' codenerix-html-compile=\'quickmodal.html\'></div>';
    $scope.quickmodal = {'html': $scope.data.meta.gentranslate.PleaseWait};
    $scope.quickmodal.html += '...<br/><img src=\'' + static_url +
                              'codenerix/img/loader.gif\'></div>';

    var internal_functions = function(scope) {
        functions(scope);
        scope.quickmodal = $scope.quickmodal;
    };

    var modalInstance = openmodal(
        $scope,
        $timeout,
        $uibModal,
        'sm',
        internal_functions,
        callback,
        true,
        callback_cancel,
        template);

    var quickmodal_ok = function(answer) {
        $scope.quickmodal.html = $scope.data.meta.gentranslate.Done +
                                 ' <img src=\'' + static_url +
                                 'codenerix/img/ok.gif\'>';
        $timeout(function() {
            modalInstance.close(answer);
        }, 2000);
    };
    var quickmodal_error = function(msg) {
        var html = '<span class=\'text-danger\'><strong>' +
                   $scope.data.meta.gentranslate.Error +
                   '</strong></span><br/>';
        html +=
            '<img src=\'' + static_url + 'codenerix/img/warning.gif\'><br/>';
        html +=
            '<button type="button" class="btn btn-sm btn-danger" ng-click="cancel()">' +
            $scope.data.meta.gentranslate.Cancel + '</button>';
        html += '<hr><h3>';
        html += msg;
        html += '</h3>';
        $scope.quickmodal.html = html;
    };

    // Execution given action
    action(quickmodal_ok, quickmodal_error);

    // Return modal window
    return modalInstance;
};

function modal_manager(
    $scope, $timeout, $uibModal, $templateCache, $http, scope) {
    // Add new alternative flight
    scope.add = function(url) {
        // Base window
        $scope.ws = url + '/add';

        // Base Window functions
        var functions = function(scope) {};
        var callback = function(scope) {
            // Close our window
            if (scope.base_window) {
                scope.base_window.dismiss('cancel');
            }

            // If base_reload specified
            if (scope.base_reload) {
                // Arguments are dinamically added
                scope.base_reload[0].apply(this, scope.base_reload.slice(1));
            }
        };

        // Start modal window
        openmodal($scope, $timeout, $uibModal, 'lg', functions, callback);
    };

    scope.removefile = function(id, msg, id_parent) {
        if (confirm(msg)) {
            if (typeof (id_parent) == 'undefined') {
                var url = $scope.wsbase + '/../' + id + '/delete';
                $scope.ws = $scope.wsbase;
            } else {
                var url = $scope.wsbase + '/' + id + '/delete';
                $scope.ws = $scope.wsbase + id_parent;
            }

            $http.post(url, {}, {})
                .success(function(answer, stat) {
                    // Check the answer
                    if (stat == 200 || stat == 202) {
                        // Reload details window
                        if ($scope.base_window != undefined) {
                            $scope.base_window.dismiss('cancel');
                        }
                        $scope.base_reload[0](
                            $scope.base_reload[1], $scope.base_reload[2]);
                        // If the request was accepted go back to the list
                    } else {
                        // Error happened, show an alert
                        console.log('ERROR ' + stat + ': ' + answer)
                        alert('ERROR ' + stat + ': ' + answer)
                    }
                })
                .error(function(data, status, headers, config) {
                    if (cnf_debug) {
                        alert(data);
                    } else {
                        alert(cnf_debug_txt)
                    }
                });

            // Base Window functions
            var functions = function(scope) {};
            var callback = function(scope) {};
            // Start modal window
            openmodal(
                $scope, $timeout, $uibModal, 'lg', functions);  //, callback);
        }
    };

    // DEPRECATED: 2017-02-14
    scope.change_alternative =
        function(id, msg) {
        if (confirm(msg)) {
            var url = $scope.ws + '/' + id + '/changealternative';

            $http.post(url, {}, {})
                .success(function(answer, stat) {
                    // Check the answer
                    if (stat == 200 || stat == 202) {
                        // Reload details window
                        if ($scope.base_window != undefined) {
                            $scope.base_window.dismiss('cancel');
                        }
                        $scope.base_reload[0](
                            $scope.base_reload[1], $scope.base_reload[2]);
                        // If the request was accepted go back to the list
                    } else {
                        // Error happened, show an alert
                        console.log('ERROR ' + stat + ': ' + answer)
                        alert('ERROR ' + stat + ': ' + answer)
                    }
                })
                .error(function(data, status, headers, config) {
                    if (cnf_debug) {
                        alert(data);
                    } else {
                        alert(cnf_debug_txt)
                    }
                });

            // Base Window functions
            var functions = function(scope) {};
            var callback = function(scope) {};
            // Start modal window
            openmodal(
                $scope, $timeout, $uibModal, 'lg', functions);  //, callback);
        }
    }

        // Get details
        scope.details = function(id) {
        // Base window
        $scope.ws = $scope.wsbase + id;
        $scope.initialws = $scope.ws;
        // Base Window functions
        var functions = function(scope) {
            // Get details for existing alternative flight
            scope.edit = function(ar) {
                // Base window
                $scope.ws = $scope.initialws + '/edit';

                // Base Window functions
                var functions = function(scope) {};
                var callback = function(scope) {
                    // Reload list window
                    if ($scope.base_window != undefined) {
                        /*
                        following line is going to be executed in the case this
                        manager is created in a modal window
                        */
                        scope.base_window.dismiss('cancel');
                    }
                    scope.base_reload[0](
                        $scope.base_reload[1], $scope.base_reload[2]);
                    // Reload details window
                    scope.det_window.dismiss('cancel');
                    scope.det_reload[0](scope.det_reload[1]);
                };

                // Start modal window
                openmodal(
                    $scope, $timeout, $uibModal, 'lg', functions, callback);
            };
            scope.gotoback = function() {
                $scope.det_window.dismiss('cancel');
            };

            $scope.msg = function(msg) {
                alert(msg);
            };

            scope.delete = function(msg) {
                if (confirm(msg)) {
                    // Clear cache
                    $templateCache.remove($scope.ws);
                    // User confirmed
                    var url = $scope.ws + '/delete';
                    $http.post(url, {}, {})
                        .success(function(answer, stat) {
                            // Check the answer
                            if (stat == 202) {
                                // Reload details window
                                if ($scope.base_window != undefined) {
                                    /*
                                    following line is going to be executed in
                                    the case this manager is created in a modal
                                    window
                                    */
                                    $scope.base_window.dismiss('cancel');
                                }
                                $scope.base_reload[0](
                                    $scope.base_reload[1],
                                    $scope.base_reload[2]);
                                // If the request was accepted go back to the
                                // list
                                $scope.det_window.dismiss('cancel');
                            } else {
                                // Error happened, show an alert
                                console.log('ERROR ' + stat + ': ' + answer)
                                alert('ERROR ' + stat + ': ' + answer)
                            }
                        })
                        .error(function(data, status, headers, config) {
                            if (cnf_debug) {
                                alert(data);
                            } else {
                                alert(cnf_debug_txt)
                            }
                        });
                    ;
                }
            };
        };

        // Prepare for refresh
        $scope.det_reload = [scope.details, id];
        $scope.det_window =
            openmodal($scope, $timeout, $uibModal, 'lg', functions);
    };

    // DEPRECATED: 2017-02-14
    // Get details OCR
    scope.details_ocr = function(id) {
        // Base window
        $scope.ws = $scope.wsbase + id + '/ocr';
        $scope.initialws = $scope.ws;
        // Base Window functions
        var functions = function(scope) {
            scope.gotoback = function() {
                $scope.det_window.dismiss('cancel');
            };
        };

        // Prepare for refresh
        $scope.det_reload = [scope.details, id];
        $scope.det_window =
            openmodal($scope, $timeout, $uibModal, 'lg', functions);
    };

    // Get details
    scope.list_modal_detail = function(id, $event) {
        // Base window
        $scope.ws = $scope.wsbase + 'modal';
        $scope.initialbase = $scope.wsbase;
        $scope.initialws = $scope.ws;

        var functions = function(scope) {};
        // Prepare for refresh
        $scope.det_reload = [scope.details, id];
        $scope.det_window =
            openmodal($scope, $timeout, $uibModal, 'lg', functions);
        //$event.stopPropagation();
    };

    // Get details customers
    scope.details_view = function(id, $event) {
        // Base window
        $scope.ws = $scope.wsbase + id + '/view';
        $scope.initialbase = $scope.wsbase + id;
        $scope.initialws = $scope.ws;
        // Base Window functions
        var functions = function(scope) {
            scope.gotoback = function() {
                $scope.det_window.dismiss('cancel');
            };

            scope.edit = function(ar) {
                // Base window
                $scope.ws = $scope.initialbase + '/edit';

                // Base Window functions
                var functions = function(scope) {};
                var callback = function(scope) {
                    // Reload list window
                    if ($scope.base_window != undefined) {
                        /*
                        following line is going to be executed in the case this
                        manager is created in a modal window
                        */
                        scope.base_window.dismiss('cancel');
                    }
                    scope.base_reload[0](
                        $scope.base_reload[1], $scope.base_reload[2]);
                    // Reload details window
                    scope.det_window.dismiss('cancel');
                    scope.det_reload[0](scope.det_reload[1]);
                };

                // Start modal window
                openmodal(
                    $scope, $timeout, $uibModal, 'lg', functions, callback);
            };
        };

        // Prepare for refresh
        $scope.det_reload = [scope.details, id];
        $scope.det_window =
            openmodal($scope, $timeout, $uibModal, 'lg', functions);
    };
};

// Function to help on refresh process
function refresh($scope, $timeout, Register, callback, internal) {
    // console.log("Refreshing "+$scope.elementid);
    if (($scope.data != undefined) && ($scope.data.filter != undefined) &&
        ($scope.data.table != undefined)) {
        // Update search
        $scope.query.search = $scope.data.filter.search;
        $scope.query.search_filter_button =
            $scope.data.meta.search_filter_button;
        // Update filters
        $scope.query.filters = {};
        angular.forEach($scope.data.filter.subfilters, function(token) {
            var value;
            if (token.kind == 'select') {
                value = parseInt(token.choosen, 10);
            } else if (token.kind == 'multiselect') {
                value = token.choosen;
            } else if (token.kind == 'multidynamicselect') {
                var id = null;
                angular.forEach(token.choosen, function(val, key) {
                    if (!isNaN(val)) {
                        id = val;
                    }
                });
                value = $scope.multidynamicseleted;
            } else if (token.kind == 'daterange') {
                if (token.value &&
                    (token.value.startDate || token.value.endDate)) {
                    value = token.value
                } else {
                    value = null;
                }
            } else {
                value = token.value;
            }
            $scope.query.filters[token.key] = value;
        });
        if ($scope.data.meta.search_filter_button) {
            angular.forEach($scope.data.filter.subfiltersC, function(token) {
                var value;
                if (token.kind == 'select') {
                    value = parseInt(token.choosen, 10);
                } else if (token.kind == 'daterange') {
                    if (token.value &&
                        (token.value.startDate || token.value.endDate)) {
                        value = token.value
                    } else {
                        value = null;
                    }
                } else {
                    value = token.value;
                }
                $scope.query.filters[token.key] = value;
            });
        }

        // Update ordering
        $scope.query.ordering = $scope.data.table.head.ordering;
    }
    // Update elementid
    $scope.query.elementid = $scope.elementid;
    // Refresh now
    var wrapper_callback = function() {
        $scope.data = $scope.tempdata;
        // Callback passed as an argument
        if (callback != undefined) {
            callback();
        }

        // Callback preinstalled in the scope
        if ((internal !== true) && ($scope.refresh_callback != undefined)) {
            $scope.refresh_callback();
        }
    };
    // Prepare arguments
    if (typeof ($scope.RegisterParams) == 'undefined') {
        var register_args = {};
    } else {
        var register_args = $scope.RegisterParams;
    }
    // Attach json
    register_args['json'] = $scope.query;
    // Call the service for the data
    $scope.tempdata = Register.query(register_args, wrapper_callback);
};

function formsubmit(
    $scope,
    $rootScope,
    $http,
    $window,
    $state,
    $templateCache,
    $uibModalInstance,
    listid,
    url,
    form,
    next,
    kind) {
    if (form.$dirty && form.$valid) {
        // Build in data
        var in_data = {};
        var form_name = form.$name;

        angular.forEach($scope.field_list, function(field) {
            // normal input html
            if ($scope[field] != undefined) {
                in_data[field] = $scope[field];
                // for multiselect (angular material chip)
            } else if ($scope.amc_select[field] != undefined) {
                var datas_temp = [];
                angular.forEach($scope.amc_select[field], function(el) {
                    datas_temp.push(el.id);
                });
                in_data[field] = datas_temp;
            }
        });

        angular.forEach(form, function(formElement, fieldName) {
            // If the fieldname starts with a '$' sign, it means it's an Angular
            // property or function. Skip those items.
            if (fieldName[0] === '$') {
                return;
            } else {
                if (fieldName != form_name) {
                    if (typeof (formElement.$viewValue) == 'object') {
                        var value = [];
                        angular.forEach(
                            formElement.$viewValue, function(val, key) {
                                if (val != undefined &&
                                    typeof (val.id) !== 'undefined') {
                                    value.push(val.id);
                                }
                            });
                        if (value.length == 0) value = formElement.$viewValue;
                        in_data[fieldName] = value;
                    } else {
                        in_data[fieldName] = formElement.$viewValue;
                    }
                }
            }
        });

        // Clear cache
        $templateCache.remove(url);

        // POST
        $http
            .post(url, in_data, {
                headers: {
                    'Content-Type':
                        'application/x-www-form-urlencoded; charset=UTF-8'
                }
            })
            .success(function(answer, stat) {
                // If the request was accepted
                if (stat == 202) {
                    // Call to call back before anything else
                    if (typeof ($scope.submit_callback) != 'undefined') {
                        if (codenerix_debug) {
                            console.log(
                                'Submit Callback found, calling it back!');
                        }
                        next = $scope.submit_callback(
                            listid, url, form, next, kind, answer, stat);
                        if (codenerix_debug) {
                            console.log(
                                'Submit callback said next state is \'' + next +
                                '\'');
                        }
                    }

                    // Go back to the list
                    if (next == 'here') {
                        if (kind == 'add') {
                            // Jump to the edit form
                            $state.go('formedit' + listid, {'pk': answer.pk});
                            // Reload page
                            $state.reload($state.current);
                        } else if (
                            (kind == 'addmodal') || (kind == 'editmodal')) {
                            // Set the primary key and let it finish execution
                            $uibModalInstance.close(answer);
                        } else {
                            // Reset all elements status
                            angular.forEach(
                                form, function(formElement, fieldName) {
                                    // If the fieldname starts with a '$' sign,
                                    // it means it's an Angular property or
                                    // function. Skip those items.
                                    if (fieldName[0] === '$') {
                                        return;
                                    } else {
                                        formElement.$pristine = true;
                                        formElement.$dirty = false;
                                    }
                                });
                            // Reset form status
                            form.$pristine = true;
                            form.$dirty = false;
                            // Reload page
                            $state.reload($state.current);
                        }
                    } else if (next == 'new') {
                        $state.go('formadd' + listid);
                        $state.transitionTo(
                            'formadd' + listid,
                            {},
                            {reload: true, inherit: true, notify: true});
                    } else if (next == 'details') {
                        $state.go('details' + listid, {'pk': answer.__pk__});
                    } else if (next == 'none') {
                        if (codenerix_debug) {
                            console.warn(
                                'Automatic destination state has been avoided by programmer\'s request!');
                        }
                    } else {
                        // Default state
                        $state.go('list' + listid);
                    }
                } else if (stat == 200) {
                    if (answer['error']) {
                        $scope.error = answer['error'];
                    } else {
                        if (next == 'here') {
                            $uibModalInstance.close();
                            $uibModalInstance.build_modal(answer);
                        } else {
                            var templateUrl = $state.current.templateUrl;
                            $state.current.template = answer;
                            // $state.transitionTo($state.current,
                            // $state.$current.params, { reload: true, inherit:
                            // true, notify: true });
                            $state.transitionTo(
                                $state.current,
                                {},
                                {reload: true, inherit: true, notify: true});
                            $state.current.templateUrl = templateUrl;
                        }
                    }
                } else {
                    $window.alert(
                        'Internal error detected (Error was: [ERROR ' + stat +
                        '] ' + answer + ')')
                }
            })
            .error(function(answer, stat) {
                if (stat == 409) {
                    // Detected 409 error, the form is trying to communicate
                    // that a field has failed and is providing feedaback to
                    // resolve de error
                    angular.forEach(answer, function(value, key) {
                        angular.forEach(value, function(msg) {
                            console.log('->' + key + ':' + msg['message']);
                            form.$valid = false;
                            form.$invalid = true;
                            form[key].$valid = false;
                            form[key].$invalid = true;
                            form[key].djng_error = true;
                            form[key].djng_error_msg = msg['message'];
                        });
                    });
                } else {
                    $window.alert(
                        'Internal error detected (Error was: [ERROR ' + stat +
                        '] ' + answer + ')');
                }
            });
    } else {
        console.info(
            'formsubmit() will work only when form is $dirty and $valid');
    }
};

// Linked elements behavior when they are called by a link() call from a click
// on a plus symbol
function inlinked(
    $scope,
    $rootScope,
    $http,
    $window,
    $uibModal,
    $state,
    $stateParams,
    $templateCache,
    Register,
    ws,
    listid,
    ngmodel,
    base_url,
    appname,
    modelname,
    formobj,
    formname,
    id,
    wsbaseurl,
    $timeout,
    inline) {
    // Get incoming attributes
    $scope.ngmodel = ngmodel;
    $scope.base_url = base_url;
    $scope.appname = appname;
    $scope.modelname = modelname;
    $scope.formobj = formobj;
    $scope.formname = formname;

    // Build ws callback
    $scope.ws = '/' + base_url + appname + '/' + modelname + '/';
    if (id) {
        $scope.ws += id + '/editmodal';
    } else {
        $scope.ws += 'addmodal';
    }
    $templateCache.remove($scope.ws);

    // Define the modal window
    $scope.build_modal = function(inline) {
        if (inline) {
            $scope.inurl = null;
            $scope.inhtml = inline;
        } else {
            $scope.inurl = $scope.ws;
            $scope.inhtml = null;
        }
        var modalInstance = $uibModal.open({
            template: $scope.inhtml,
            templateUrl: $scope.inurl,
            controller: [
                '$scope',
                '$rootScope',
                '$http',
                '$window',
                '$uibModal',
                '$uibModalInstance',
                '$state',
                '$stateParams',
                '$templateCache',
                'Register',
                'ws',
                'hotkeys',
                function(
                    $scope,
                    $rootScope,
                    $http,
                    $window,
                    $uibModal,
                    $uibModalInstance,
                    $state,
                    $stateParams,
                    $templateCache,
                    Register,
                    ws,
                    hotkeys) {
                    // Autostart multitools
                    if (id) {
                        var action = 'editmodal'
                        multiedit(
                            $scope,
                            $rootScope,
                            $timeout,
                            $http,
                            $window,
                            $uibModal,
                            $state,
                            $stateParams,
                            $templateCache,
                            Register,
                            0,
                            ws,
                            hotkeys);
                    } else {
                        var action = 'addmodal'
                        multiadd(
                            $scope,
                            $rootScope,
                            $timeout,
                            $http,
                            $window,
                            $uibModal,
                            $state,
                            $stateParams,
                            $templateCache,
                            Register,
                            0,
                            ws,
                            hotkeys);
                    }

                    // Set submit function
                    $scope.submit = function(form, next) {
                        // Submit the form control
                        formsubmit(
                            $scope,
                            $rootScope,
                            $http,
                            $window,
                            $state,
                            $templateCache,
                            $uibModalInstance,
                            listid,
                            ws,
                            form,
                            'here',
                            action);
                    };
                    // Set delete function
                    $scope.delete = function(msg, url) {
                        if (confirm(msg)) {
                            // Build url
                            if (url == undefined) {
                                url = ws + '/../delete';
                            }
                            // Clear cache
                            $templateCache.remove(url);
                            // User confirmed
                            $http.post(url, {}, {})
                                .success(function(answer, stat) {
                                    // Check the answer
                                    if (stat == 202) {
                                        // Everything OK, close the window
                                        answer['delete'] = true;
                                        $uibModalInstance.close(answer);
                                    } else {
                                        // Error happened, show an alert
                                        console.log(
                                            'ERROR ' + stat + ': ' + answer)
                                        alert('ERROR ' + stat + ': ' + answer)
                                    }
                                })
                                .error(function(data, status, headers, config) {
                                    if (cnf_debug) {
                                        alert(data);
                                    } else {
                                        alert(cnf_debug_txt)
                                    }
                                });
                        }
                    };
                    // Set cancel function
                    $scope.cancel = function() {
                        $uibModalInstance.dismiss('cancel');
                    };
                              }
            ],
            size: 'lg',
            resolve: {
                              Register: function() {
                    return $scope.Register;
                }, ws: function() {
                    return $scope.ws;
                }, },
        });
        modalInstance.build_modal = $scope.build_modal;

        modalInstance.result.then(function(answer) {
            // Select the new created item
            if (answer) {
                var options = $scope.options[ngmodel];
                if (answer['__pk__']) {
                    if ('delete' in answer && answer['delete'] == true) {
                        // Delete item
                        var set_view_value = true;
                        if (options == undefined) {
                            // multiselect
                            options = $scope.amc_items[ngmodel]
                            set_view_value = false;
                        }
                        var new_options = [];
                        angular.forEach(options, function(key, value) {
                            // Update element
                            if (options[value]['id'] != answer['__pk__']) {
                                new_options[value] = options[value]
                            }
                        });
                        $scope.options[ngmodel] = new_options;
                        formobj[ngmodel].$setViewValue(null);

                    } else if (ngmodel) {
                        // Select the new created item
                        var set_view_value = true;
                        if (options == undefined) {
                            // multiselect
                            options = $scope.amc_items[ngmodel]
                            set_view_value = false;
                        }
                        var inlist = false;
                        angular.forEach(options, function(key, value) {
                            // Update element
                            if (options[value]['id'] == answer['__pk__']) {
                                options[value]['label'] = answer['__str__'];
                                inlist = true;
                            }
                        });
                        if (!inlist) {
                            // Attach the new element
                            if (options == undefined) {
                                options = [];
                            }
                            options.push({
                                'id': answer['__pk__'],
                                'label': answer['__str__']
                            });
                        }
                        /*
                         * WORKING ON IT!
                        console.log(answer['__pk__']);
                        console.log(options);
                        console.log(formobj[ngmodel]);
                        //
                        ------------------------------------------******************
                        // Select the new option
                        formobj[ngmodel].$setViewValue(null);
                        formobj[ngmodel].$setViewValue(answer['__pk__']);
                        // Change dirty/pristine for the input
                        formobj[ngmodel].$pristine = false;
                        formobj[ngmodel].$dirty = true;
                        */

                        if (set_view_value) {
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

                    // refresh info of fields associate by pk
                    if (wsbaseurl != undefined) {
                        var url = wsbaseurl + answer['__pk__'];
                        $http.get(url, {}, {}).success(function(answer, stat) {
                            angular.forEach(answer, function(val, key) {
                                $scope[key] = val;
                                // formobj[key] = val;
                            });
                        });
                    }
                }
            }
        });
    };
    $scope.build_modal(inline);
};

function dynamic_fields(scope) {
    /*
    Inside the DynamicSelects will exists $externalScope which refers to the
    Scope outside the selector
    */

    // Memory for dynamic fields
    scope.dynamicFieldsMemory = {};

    scope.multidynamicseleted = [];

    scope.removeSelected = function(list) {
        var temp = [];
        angular.forEach(scope.multidynamicseleted, function(val, key) {
            if (list.indexOf(val.id) >= 0) {
                temp.push(val);
            }
        });
        scope.multidynamicseleted = temp;
    };

    scope.saveSelected = function(list, value) {
        var id = null;
        angular.forEach(value, function(val, key) {
            if (!isNaN(val)) {
                id = val;
            }
        });
        var remove = null;
        if (id !== null) {
            var i = 1;
            angular.forEach(scope.multidynamicseleted, function(val, key) {
                if (val.id == id) {
                    var h = scope.multidynamicseleted.splice(i, 1);
                    remove = true;
                }
                i = i + 1;
            });
            if (remove != true) {
                angular.forEach(list, function(val, key) {
                    if (val.id == id) {
                        scope.multidynamicseleted.push(
                            {'label': val.label, 'id': val.id});
                    }
                });
            }
        }
        if (id == null || scope.multidynamicseleted.length == 0) {
            scope.multidynamicseleted = [];
        }
        return false;
    };

    // Control how the selected ui-select field works with pristine/dirty states
    scope.selectedOptionSelect = function(
        input, value, ngchange, externalScope, selected) {
        if ((typeof (input) == 'undefined') || (input === null)) {
            // Placeholder input
            input = {'$setViewValue': function() {}};
        }
        if (!input.$dirty) {
            input.$dirty = input.$viewValue != value;
        }
        if (input.$pristine) {
            input.$pristine = input.$viewValue == value;
        }
        input.$setViewValue(input.$modelValue);

        // Set selected
        input.selected = selected;
        // Decode JSON if we got JSON DATA
        angular.forEach(input.selected, (function(value, key) {
                            if (key == '__JSON_DATA__') {
                                input.selected['__JSON_DATA__'] =
                                    angular.fromJson(value);
                                return;
                            }
                        }));

        // Process the selected item
        if (scope.valuegetforeingkey[input.$name] != undefined &&
            'rows' in scope.valuegetforeingkey[input.$name]) {
            // Function to process new value set
            var set_new = function(scope, key, answer, value) {
                // Set new value
                if (scope[scope.form_name] != undefined &&
                    scope[scope.form_name][key] != undefined) {
                    var element = scope[scope.form_name][key];
                    if (typeof (value) == 'object') {
                        if (scope.options != undefined && key in
                                                              scope.options) {
                            var info = [];
                            info['id'] = value[0];
                            info['label'] = value[1];
                            scope.options[key].push(info);
                            element.$setViewValue(value[0]);
                        } else if ('__JSON_DATA__' in value) {
                            element.$setViewValue(
                                value);  // Update form elements
                            if (key in scope) {
                                scope[key] =
                                    value;  // Update scope slements (it doesn't
                                            // connect properly scope with
                                            // children scopes)
                            }
                        }
                    } else {
                        element.$setViewValue(value);
                    }
                    element.$render();
                    if (ngchange !== undefined) {
                        // Evaluate the expresion
                        scope.$eval(ngchange);
                    }
                }

                if ('_clear_' in answer) {
                    angular.forEach(
                        answer['_clear_'], (function(v, key) {
                            scope[scope.form_name][v].$setViewValue('');
                            scope[scope.form_name][v].$render();
                        }));
                }
                if ('_readonly_' in answer) {
                    scope.dynamicFieldsMemory.autocomplete.readonly =
                        answer['_readonly_'];
                    angular.forEach(
                        scope.dynamicFieldsMemory.autocomplete.readonly,
                        (function(key) {
                            scope['readonly_' + key] = true;
                        }));
                }
            };

            // For each field
            angular.forEach(
                scope.valuegetforeingkey[input.$name].rows,
                (function(value2, key) {
                    if (value2['id'] == input.$modelValue) {
                        scope.resetAutoComplete();
                        angular.forEach(
                            value2, (function(value3, key) {
                                var async = true;
                                var kind = undefined;
                                if (key && key != 'label' && key != 'id' &&
                                    key[0] != '$') {
                                    var keysp = key.split(':')
                                    if (keysp.length >= 2) {
                                        key = keysp[0];
                                        kind = keysp[1];
                                        if (kind == '__JSON_DATA__') {
                                            try {
                                                value3 = {
                                                    '__JSON_DATA__':
                                                        angular.fromJson(value3)
                                                };
                                            } catch (e) {
                                                value3 = undefined;
                                                console.log('ERROR: ' + e);
                                            }
                                        } else if (kind == '__SCOPE_CALL__') {
                                            value3 = scope.$eval(value3);
                                        } else if (kind == '__SERVICE_CALL__') {
                                            async = false;
                                            jQuery.ajax({
                                                url: value3,
                                                success: function(answer) {
                                                    value3 = answer['value'];
                                                    // Set new value
                                                    set_new(
                                                        scope,
                                                        key,
                                                        value2,
                                                        value3);
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
        } else if (ngchange !== undefined) {
            // Evaluate the expresion
            scope.$eval(ngchange, {'$externalScope': externalScope});
        }
    };

    scope.multi_dynamic_select_dict = function(arg, formname) {
        return multi_dynamic_select_dict(arg, formname);
    };

    // Manage dynamic foreignkeys selects working with ui-select
    scope.valuegetforeingkey = {};
    scope.getForeignKeys = function(
        http,
        baseurl,
        options,
        filter,
        modelname,
        modelvalue,
        search,
        deepness) {
        if ((search.length >= deepness) || (search == '*')) {
            var filter2 = {};
            angular.forEach(filter, function(value, key) {
                if (typeof (value) == 'object') {
                    filter2[key] = value.$viewValue;
                } else {
                    filter2[key] = value;
                }
            });
            // Prepare URL
            var url =
                baseurl + search + '?def=1&filter=' + angular.toJson(filter2)

            // Send the request
            http.get(url, {}, {}).success(function(answer, stat) {
                scope.valuegetforeingkey[modelname] = answer;
                if ('clear' in answer) {
                    answer = answer['rows'];
                }
                options[modelname] = answer;
            });
        } else if (modelvalue == undefined) {
            options[modelname] = [{'id': null, 'label': '---------'}];
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
            angular.forEach(
                scope.dynamicFieldsMemory.autocomplete.clear, (function(key) {
                    // Set new value
                    scope[key] = '';
                }));
            scope.dynamicFieldsMemory.autocomplete.clear = [];
        }
        // Readonly fields
        if (scope.dynamicFieldsMemory.autocomplete.readonly) {
            angular.forEach(
                scope.dynamicFieldsMemory.autocomplete.readonly,
                (function(key) {
                    scope['readonly_' + key] = false;
                }));
            scope.dynamicFieldsMemory.autocomplete.readonly = [];
        }
    };

    scope.getAutoComplete = function(
        http,
        baseurl,
        options,
        filter,
        modelname,
        modelvalue,
        search,
        deepness) {
        if ((search.length >= deepness) || (search == '*')) {
            var filter2 = {};
            angular.forEach(filter, function(value, key) {
                if (typeof (value) == 'object') {
                    filter2[key] = value.$viewValue;
                } else {
                    filter2[key] = value;
                }
            });

            // Prepare URL
            var url = baseurl + search + '?filter=' + angular.toJson(filter2)

            // Send the request
            return http.get(url, {}, {}).then(function(answer) {
                // Remember what to clear and what to set readonly
                scope.dynamicFieldsMemory.autocomplete.clear_tmp =
                    answer.data.clear;
                scope.dynamicFieldsMemory.autocomplete.readonly_tmp =
                    answer.data.readonly;
                // Return answer
                return answer.data.rows
            });
        }
    };

    // Set dynamic values that came from an autofield
    // Note: Only refresh input NOT OTHER TAG HTML (We believe that angular is
    // not aware about the new DOM and that Django-Angular is only compiling the
    // inputs so Angular is aware only about them)
    scope.autoFillFields = function($item, $model, $label, $event) {
        // Copy structures
        if (scope.dynamicFieldsMemory.autocomplete.clear_tmp) {
            scope.dynamicFieldsMemory.autocomplete.clear =
                scope.dynamicFieldsMemory.autocomplete.clear_tmp;
            scope.dynamicFieldsMemory.autocomplete.clear_tmp = [];
        }
        if (scope.dynamicFieldsMemory.autocomplete.readonly_tmp) {
            scope.dynamicFieldsMemory.autocomplete.readonly =
                scope.dynamicFieldsMemory.autocomplete.readonly_tmp;
            scope.dynamicFieldsMemory.autocomplete.readonly_tmp = [];
        }
        // Set readonly
        angular.forEach(
            scope.dynamicFieldsMemory.autocomplete.readonly, (function(key) {
                scope['readonly_' + key] = true;
            }));
        // Process the selected item
        angular.forEach($item, (function(value, key) {
                            if (key != 'label') {
                                // Set new value
                                scope[key] = value;
                            }
                        }));
    };
};

/*
function answer_rendered(element,$q) {
    var deferred = $q.defer(),
    intervalKey,
    counter = 0,
    maxIterations = 50;

    intervalKey = setInterval(function () {
        var jel = element[0].children.length;               // Javascript first
usable row (second on the list) if (jel>2) { deferred.resolve(element);
            clearInterval(intervalKey);
        } else if (counter >= maxIterations) {
            deferred.reject("no element found");
            clearInterval(intervalKey);
        }
        counter++;
    }, 100);

    return deferred.promise;
};

answer_rendered(element,$q).then(function (element) {
        scope.refresh_vtable();
}, function (message) {
        console.log(message);
});
*/

var codenerix_directive_htmlcompile = [
    'codenerixHtmlCompile',
    [
        '$compile',
        function($compile) {
            return {
                restrict: 'A', link: function(scope, element, attrs) {
                    scope.$watch(
                        attrs.codenerixHtmlCompile,
                        function(newValue, oldValue) {
                            element.html(newValue);
                            $compile(element.contents())(scope);
                        });
                }
            }
        }
    ]
];

var codenerix_directive_onenter = [
    'codenerixOnEnter',
    [function() {
        return function(scope, element, attrs) {
            element.bind('keydown keypress', function(event) {
                if (event.which === 13) {
                    scope.$apply(function() {
                        scope.$eval(attrs.codenerixOnEnter);
                    });
                    event.preventDefault();
                }
            });
        };
    }]
];

var codenerix_directive_ontab = [
    'codenerixOnTab',
    [function() {
        return function(scope, element, attrs) {
            element.bind('keydown keypress', function(event) {
                if (event.which === 9) {
                    scope.$apply(function() {
                        scope.$eval(attrs.codenerixOnTab);
                    });
                    event.preventDefault();
                }
            });
        };
    }]
];

var codenerix_directive_focus = [
    'codenerixFocus',
    [
        '$timeout',
        function($timeout) {
            return {
                scope: {trigger: '=codenerixFocus'},
                link: function(scope, element) {
                    scope.$watch('trigger', function(value) {
                        if (value === true) {
                            $timeout(function() {
                                element[0].focus();
                                scope.trigger = false;
                            });
                        }
                    });
                }
            };
            /*
            return {
                link: function(scope, element, attrs) {
                    scope.$watch(attrs.codenerixFocus, function(value) {
                        console.log('FOCUS=',value);
                        if(value === true) {
                            $timeout(function() {
                                element[0].focus();
                                console.log(scope.trigger);
                                console.log(scope[attrs.codenerixFocus]);
                                scope[attrs.codenerixFocus] = false;
                                console.log(scope[attrs.codenerixFocus]);
                            });
                        }
                    });
                }
            };
            */
        }
    ]
];

var codenerix_directive_vtable = [
    'codenerixVtable',
    [
        '$window',
        '$timeout',
        '$q',
        'Register',
        function($window, $timeout, $q, Register) {
            return {
                restrict: 'A',
                transclude: true,
                replace: false,
                template:
                    '<tr><td ng-repeat=\'column in data.table.head.columns\' ng-style="{height: codenerix_vtable.top+\'px\'}" style=\'margin:0px;padding:0px;border:1px solid #fff;\' id=\'codenerix_vtable_top\'></td></tr>' +
                        '<tr ng-repeat="row in data.table.body" id=\'row{{row.pk}}\' ng-click="detail(row.pk)" ng-class="{\'row_selected\':$index+1==selected_row}" ui-view>' +
                        '<tr><td ng-repeat=\'column in data.table.head.columns\' ng-style="{height: codenerix_vtable.bottom+\'px\'}" style=\'margin:0px;padding:0px;border:1px solid #fff;\'></td></tr>',
                link: function(scope, element, attrs) {
                    if (scope.data != undefined &&
                        scope.data.meta != undefined &&
                        scope.data.meta.vtable != undefined &&
                        scope.data.meta.vtable) {
                        // console.log("Codenerix VTable: Load");

                        // Initialize scope
                        // scope.query.page=1;
                        // scope.query.rowsperpage=1;
                        if (scope.$parent.$parent.listid != undefined) {
                            scope = scope.$parent.$parent;
                        } else if (scope.$parent.listid != undefined) {
                            scope = scope.$parent;
                        } else {
                            console.error(
                                'Couldn\'t align \'scope\' variable with its $parent\'s');
                        }
                        scope.codenerix_vtable = {};
                        scope.codenerix_vtable.top = 0;
                        scope.codenerix_vtable.bottom = 0;
                        scope.codenerix_vtable.last_scroll =
                            (new Date).getTime();

                        // Install refresh auto callback
                        scope.refresh_callback = function() {
                            if (scope.data != undefined &&
                                scope.data.meta != undefined &&
                                scope.data.meta.vtable != undefined &&
                                scope.data.meta.vtable) {
                                // console.log("Codenerix VTable: Refresh
                                // detected"); Ensure refresh_vtable after
                                // render
                                $timeout(scope.codenerix_vtable.refresh, 0);
                                //} else {
                                //    console.log("Codenerix VTable: Refresh
                                //    detected but no VTABLE");
                            }
                        };

                        // Remove all watchers on scroll event
                        scope.$on('$destroy', function() {
                            angular.element($window).off('scroll');
                        });
                        // Install scroll watcher
                        angular.element($window).on('scroll', function() {
                            if (scope.data != undefined &&
                                scope.data.meta != undefined &&
                                scope.data.meta.vtable != undefined &&
                                scope.data.meta.vtable) {
                                // console.log("Codenerix VTable: Scroll
                                // detected"); Ensure refresh_vtable after
                                // render
                                var new_last_scroll = (new Date).getTime();
                                scope.codenerix_vtable.last_scroll =
                                    new_last_scroll;
                                $timeout(
                                    scroll_refresh(scope, new_last_scroll),
                                    300);
                                // Save changes in the scope
                                scope.$apply();
                            }
                        });

                        // Refresh VTable system
                        scope.codenerix_vtable.refresh = function(
                            cache, callback) {
                            // console.log("Codenerix VTable: Refresh VTable");

                            // === FUTURE HELPERS ===
                            // ================================================
                            // var row_position =
                            // jel.getBoundingClientRect().top; // Offset
                            // position to Screen Top

                            // === GEOMETRY DECISIONS ===
                            // ============================================ Get
                            // geometry and details
                            var jel =
                                element[0]
                                    .children[1];  // Javascript first usable
                                                   // row (second on the list)
                            var row_height = jel.scrollHeight;  // Row height
                            var row_total =
                                scope.data.meta.row_total;  // Total rows in the
                                                            // last answer
                            var window_height =
                                $window.innerHeight;  // Window height

                            // Multiplier for pagesize (1:default)
                            // - 1: many stops for caching, fast loading
                            // - 4: few stops for caching, long time loading
                            var page_size_multiplier = 1;
                            // Size of the window in number of rows
                            var rowsperpage =
                                Math.ceil(window_height / row_height) *
                                page_size_multiplier;

                            if (row_total > 0) {
                                // Calculate geometry details
                                var cache =
                                    4;  // Cache size is 4 (firstpage + 4 pages)
                                var scroll_height =
                                    row_total *
                                    row_height;  // Get scroll height
                                var scroll_position =
                                    $window.scrollY;  // Get scroll position
                                var proportion =
                                    scroll_position /
                                    scroll_height;  // Get proportion
                                var row_to_show =
                                    proportion *
                                    row_total;  // Row that we should show
                                var page_to_show =
                                    Math.floor(row_to_show / rowsperpage) +
                                    1;  // Page to show
                                var vpagefirst =
                                    page_to_show - 1;  // First page to bring
                                var vpagelast =
                                    vpagefirst +
                                    cache;  // Last page to bring (firstpage +
                                            // cache pages)
                                if (vpagefirst < 1) {
                                    vpagefirst = 1;
                                }  // Protect first page not to be out of range
                                var vpagetotal =
                                    vpagelast -
                                    vpagefirst;  // Total pages to bring

                                // === DEBUG ===
                                // =========================================================
                                // Prepare DEBUG message
                                // var msg ="Codenerix VTable: Debug"
                                // msg+="\n\tfirst: "+vpagefirst;
                                // msg+="\n\tbring: "+vpagetotal;
                                // msg+="\n\trows:  "+rowsperpage;

                                // Show DEBUG message
                                // console.log(msg);

                                // === MEMORY ===
                                // ========================================================
                                if ((cache !== true) ||
                                    (vpagefirst !=
                                     scope.codenerix_vtable.vpagefirst) ||
                                    (vpagetotal !=
                                     scope.codenerix_vtable.pages_to_bring) ||
                                    (rowsperpage !=
                                     scope.codenerix_vtable.rowsperpage)) {
                                    scope.codenerix_vtable.vpagefirst =
                                        vpagefirst;
                                    scope.codenerix_vtable.pages_to_bring =
                                        vpagetotal;
                                    scope.codenerix_vtable.rowsperpage =
                                        rowsperpage;

                                    // === QUERY ===
                                    // =========================================================
                                    // Set new query filters
                                    scope.query.page = vpagefirst;
                                    scope.query.pages_to_bring = vpagetotal;
                                    scope.query.rowsperpage = rowsperpage;
                                    // Refresh table with internal state set to
                                    // 'true' to avoid recursion
                                    refresh(
                                        scope, $timeout, Register, function() {
                                            // === REDRAW ===
                                            // ========================================================
                                            // Set top and bottom depending on
                                            // the result
                                            scope.codenerix_vtable.top =
                                                rowsperpage * (vpagefirst - 1) *
                                                row_height;
                                            scope.codenerix_vtable.bottom =
                                                (row_total -
                                                 (vpagelast * rowsperpage)) *
                                                row_height;
                                            // === CALLBACK ===
                                            // ======================================================
                                            // Callback passed as an argument
                                            if (callback != undefined) {
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
        }
    ]
];

var codenerix_directive_autofocus = [
    'codenerixAutofocus',
    [
        '$timeout',
        function($timeout) {
            return {
                restrict: 'AC',
                link: function(_scope, _element) {
                    $timeout(function() {
                        _element[0].focus();
                    }, 0);
                }
            };
        }
    ]
];

// We got the example code from https://stackoverflow.com/users/1957251/khanh-to
// from Khanh TO We then adapted his version from $modal to $uibModal which is
// the one we use with CODENERIX and we renamed it to codenerixReallyClick
var codenerix_directive_reallyclick = [
    'codenerixReallyClick',
    [
        '$uibModal',
        function($uibModal) {
            var ModalInstanceCtrl = function($scope, $uibModalInstance) {
                $scope.ok = function() {
                    $uibModalInstance.close();
                };

                $scope.cancel = function() {
                    $uibModalInstance.dismiss('cancel');
                };
            };

            return {
                restrict: 'A', scope: {
                    codenerixReallyClick: '&',
                    codenerixReallyActive: '&?',
                    codenerixReallyOk: '&?',
                    codenerixReallyCancel: '&?',
                    item: '='
                },
                    link: function(scope, element, attrs) {
                        element.bind('click', function() {
                            // Get attributes
                            var message = attrs.codenerixReallyMessage ||
                                          'Are you sure ?';
                            var size = attrs.codenerixReallySize || 'md';
                            if (typeof (scope.codenerixReallyActive) ==
                                'undefined') {
                                var active = true;
                            } else {
                                var active = scope.codenerixReallyActive();
                            }
                            if (typeof (scope.codenerixReallyOk) ==
                                'undefined') {
                                var ok = true;
                            } else {
                                var ok = scope.codenerixReallyOk();
                            }
                            if (typeof (scope.codenerixReallyCancel) ==
                                'undefined') {
                                var cancel = true;
                            } else {
                                var cancel = scope.codenerixReallyCancel();
                            }

                            // If the directive is active
                            if (active) {
                                var modalHtml = '<div class="modal-body">' +
                                                message + '</div>';
                                modalHtml += '<div class="modal-footer">';
                                if (ok) {
                                    modalHtml +=
                                        '<button class="btn btn-primary" ng-click="ok()">OK</button>';
                                }
                                if (cancel) {
                                    modalHtml +=
                                        '<button class="btn btn-danger" ng-click="cancel()">Cancel</button>'
                                }
                                modalHtml += '</div>';

                                var uibModalInstance = $uibModal.open({
                                    template: modalHtml,
                                    controller: ModalInstanceCtrl,
                                    size: size,
                                });

                                uibModalInstance.result.then(
                                    function() {
                                        scope.codenerixReallyClick(
                                            {item: scope.item});
                                    },
                                    function() {
                                        // Modal dismissed
                                    });
                            } else {
                                scope.codenerixReallyClick({item: scope.item});
                            }
                        });
                    }
            }
        }
    ]
];

var codenerix_run = [
    '$http',
    '$rootScope',
    '$cookies',
    function($http, $rootScope, $cookies) {
        // Add automatic CSRFToken
        $http.defaults.headers.post['X-CSRFToken'] = $cookies.csrftoken;
        $http.defaults.headers.common['X-CSRFToken'] = $cookies.csrftoken;
        // Set internal XSRFToken
        $http.defaults.xsrfHeaderName = 'X-CSRFToken';
        $http.defaults.xsrfCookieName = 'csrftoken';
        // Redirect if login required
        $rootScope.$on('event:auth-loginRequired', function() {
            window.location = '/';
        });
    }
];

var codenerix_config1 = [
    'cfpLoadingBarProvider',
    function(cfpLoadingBarProvider) {
        // cfpLoadingBarProvider.includeSpinner = false;
        cfpLoadingBarProvider.spinnerTemplate =
            '<div id="loading-bar-spinner"><div class="bubblingG"><span id="bubblingG_1"></span><span id="bubblingG_2"></span><span id="bubblingG_3"></span></div></div>';
        cfpLoadingBarProvider.latencyThreshold = 0;
    }
];

var codenerix_config2 = [
    '$httpProvider',
    function($httpProvider) {
        $httpProvider.defaults.headers.common['X-Requested-With'] =
            'XMLHttpRequest';
    }
];

// Add a new library to codenerix_libraries if it doesn't exists yet
function codenerix_addlib(name) {
    if (typeof (name) === 'string') {
        if (codenerix_libraries.indexOf(name) == -1) {
            codenerix_libraries.push(name);
        } else {
            console.info('Library \'' + name + '\' already in codenerix');
        }
    } else {
        console.error('codenerix_addlib() is expecting a string')
    }
};

// Add a new libraries to codenerix_libraries if it doesn't exists yet
function codenerix_addlibs(names) {
    if (Object.prototype.toString.call(names) === '[object Array]') {
        angular.forEach(names, function(name, key) {
            codenerix_addlib(name);
        });
    } else {
        console.error('codenerix_addlibs() is expecting an Array')
    }
};

// Remove a library from codenerix_libraries if it does exists
function codenerix_dellib(name) {
    if (typeof (name) === 'string') {
        var index = codenerix_libraries.indexOf(name);
        if (index != -1) {
            codenerix_libraries.remove(index);
        } else {
            console.info('Library \'' + name + '\' not found in codenerix');
        }
    } else {
        console.error('codenerix_dellib() is expecting a string')
    }
};

// Add a new libraries to codenerix_libraries if it doesn't exists yet
function codenerix_dellibs(names) {
    if (Object.prototype.toString.call(names) === '[object Array]') {
        angular.forEach(names, function(name, key) {
            codenerix_dellib(name);
        });
    } else {
        console.error('codenerix_dellibs() is expecting an Array')
    }
}

// Function to wrap refresh_vtable calls so scroll will not stress the system
// with massive events
function scroll_refresh(scope, new_last_scroll) {
    return function() {
        if (scope.codenerix_vtable.last_scroll == new_last_scroll) {
            scope.codenerix_vtable.refresh(true);
        };
    }
};

// Define get_static if no other method exists
if (typeof (get_static) == 'undefined') {
    var get_static = function(path) {
        if (typeof (static_url) != 'undefined') {
            var result = static_url + path;
        } else {
            var result = '/static/' + path;
        }
        return result;
    };
}

function codenerix_builder(libraries, routes, redirects) {
    /*
     * libraries:
     *      - It is a list of mosules to be added or removed from the loader of
     * the controller.
     *      - The loader will set by default the modules to load that are set in
     * the 'codenerix_libraries' variable
     *      - Use 'module' to add a module to the loader
     *      - Use '-module' to remove a module from the loader
     *      - Example: [ '-codenerixServices', 'newModule' ]
     *
     * routes: { dictionary of routes to add or remove from the routing system }
     *         { 'state': [ 'url', 'template path', 'controller' ],
     *           'state': null }
     *          Description:
     *              state: state name (it can be 'otherwise' meaning the default
     * or otherwise method from urlRouterProvider) url: Angular url template
     * path: URI path to the template controller: name of the controller to use
     * for this state Predefined states:
     *              - States: list0, list0.rows, formadd0, formedit0, details0
     *              - If you assign <null> to the state then the state is not
     * added to the routing system. Ex: { 'list0':null }
     *              - If you set <null> to any element in the list
     * URL/Template/Controller will not be added to the route in the router:
     *                  Ex: { 'list0': [ '/urlbase', null, 'newController'] }
     *              - If you set <undefined> to any element in the list
     * URL/Template/Controller predefined value will be used. Ex: { 'list0': [
     * '/urlbase', null, 'newController'] } Customized states:
     *              - You can add any custom state to the router dictionary
     *              - If you set <null> to any element in the list
     * URL/Template/Controller will not be added to the route in the router:
     *                  Ex: { 'customState': [ '/custom_url', null,
     * 'customController'] }
     *
     * redirects: [ list of redirects (tuple of 2 elements [what, handler] ) ]
     * by default it will add otherwise to '/' if no other configuration is set.
     *  - what: String | RegExp | UrlMatcher | otherwise
     *  - handler: String | Function
     *  - Examples:
     *      [ '', '/add' ]          // Blank route to /add
     *      [ '/', '/add' ]         // route list "/" to /add
     *      [ '/add', '/edit' ]     // route add "/add" to /edit
     *      [ /aspx/i, '/index' ]   // Redirect to /index using a regex
     *      [ 'complex',            // Complex redirection
     *          ['$match', '$stateParams', function ($match, $stateParams) {
     *              if ($state.$current.navigable != state ||
     * !equalForKeys($match, $stateParams)) { $state.transitionTo(state, $match,
     * false);
     *              }
     *          }]
     *      ]
     *      [undefined, '/index'] // Otherwise redirect to /index
     *      [undefined, function($injector, $location) {
     *          ... some advanced code...
     *      }] // Otherwise redirect as function says
     *
     * This three sentences works the same:
     *  'list0': [undefined,
     * get_static('codenerix_products/partials/products_list.html'), undefined]
     * -> OLD way 'list0': {templateUrl:
     * get_static('codenerix_products/partials/products_list.html')} -> NEW way
     *  'list0': {'views': {'': {templateUrl:
     * get_static('codenerix_products/partials/products_list.html')}}} -> NEW
     * way with several views
     *
     *
     * Example custom ui-view name
     *  'list0': {
     *              'url': '/.../:pk/...',  // The url that we will use for this
     * state 'params': {'pk': null}, // Params from the state that we will pass
     * to views 'views': {
     *                  '': {...},  // ui-view without name
     *                  'example1': {....}, // ui-view named example1 ->
     * ui-view='example1' 'example2': {....},
     *              },
     *           }
     *
     * Notes:
     *      - If libraries is not set (it is undefined), libraries will become
     * an empty list [] by default
     *      - If router not set (different than undefined), the routing system
     * will be initialized and the default URL will be '/'
     */

    // Check libraries
    if (libraries === undefined) {
        libraries = [];
    }
    // Prepare libraries
    angular.forEach(libraries, function(name, key) {
        if (name[0] == '-') {
            name = name.substring(1);
            codenerix_dellib(name);
        } else {
            codenerix_addlib(name);
        }
    });

    // Build the base module
    var module =
        angular
            .module('codenerixApp', codenerix_libraries)

            // Default configuration
            .config(codenerix_config1)
            .config(codenerix_config2)

            // Set Codenerix directives
            .directive(
                codenerix_directive_vtable[0], codenerix_directive_vtable[1])
            .directive(
                codenerix_directive_focus[0], codenerix_directive_focus[1])
            .directive(
                codenerix_directive_autofocus[0],
                codenerix_directive_autofocus[1])
            .directive(
                codenerix_directive_htmlcompile[0],
                codenerix_directive_htmlcompile[1])
            .directive(
                codenerix_directive_onenter[0], codenerix_directive_onenter[1])
            .directive(
                codenerix_directive_ontab[0], codenerix_directive_ontab[1])
            .directive(
                codenerix_directive_reallyclick[0],
                codenerix_directive_reallyclick[1])

            // Set routing system
            .run(codenerix_run);

    // Decide about routing
    if (routes !== null) {
        // Create the routing system
        module.config([
            '$urlRouterProvider',
            function($urlRouterProvider) {
                var otherwise = false;
                if (typeof (redirects) != 'undefined') {
                    angular.forEach(redirects, function(value, key) {
                        if (value.length == 2) {
                            var what = value[0];
                            var handler = value[1];

                            if (what == undefined) {
                                // We are setting an otherwise
                                otherwise = true;
                                // Check we have a handler
                                if (handler !== null) {
                                    if (codenerix_debug == true) {
                                        console.log(
                                            'Router: default \'' + handler +
                                            '\'');
                                    }
                                    $urlRouterProvider.otherwise(handler);
                                } else {
                                    // We do not have a handler
                                    if (codenerix_debug == true) {
                                        console.log(
                                            'Router: no default route set!');
                                    }
                                }
                            } else {
                                if (codenerix_debug == true) {
                                    console.log(
                                        'Router: redirect \'' + what +
                                        '\' to \'' + handler + '\'');
                                }
                                $urlRouterProvider.when(what, handler);
                            }
                        } else {
                            console.error(
                                'Detected redirect with wrong rule, they should be Array(2)');
                        }
                    });
                }
                if (!otherwise) {
                    if (codenerix_debug == true) {
                        console.log('Router: default \'/\'');
                    }
                    $urlRouterProvider.otherwise('/');
                }
            }
        ]);

        // Check if we should use default routes
        if (routes === undefined) {
            routes = {}
        }
        // Build known
        var known = Array();
        // List base
        known.push([
            'list0',
            {
                '': {
                     url: '/',
                     templateUrl: get_static('codenerix/partials/list.html'),
                     controller: 'ListCtrl'
                }
        }
        ]);
        // List rows header and summary
        var rows_dict = null;
        if (typeof (static_partial_row) != 'undefined') {
            if (rows_dict == null) {
                rows_dict = {};
            }
            rows_dict[''] = {templateUrl: static_partial_row};
        }
        if (typeof (static_partial_header) != 'undefined') {
            if (rows_dict == null) {
                rows_dict = {};
            }
            rows_dict['header'] = {templateUrl: static_partial_header};
        }
        if (typeof (static_partial_summary) != 'undefined') {
            if (rows_dict == null) {
                rows_dict = {};
            }
            rows_dict['summary'] = {templateUrl: static_partial_summary};
        }
        if (rows_dict != null) {
            known.push(['list0.rows', rows_dict]);
        }
        // If we are in a from (ws_entry_point exists)
        if (typeof (ws_entry_point) != 'undefined') {
            // Form add
            known.push([
                'formadd0',
                {
                    '': {
                         url: '/add',
                         templateUrl: function(params) {
                            return '/' + ws_entry_point + '/add';
                        }, controller: 'FormAddCtrl'
                    }
            }
            ]);
            // Form edit
            known.push([
                'formedit0',
                {
                    '': {
                         url: '/:pk/edit',
                         templateUrl: function(params) {
                            return '/' + ws_entry_point + '/' + params.pk +
                                   '/edit';
                        }, controller: 'FormEditCtrl'
                    }
            }
            ]);
            // Details
            known.push([
                'details0',
                {
                    '': {
                         url: '/:pk',
                         templateUrl: function(params) {
                            return '/' + ws_entry_point + '/' + params.pk;
                        }, controller: 'DetailsCtrl'
                    }
            }
            ]);

            // Sublists
            var tag = '';
            var controller = '';
            // If we have tabs (sublists) to render
            if (typeof (tabs_js) != 'undefined') {
                // For every tab
                angular.forEach(tabs_js, function(tab, i) {
                    // Decide wether this is static or autogenerated sublist
                    // (STATIC sublists are deprecated)
                    if (tab.auto) {
                        controller = 'SubListCtrl';
                    } else {
                        controller = 'SubListStaticCtrl';
                    }
                    // Sublist
                    known.push([
                        'details0.sublist' + tab.internal_id + '',
                        {
                            '': {
                                 url: '/sublist' + tab.internal_id + '/:listid/',
                                 templateUrl:
                                    get_static('codenerix/partials/list.html'),
                                 controller: controller
                            }
                    }
                    ]);
                    // Sublist rows header and summary
                    var rows_dict = null;
                    if (typeof (tab.static_partial_row) != 'undefined') {
                        if (rows_dict == null) {
                            rows_dict = {};
                        }
                        rows_dict[''] = {'templateUrl': tab.static_partial_row};
                    }
                    if (typeof (tab.static_partial_header) != 'undefined') {
                        if (rows_dict == null) {
                            rows_dict = {};
                        }
                        rows_dict['header'] = {
                            templateUrl: tab.static_partial_header
                        };
                    }
                    if (typeof (tab.static_partial_summary) != 'undefined') {
                        if (rows_dict == null) {
                            rows_dict = {};
                        }
                        rows_dict['summary'] = {
                            templateUrl: tab.static_partial_summary
                        };
                    }
                    if (rows_dict != null) {
                        known.push([
                            'details0.sublist' + tab.internal_id + '.rows',
                            rows_dict
                        ]);
                    }
                });
            }
            // Add sublist0 at the end as a default option
            known.push([
                'details0.sublist',
                {
                    '': {
                         url: '/sublist/0/',
                         templateUrl: get_static('codenerix/partials/list.html'),
                         controller: 'SubListCtrl'
                    }
            }
            ]);
        }

        // Process known routes
        angular.forEach(known, function(value, key) {
            // Get configuration
            var state = value[0];
            var state_dict = value[1];
            if (state in routes) {
                var route = routes[state];
                if (route === null) {
                    // Remove actual state, we will not process it
                    state = null;
                } else {
                    // Get information
                    if (typeof (route.length) == 'number') {
                        // It is a list (old method)
                        angular.forEach(
                            ['url', 'templateUrl', 'controller'],
                            function(key, value) {
                                if (route[value] === null) {
                                    delete state_dict[''][key];
                                } else if (route[value] !== undefined) {
                                    state_dict[''][key] = route[value];
                                }
                            });
                    } else {
                        angular.forEach(route, function(v, k) {
                            if (k == '') {
                                angular.forEach(route[''], function(v2, k2) {
                                    state_dict[''][k2] = v2;
                                });
                            } else {
                                state_dict[k] = v;
                            }
                        });
                    }
                }
                // Remove the key from routes
                delete routes[state];
            }

            // Set state_dict to final stage
            for (var k in state_dict) {
                if (k != '') {
                    break;
                }
            }
            if (k == '') {
                state_dict = state_dict[''];
            } else {
                state_dict = {views: state_dict};
            }

            // Check if we have an state to process (the user maybe defined it
            // as null, what means it wants to remove this state)
            if (state !== null) {
                // Attach the new state
                module.config([
                    '$stateProvider',
                    '$urlRouterProvider',
                    function($stateProvider, $urlRouterProvider) {
                        if (codenerix_debug == true) {
                            console.log(
                                'Router: known \'' + state + '\' -> ' +
                                JSON.stringify(state_dict));
                        }
                        $stateProvider.state(state, state_dict);
                    }
                ]);
            }
        });

        // Process new routes
        angular.forEach(routes, function(config, state) {
            if (config !== null) {
                if (typeof (config.length) == 'number') {
                    // Get configuration
                    var url = config[0];
                    var template = config[1];
                    var ctrl = config[2];

                    // Build the state dictionary
                    var state_dict = {};
                    if (url !== null) {
                        state_dict['url'] = url;
                    }
                    if (template !== null) {
                        state_dict['templateUrl'] = template;
                    }
                    if (ctrl !== null) {
                        state_dict['controller'] = ctrl;
                    }
                } else {
                    var state_dict = config;
                }

                // Set state_dict to final stage
                for (var k in state_dict) {
                    if (k != '') {
                        break;
                    }
                }
                if (k == '') {
                    state_dict = state_dict[''];
                } else {
                    state_dict = state_dict;
                }

                // Attach the new state
                module.config([
                    '$stateProvider',
                    '$urlRouterProvider',
                    function($stateProvider, $urlRouterProvider) {
                        if (codenerix_debug == true) {
                            console.log(
                                'Router: new \'' + state + '\' -> ' +
                                JSON.stringify(state_dict));
                        }
                        $stateProvider.state(state, state_dict);
                    }
                ]);
            }
        });
    }

    if (codenerix_debug == true) {
        console.info(
            'Router: if the path of the URL doesn\'t exists, AngularJS will now warn you in anyway, the state will stay with a blank page');
    }


    // Add factory
    module.factory('ListMemory', function() {
        return {};
    });

    // Return the just built module
    return module;
};

function multilist(
    $scope,
    $rootScope,
    $timeout,
    $location,
    $uibModal,
    $templateCache,
    $http,
    $state,
    Register,
    ListMemory,
    listid,
    ws,
    callback,
    sublist,
    hotkeys) {
    // Move to inside state to get double view resolved
    let listid_txt = listid;
    if ((callback == undefined) && (!sublist)) {
        $state.go('list' + listid + '.rows');
    } else {
        listid_txt = 's' + listid;
    }
    $scope.listid = listid;
    // Startup memory
    var l = ListMemory;
    if ((l.mem != undefined) && (l.mem[listid_txt])) {
        // We have already a memory from what happened here
        $scope.query = l.mem[listid_txt];
    } else {
        // Enviroment
        $scope.ws = ws;
        $scope.wsbase = ws + '/';
        $scope.page = 1;
        $scope.pages_to_bring = 1;
        $scope.rowsperpage = 1;
        $scope.filters = [];
        $scope.ordering = [];
        $scope.options = {};
        $scope.year = null;
        $scope.month = null;
        $scope.day = null;
        $scope.hour = null;
        $scope.minute = null;
        $scope.second = null;
        $scope.context = {};

        // Prepare query
        $scope.query = {
            'listid': listid,
            'elementid': null,
            'search': '',
            'page': 1,
            'pages_to_bring': 1,
            'rowsperpage': 50,
            'filters': {},
            'ordering': [],
            'year': null,
            'month': null,
            'day': null,
            'hour': null,
            'minute': null,
            'second': null,
            'context': {},
        };
    }

    // Initialize general variables
    $scope.focus = {};
    $scope.focus.search_box = false;
    $scope.selected_row = 0;

    // Remember http
    $scope.http = $http;
    // Set dynamic foreign fields controller functions
    dynamic_fields($scope);
    angularmaterialchip($scope);
    if (typeof (codenerix_extensions) != 'undefined') {
        codenerix_extensions($scope, $timeout);
    }

    // Set dynamic scope filling with subscribers
    $scope.subscribers = function(subsjsb64) {
        subscribers_worker($scope, subsjsb64)
    };


    // Memory
    if (l.mem == undefined) {
        l.mem = {};
    }
    l.mem[listid_txt] = $scope.query;

    if (sublist) {
        $scope.refresh_callback = function() {
            $scope.$apply();
        }
    }

    // Edit/detail link
    $scope.set_elementid = function(value, name) {
        if ($rootScope.elementid == value) {
            $rootScope.elementid = null;
            $rootScope.elementname = null;
        } else {
            $rootScope.elementid = value;
            $rootScope.elementname = name;
        }
    };

    $scope.addnew = function() {
        if ($scope.data.meta.linkadd) {
            if (!sublist) {
                $state.go('formadd' + listid);
            } else {
                // Base window
                $scope.ws = ws + '/addmodal';

                // Base Window functions
                var functions = function(scope) {};
                var callback = function(scope) {
                    // Close our window
                    if (scope.base_window) {
                        scope.base_window.dismiss('cancel');
                    }
                    $state.go($state.current, {listid: scope.listid});
                    refresh(scope, $timeout, Register, undefined);
                };

                // Start modal window
                openmodal(
                    $scope, $timeout, $uibModal, 'lg', functions, callback);
            }
        }
    };

    // Go to previous row
    $scope.goto_row_previous =
        function() {
        if ($scope.selected_row > 1) {
            $scope.selected_row = $scope.selected_row - 1;
        }
    }
        // Go to next row
        $scope.goto_row_next = function() {
        if ($scope.selected_row < $scope.data.meta.row_total) {
            $scope.selected_row = $scope.selected_row + 1;
        }
    };
    // Go to selected row
    $scope.goto_row_detail = function() {
        if ($scope.selected_row) {
            var pk = $scope.data.table.body[$scope.selected_row - 1].pk;
            $scope.detail(pk);
        }
    };

    $scope.gotourl = function(url) {
        // Jump to new location
        window.location.href = url;
    };

    $scope.detail = function(pk) {
        if ($scope.data.meta.linkedit || $scope.data.meta.show_details) {
            if (!sublist) {
                if ($scope.data.meta.show_details) {
                    // Showing details
                    if ($scope.data.meta.show_modal) {
                        // Show in a modal window
                        modal_manager(
                            $scope,
                            $timeout,
                            $uibModal,
                            $templateCache,
                            $http,
                            $scope);
                        $scope.details(pk);
                    } else {
                        // Show like always
                        $state.go('details' + listid, {'pk': pk});
                    }
                } else {
                    // Edit normally
                    $state.go('formedit' + listid, {'pk': pk});
                }
            } else {
                // Base window
                if ($scope.data.meta.show_details) {
                    $scope.ws = ws + '/' + pk + '/modal';
                } else {
                    $scope.ws = ws + '/' + pk + '/editmodal';
                }

                // Base Window functions
                var functions = function(scope) {};
                var callback = function(scope) {
                    // Close our window
                    if (scope.base_window) {
                        scope.base_window.dismiss('cancel');
                    }
                    $state.go($state.current, {listid: scope.listid});
                    refresh(scope, $timeout, Register, undefined);
                };

                // Start modal window
                openmodal(
                    $scope, $timeout, $uibModal, 'lg', functions, callback);
            }
        }
    };
    // Extra help functions
    $scope.refresh = function() {
        refresh($scope, $timeout, Register, callback);
    };
    $scope.isList = function(obj) {
        return obj instanceof Array;
    };
    $scope.getKey = function(string) {
        return string.split('__')[1];
    };
    $scope.date_change = function(name) {
        var found = false;
        angular.forEach(
            ['second', 'minute', 'hour', 'day', 'month', 'year'],
            function(key) {
                if (!found) {
                    $scope.query[key] = null;
                    if (name == key) {
                        found = true;
                    }
                }
            });
        refresh($scope, $timeout, Register, callback);
    };
    $scope.date_select = function(name, value) {
        $scope.query[name] = value;
        refresh($scope, $timeout, Register, callback);
    };
    $scope.rows_change = function(value) {
        $scope.query.rowsperpage = value;
        refresh($scope, $timeout, Register, callback);
    };
    $scope.page_change = function(value) {
        $scope.query.page = value;
        refresh($scope, $timeout, Register, callback);
    };

    $scope.reset_filter = function() {
        $scope.data.meta.search_filter_button = false;

        $scope.data = undefined;
        // Prepare query
        $scope.query = {
            'listid': listid,
            'elementid': null,
            'search': '',
            'page': 1,
            'rowsperpage': 50,
            'filters': {},
            'ordering': [],
            'year': null,
            'month': null,
            'day': null,
            'hour': null,
            'minute': null,
            'second': null,
            'context': {},
        };
        refresh($scope, $timeout, Register, callback);
    };

    $scope.goto_search = function() {
        $scope.focus.search_box = true;
    };
    $scope.switch_filters = function() {
        $scope.data.meta.search_filter_button =
            !$scope.data.meta.search_filter_button
    };

    $scope.print_excel = function() {
        var url = $scope.data.meta.request.path_info + '?' +
                  $scope.data.meta.request.query_string + '&export=xlsx';
        window.open(url, '_blank');
    };

    // Get details
    $scope.list_modal = function(id) {
        // Base window
        id = String(id);
        $scope.wsbase = ws + '/';

        $scope.ws = $scope.wsbase + id + '/modal';
        $scope.initialbase = $scope.wsbase;

        $scope.id_parent = null;
        //$scope.initialws = $scope.ws;

        var functions = function(scope) {
            scope.init =
                function(id_parent) {
                id = String(id);
                id_parent = String(id_parent);
                if ($scope.id_parent == null) {
                    $scope.id_parent = id_parent;
                }
            }

                // DEPRECATED: 2017-02-14
                scope.createrelationfile =
                    function() {
                var url = $scope.initialbase + $scope.id_parent + '/add'
                $scope.add(url);
            }

                    // DEPRECATED: 2017-02-14
                    scope.removefile = function(id, msg, id_parent) {
                id = String(id);
                id_parent = String(id_parent);
                if ($scope.id_parent == null) {
                    $scope.id_parent = id_parent;
                }
                if (confirm(msg)) {
                    var url = $scope.wsbase + id_parent + '/' + id + '/delete';
                    $scope.ws = $scope.wsbase + id_parent + '/modal';


                    $http.post(url, {}, {})
                        .success(function(answer, stat) {
                            // Check the answer
                            if (stat == 200 || stat == 202) {
                                // Reload details window
                                if ($scope.base_window != undefined) {
                                    $scope.base_window.dismiss('cancel');
                                }
                                $scope.base_reload[0](
                                    $scope.base_reload[1],
                                    $scope.base_reload[2]);
                                // If the request was accepted go back to the
                                // list
                            } else {
                                // Error happened, show an alert
                                console.log('ERROR ' + stat + ': ' + answer)
                                console.log(answer);
                                alert('ERROR ' + stat + ': ' + answer)
                            }
                        })
                        .error(function(data, status, headers, config) {
                            if (cnf_debug) {
                                alert(data);
                            } else {
                                alert(cnf_debug_txt)
                            }
                        });

                    // Base Window functions
                    var functions = function(scope) {};
                    var callback = function(scope) {
                        // scope.cb_window.dismiss('cancel');
                        // scope.cb_reload[0](scope.cb_reload[1]);
                        scope.det_window.dismiss('cancel');
                        scope.det_reload[0](scope.det_reload[1]);
                    };
                    // Start modal window
                    openmodal(
                        $scope, $timeout, $uibModal, 'lg', functions, callback);
                }
            };

            scope.edit = function(id, id_parent) {
                id = String(id);
                id_parent = String(id_parent);
                if ($scope.id_parent == null) {
                    $scope.id_parent = id_parent;
                }
                // Base window
                $scope.ws = $scope.initialbase + id_parent + '/' + id + '/edit';

                // Base Window functions
                var functions = function(scope) {};
                var callback = function(scope) {
                    // Reload list window
                    if ($scope.base_window != undefined) {
                        /*
                        following line is going to be executed in the case this
                        manager is created in a modal window
                        */
                        scope.base_window.dismiss('cancel');
                    }
                    scope.base_reload[0](
                        $scope.base_reload[1], $scope.base_reload[2]);
                    // Reload details window
                    scope.det_window.dismiss('cancel');
                    scope.det_reload[0](scope.det_reload[1]);
                };

                // Start modal window
                openmodal(
                    $scope, $timeout, $uibModal, 'lg', functions, callback);
            };

            // DEPRECATED: 2017-02-14
            // Get details OCR
            scope.details_ocr = function(id) {
                id = String(id);
                // Base window
                $scope.ws = $scope.wsbase + id + '/ocr';
                $scope.initialws = $scope.ws;
                // Base Window functions
                var functions = function(scope) {
                    scope.gotoback = function() {
                        $scope.det_window.dismiss('cancel');
                    };
                };

                // Prepare for refresh
                $scope.det_reload = [scope.details, id];
                $scope.det_window =
                    openmodal($scope, $timeout, $uibModal, 'lg', functions);
            };

            scope.details_view = function(id, $event) {
                // Base window
                $scope.ws = $scope.wsbase + id + '/view';
                $scope.initialws = $scope.ws;
                // Base Window functions
                var functions = function(scope) {
                    scope.gotoback = function() {
                        $scope.det_window.dismiss('cancel');
                    };

                    scope.edit = function(ar) {
                        // Base window
                        $scope.ws = $scope.wsbase + $scope.id_parent + '/' +
                                    id + '/edit';

                        // Base Window functions
                        var functions = function(scope) {};
                        var callback = function(scope) {
                            // Reload list window
                            if ($scope.base_window != undefined) {
                                /*
                                following line is going to be executed in the
                                case this manager is created in a modal window
                                */
                                scope.base_window.dismiss('cancel');
                            }
                            scope.base_reload[0](
                                $scope.base_reload[1], $scope.base_reload[2]);
                            // Reload details window
                            scope.det_window.dismiss('cancel');
                            scope.det_reload[0](
                                scope.det_reload[1], scope.det_reload[2]);
                        };

                        // Start modal window
                        openmodal(
                            $scope,
                            $timeout,
                            $uibModal,
                            'lg',
                            functions,
                            callback);
                    };
                };

                // Prepare for refresh
                $scope.det_reload = [scope.details_view, id, $event];
                $scope.det_window =
                    openmodal($scope, $timeout, $uibModal, 'lg', functions);
                $event.stopPropagation();
            };
            modal_manager(
                $scope, $timeout, $uibModal, $templateCache, $http, $scope);

            scope.addrecord = function() {
                var url = $scope.initialbase + $scope.id_parent + '/addfile'
                $scope.add(url);
            };
            scope.removerecord = function(id, msg, args) {
                // var url = $scope.initialbase+$scope.id_parent+"/addfile"
                var url = $scope.wsbase + '/' + id + '/delete';
                del_item_sublist(id, msg, url, $scope, $http, args);
                //$scope.add(url);
            };
        };
        var callback = function(scope) {
            // scope.cb_reload[0](scope.cb_reload[1]);
        };
        // Prepare for refresh
        $scope.base_reload = [$scope.list_modal, id];
        $scope.base_window = openmodal(
            $scope, $timeout, $uibModal, 'lg', functions);  //, callback);
    };
    // DEPRECATED: 2017-07-04
    $scope.open_details = function(id, id_parent) {
        id = String(id);
        id_parent = String(id_parent);
        $scope.wsbase = ws + '/';
        // Base window
        $scope.ws = $scope.wsbase + id + '/view/True';
        $scope.initialbase = $scope.wsbase + id_parent + '/' + id;

        $scope.initialws = $scope.ws;
        $scope.id_parent = id_parent;
        // Base Window functions
        var functions = function(scope) {
            scope.gotoback = function() {
                $scope.det_window.dismiss('cancel');
            };

            scope.edit = function(ar) {
                // Base window
                $scope.ws = $scope.initialbase + '/edit';

                // Base Window functions
                var functions = function(scope) {};
                var callback = function(scope) {
                    // Reload details window
                    $scope.det_window.dismiss('cancel');
                    $scope.det_reload[0]($scope.det_reload[1]);
                };

                // Start modal window
                openmodal(
                    $scope, $timeout, $uibModal, 'lg', functions, callback);
            };
        };

        // Prepare for refresh
        $scope.det_reload = [$scope.details_view, id, id_parent];
        $scope.det_window =
            openmodal($scope, $timeout, $uibModal, 'lg', functions);
    };

    $scope.switch_order = function(id) {
        if (id) {
            var actual, max, absvalue, sign;
            actual = $scope.data.table.head.ordering[id];
            if (actual == undefined) {
                actual = 0;
            }
            // Find the value and check if it is a quick change
            if (actual > 0) {
                // Invert order, keep the rest
                $scope.data.table.head.ordering[id] = -actual;
            } else {
                // Find the max ordering
                max = 0;
                angular.forEach(
                    $scope.data.table.head.ordering, function(value) {
                        absvalue = Math.abs(value)
                        if (absvalue > max) {
                            max = absvalue;
                        }
                    });

                // If it is a new ordering element, set to max+1
                if (actual == 0) {
                    $scope.data.table.head.ordering[id] = max + 1;
                } else {
                    // The element is going out from the list, recount the list
                    if (actual == max) {
                        // Good luck, this is the last element from the list,
                        // remove ordering and we are done
                        $scope.data.table.head.ordering[id] = 0;
                    } else {
                        // This is an object in the middel of the list recount
                        // the list and remove the object
                        angular.forEach(
                            $scope.data.table.head.ordering,
                            function(value, key) {
                                if (value > 0) {
                                    sign = 1;
                                } else {
                                    sign = -1;
                                }
                                absvalue = Math.abs(value);
                                actual = Math.abs(actual);
                                if (absvalue < actual) {
                                    $scope.data.table.head.ordering[key] =
                                        sign * absvalue;
                                } else if (absvalue > actual) {
                                    $scope.data.table.head.ordering[key] =
                                        sign * (absvalue - 1);
                                }
                            });
                        $scope.data.table.head.ordering[id] = 0;
                    }
                }
            }
            // Refresh
            refresh($scope, $timeout, Register, callback);
        }
    };

    $scope.refreshlist = function(listid) {
        $state.go($state.current, {listid: listid});
        refresh($scope, $timeout, Register, undefined);
    };

    $scope.removerecord = function(id, msg, args) {
        $scope.base_reload = [$scope.refreshlist, $scope.listid, 0];
        var url = ws + '/' + id + '/delete';
        del_item_sublist(id, msg, url, $scope, $http, args);
    };

    // Startup hotkey system
    if (codenerix_hotkeys && hotkeys !== undefined) {
        var hotkeysrv = hotkeys.bindTo($scope);
        hotkeysrv.add(
            {combo: '+', description: 'Add new row', callback: $scope.addnew});
        hotkeysrv.add({
            combo: 'ctrl+up',
            description: 'Select previous row',
            callback: $scope.goto_row_previous
        });
        hotkeysrv.add({
            combo: 'ctrl+down',
            description: 'Select next row',
            callback: $scope.goto_row_next
        });
        hotkeysrv.add({
            combo: 'enter',
            description: 'Go to selected row',
            callback: $scope.goto_row_detail
        });
        hotkeysrv.add({
            combo: 'ctrl+enter',
            description: 'Go to selected row',
            callback: $scope.goto_row_detail
        });
        hotkeysrv.add({
            combo: 'ctrl+right',
            description: 'Go to selected row',
            callback: $scope.goto_row_detail
        });
        hotkeysrv.add(
            {combo: 'r', description: 'Refresh', callback: $scope.refresh});
        hotkeysrv.add({
            combo: 's',
            description: 'Go to search box',
            callback: $scope.goto_search
        });
        hotkeysrv.add({
            combo: 'f',
            description: 'Enable/disable filters',
            callback: $scope.switch_filters
        });
        hotkeysrv.add({
            combo: 'x',
            description: 'Export to Excel',
            callback: $scope.print_excel
        });
    }
    // First query
    refresh($scope, $timeout, Register, callback);
};

function multiadd(
    $scope,
    $rootScope,
    $timeout,
    $http,
    $window,
    $uibModal,
    $state,
    $stateParams,
    $templateCache,
    Register,
    listid,
    ws,
    hotkeys) {
    // Set our own url
    var url = ws + '/add';
    $scope.options = {};

    // Remember http
    $scope.http = $http;

    // Clear cache
    $templateCache.remove(url);

    // Add datetimepicker function
    $scope.onTimeSet =
        function(newDate, oldDate) {
        console.log(newDate);
        console.log(oldDate);
    }

        // Add linked element
        $scope.linked =
            function(
                base_url,
                ngmodel,
                appname,
                modelname,
                formobj,
                formname,
                id,
                wsbaseurl) {
        inlinked(
            $scope,
            $rootScope,
            $http,
            $window,
            $uibModal,
            $state,
            $stateParams,
            $templateCache,
            Register,
            ws,
            listid,
            ngmodel,
            base_url,
            appname,
            modelname,
            formobj,
            formname,
            id,
            wsbaseurl,
            $timeout);
    }

    // Set dynamic foreign fields controller functions
    dynamic_fields($scope);
    angularmaterialchip($scope);
    if (typeof (codenerix_extensions) != 'undefined') {
        codenerix_extensions($scope, $timeout);
    }

    // Set dynamic scope filling with subscribers
    $scope.subscribers = function(subsjsb64) {
        subscribers_worker($scope, subsjsb64)
    };

    // Go to list
    $scope.gotoback = function() {
        $state.go('list' + listid);
    };

    // Update this element
    $scope.submit = function(
        form, next, target, nlistid, nurl, nform, nnext, naction) {
        if (form instanceof KeyboardEvent) {
            form = $scope[$scope.form_name];
            next = 'list';
        }
        if (typeof (nlistid) == 'undefined') {
            var ulistid = listid;
        } else {
            var ulistid = nlistid;
        }
        if (typeof (nurl) == 'undefined') {
            var uurl = url;
        } else {
            var uurl = nurl;
        }
        if (typeof (nform) == 'undefined') {
            var uform = form;
        } else {
            var uform = nform;
        }
        if (typeof (nnext) == 'undefined') {
            var unext = next;
        } else {
            var unext = nnext;
        }
        if (typeof (naction) == 'undefined') {
            var uaction = 'add';
        } else {
            var uaction = naction;
        }
        if ((target == 'submit') || (typeof (target) == 'undefined')) {
            formsubmit(
                $scope,
                $rootScope,
                $http,
                $window,
                $state,
                $templateCache,
                null,
                ulistid,
                uurl,
                uform,
                unext,
                uaction);
        } else {
            $scope[target](ulistid, uurl, uform, unext, uaction);
        }
    };

    $scope.gotourl = function(url) {
        // Jump to new location
        window.location.href = url;
    };

    var fields = [];
    $scope.preUpdateField = function(field_o, field_d) {
        fields[field_o] = $scope[field_o];
        fields[field_d] = $scope[field_d];
    };
    $scope.UpdateField = function(field_o, field_d) {
        if (typeof ($scope[field_d]) == 'undefined' || $scope[field_d] == '' ||
            fields[field_o] == fields[field_d]) {
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
        if (duration != false) {
            $scope.ArrivalForm.ArrivalForm_date = duration;
            $scope.ArrivalForm.ArrivalForm_date_time = duration_time;
        }
    };
    // DEPRECATED: 2017-02-14
    // change estimate date (departure and arrival)
    $scope.changeEstimatedDateFlight = function() {
        changeEstimatedDateFlight($scope);
    };
    // DEPRECATED: 2017-02-14
    $scope.changeActualDateFlight = function() {
        changeActualDateFlight($scope);
    };

    // Startup hotkey system
    if (codenerix_hotkeys && hotkeys !== undefined) {
        var hotkeysrv = hotkeys.bindTo($scope);
        hotkeysrv.add({
            combo: 'ctrl+left',
            description: 'Go back',
            allowIn: ['INPUT', 'SELECT', 'TEXTAREA'],
            callback: $scope.gotoback
        });
        hotkeysrv.add({
            combo: 'ctrl+enter',
            description: 'Save',
            allowIn: ['INPUT', 'SELECT', 'TEXTAREA'],
            callback: $scope.submit
        });
    }
};

function multidetails(
    $scope,
    $rootScope,
    $timeout,
    $http,
    $window,
    $uibModal,
    $state,
    $stateParams,
    $templateCache,
    Register,
    listid,
    ws,
    hotkeys) {
    // Set our own url
    var url = ws + '/' + $stateParams.pk;

    // Clear cache
    $templateCache.remove(url);

    // Check if autostate has been disabled by the caller
    if (typeof (tabs_js) != 'undefined' && tabs_js.length != 0) {
        $state.go('details0.sublist' + listid + '.rows');
    }

    // Go to list
    $scope.gotoback = function() {
        $state.go('list' + listid);
    };

    // Delete this element
    $scope.edit = function() {
        // Clear cache
        $templateCache.remove(url);
        // Go to edit state
        $state.go('formedit' + listid, {pk: $stateParams.pk});
    };

    $scope.msg = function(msg) {
        alert(msg);
    };

    $scope.gotourl = function(url) {
        // Jump to new location
        window.location.href = url;
    };

    // Delete this element
    $scope.delete = function(msg) {
        if (confirm(msg)) {
            // Clear cache
            $templateCache.remove(url);
            // User confirmed
            var url = ws + '/' + $stateParams.pk + '/delete';
            $http.post(url, {}, {})
                .success(function(answer, stat) {
                    // Check the answer
                    if (stat == 202) {
                        // If the request was accepted go back to the list
                        $state.go('list' + listid);
                    } else {
                        // Error happened, show an alert
                        console.log('ERROR ' + stat + ': ' + answer)
                        alert('ERROR ' + stat + ': ' + answer)
                    }
                })
                .error(function(data, status, headers, config) {
                    if (cnf_debug) {
                        alert(data);
                    } else {
                        alert(cnf_debug_txt)
                    }
                });
        }
    };

    // Set dynamic scope filling with subscriber
    $scope.subscribers = function(subsjsb64) {
        subscribers_worker($scope, subsjsb64)
    };

    // Startup hotkey system
    if (codenerix_hotkeys && hotkeys !== undefined) {
        var hotkeysrv = hotkeys.bindTo($scope);
        hotkeysrv.add({
            combo: 'ctrl+left',
            description: 'Go back',
            allowIn: ['INPUT', 'SELECT', 'TEXTAREA'],
            callback: $scope.gotoback
        });
        hotkeysrv.add({combo: 'e', description: 'Edit', callback: $scope.edit});
    }
};

function multiedit(
    $scope,
    $rootScope,
    $timeout,
    $http,
    $window,
    $uibModal,
    $state,
    $stateParams,
    $templateCache,
    Register,
    listid,
    ws,
    hotkeys) {
    // Set our own url
    var url = ws + '/' + $stateParams.pk + '/edit';
    $scope.options = {};

    // Rembmer http
    $scope.http = $http;

    // Clear cache
    $templateCache.remove(url);

    // Add linked element
    $scope.linked =
        function(
            base_url,
            ngmodel,
            appname,
            modelname,
            formobj,
            formname,
            id,
            wsbaseurl) {
        inlinked(
            $scope,
            $rootScope,
            $http,
            $window,
            $uibModal,
            $state,
            $stateParams,
            $templateCache,
            Register,
            ws,
            listid,
            ngmodel,
            base_url,
            appname,
            modelname,
            formobj,
            formname,
            id,
            wsbaseurl,
            $timeout);
    }

    // Set dynamic foreign fields controller functions
    dynamic_fields($scope);
    angularmaterialchip($scope);
    if (typeof (codenerix_extensions) != 'undefined') {
        codenerix_extensions($scope, $timeout);
    }

    // Set dynamic scope filling with subscribers
    $scope.subscribers = function(subsjsb64) {
        subscribers_worker($scope, subsjsb64)
    };

    // Go to list
    $scope.gotoback = function() {
        // Clear cache
        $templateCache.remove(url);
        // Go to list
        $state.go('list' + listid);
        // $state.go('details'+listid,{pk:$stateParams.pk});
    };

    $scope.gotourl = function(url) {
        // Jump to new location
        window.location.href = url;
    };

    // Go to details
    $scope.gotodetails = function() {
        // Clear cache
        $templateCache.remove(url);
        // Go to list
        $state.go('details' + listid, {pk: $stateParams.pk});
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
        // changeDurationFlight($scope);
        var duration;
        var duration_time;
        var duration_tuple = changeDurationFlightC($scope);
        duration = duration_tuple[0];
        duration_time = duration_tuple[1];
        if (duration != false && typeof ($scope.ArrivalForm) != 'undefined') {
            $scope.ArrivalForm.ArrivalForm_date = duration;
            $scope.ArrivalForm.ArrivalForm_date_time = duration_time;
        }
    };
    // DEPRECATED: 2017-02-14
    $scope.init = function() {
        angular.element(document).ready(function() {
            setTimeout(function() {
                $scope.changeEstimatedDateFlight();
            }, 1);
        });
    };
    // DEPRECATED: 2017-02-14
    //$scope.init();
    // change estimate date (departure and arrival)
    $scope.changeEstimatedDateFlight = function() {
        changeEstimatedDateFlight($scope);
    };
    // DEPRECATED: 2017-02-14
    $scope.changeEstimatedDateFlight = function() {
        changeActualDateFlight($scope);
    };
    // DEPRECATED: 2017-02-14
    $scope.changeActualDateFlight = function() {
        changeActualDateFlight($scope);
    };

    $scope.msg =
        function(msg) {
        alert(msg);
    }
        // Delete this element
        $scope.delete = function(msg, target, nurl) {
        if (typeof (nurl) == 'undefined') {
            var uurl = url;
        } else {
            var uurl = nurl;
        }
        if ((target == 'delete') || (typeof (target) == 'undefined')) {
            if (confirm(msg)) {
                // Clear cache
                $templateCache.remove(uurl);
                // Get url
                if (typeof (nurl) == 'undefined') {
                    var uurl = ws + '/' + $stateParams.pk + '/delete';
                } else {
                    var uurl = nurl;
                }
                $http.post(uurl, {}, {})
                    .success(function(answer, stat) {
                        // Check the answer
                        if (stat == 202) {
                            // Call to call back before anything else
                            var next = 'list';
                            if (typeof ($scope.delete_callback) !=
                                'undefined') {
                                if (codenerix_debug) {
                                    console.log(
                                        'Delete Callback found, calling it back!');
                                }
                                next = $scope.delete_callback(
                                    listid,
                                    uurl,
                                    $stateParams.pk,
                                    next,
                                    answer,
                                    stat);
                                if (codenerix_debug) {
                                    console.log(
                                        'Delete callback said next state is \'' +
                                        next + '\'');
                                }
                            }

                            if (next == 'list') {
                                // If the request was accepted go back to the
                                // list
                                $state.go('list' + listid);
                            } else if (next == 'none') {
                                if (codenerix_debug) {
                                    console.warn(
                                        'Automatic destination state has been avoided by programmer\'s request!');
                                }
                            } else {
                                console.error(
                                    'Unknown destination requested by the programmer, I don\'t understand next=\'' +
                                    next + '\'');
                            }
                        } else {
                            // Error happened, show an alert
                            console.log('ERROR ' + stat + ': ' + answer)
                            alert('ERROR ' + stat + ': ' + answer)
                        }
                    })
                    .error(function(data, status, headers, config) {
                        if (cnf_debug) {
                            alert(data);
                        } else {
                            alert(cnf_debug_txt)
                        }
                    });
            }
        } else {
            $scope[target](msg, $stateParams.pk);
        }
    };

    // Update this element
    $scope.submit = function(
        form, next, target, nlistid, nurl, nform, nnext, naction) {
        if (form instanceof KeyboardEvent) {
            form = $scope[$scope.form_name];
            next = 'list';
        }
        if (typeof (nlistid) == 'undefined') {
            var ulistid = listid;
        } else {
            var ulistid = nlistid;
        }
        if (typeof (nurl) == 'undefined') {
            var uurl = url;
        } else {
            var uurl = nurl;
        }
        if (typeof (nform) == 'undefined') {
            var uform = form;
        } else {
            var uform = nform;
        }
        if (typeof (nnext) == 'undefined') {
            var unext = next;
        } else {
            var unext = nnext;
        }
        if (typeof (naction) == 'undefined') {
            var uaction = 'edit';
        } else {
            var uaction = naction;
        }
        if ((target == 'submit') || (typeof (target) == 'undefined')) {
            formsubmit(
                $scope,
                $rootScope,
                $http,
                $window,
                $state,
                $templateCache,
                null,
                ulistid,
                uurl,
                uform,
                unext,
                uaction);
        } else {
            $scope[target](
                ulistid, uurl, uform, unext, uaction, $stateParams.pk);
        }
    };

    var fields = [];
    $scope.preUpdateField = function(field_o, field_d) {
        fields[field_o] = $scope[field_o];
        fields[field_d] = $scope[field_d];
    };
    $scope.UpdateField = function(field_o, field_d) {
        if (typeof ($scope[field_d]) == 'undefined' || $scope[field_d] == '' ||
            fields[field_o] == fields[field_d]) {
            $scope[field_d] = $scope[field_o];
        }
        fields[field_o] = $scope[field_o];
        fields[field_d] = $scope[field_d];
    };

    // Startup hotkey system
    if (codenerix_hotkeys && hotkeys !== undefined) {
        var hotkeysrv = hotkeys.bindTo($scope);
        hotkeysrv.add({
            combo: 'ctrl+left',
            description: 'Go back',
            allowIn: ['INPUT', 'SELECT', 'TEXTAREA'],
            callback: $scope.gotoback
        });
        hotkeysrv.add({
            combo: 'ctrl+enter',
            description: 'Save',
            allowIn: ['INPUT', 'SELECT', 'TEXTAREA'],
            callback: $scope.submit
        });
    }
};

// DEPRECATED: 2017-02-14
// calc date arrival and duration
// change duration
function changeDurationFlightC($scope) {
    if ($scope.FlightForm_status != flightForm_status_takeof) {
        if (typeof ($scope.FlightForm) == 'undefined') {
            var duration = $scope.FlightFormConfirm.FlightFormConfirm_duration;
        } else {
            var duration = $scope.FlightForm.FlightForm_duration;
        }
        if (typeof ($scope.FlightForm) != 'undefined' &&
            typeof ($scope.FlightForm.FlightForm_departure_time) !=
                'undefined' &&
            typeof ($scope.FlightForm.FlightForm_departure_time_time) !=
                'undefined' &&
            $scope.FlightForm.FlightForm_departure_time != '' &&
            $scope.FlightForm.FlightForm_departure_time_time != '' &&
            duration != '' && typeof (duration) != 'undefined') {
            var fecha = $scope.FlightForm.FlightForm_departure_time.split('-');
            var hora_int = $scope.FlightForm.FlightForm_departure_time_time;
            var hora = [];
            if (typeof (hora_int) != 'undefined') {
                if (hora_int.length == 3) {
                    hora.push(hora_int[0]);
                    hora.push(hora_int.substring(1, 3));
                } else {
                    hora.push(hora_int.substring(0, 2));
                    hora.push(hora_int.substring(2, 4));
                }
            }

            var arrival = new Date(
                fecha[0],
                fecha[1] - 1,
                fecha[2],
                hora[0],
                parseInt(hora[1]) + parseInt(duration));
            var f = arrival.getFullYear() + '-' +
                    ('0' + (arrival.getMonth() + 1)).slice(-2) + '-' +
                    ('0' + arrival.getDate()).slice(-2);
            var h = ('0' + arrival.getHours()).slice(-2) + '' +
                    ('0' + arrival.getMinutes()).slice(-2);
            return [f, h];

        } else if (
            typeof ($scope.DepartureForm) != 'undefined' &&
            typeof ($scope.DepartureForm.DepartureForm_date) != 'undefined' &&
            $scope.DepartureForm.DepartureForm_date != '' && duration != '' &&
            typeof (duration) != 'undefined') {
            var fecha = $scope.DepartureForm.DepartureForm_date.split('-');
            var hora_int = $scope.DepartureForm.DepartureForm_date_time;
            var hora = [];
            if (typeof (hora_int) != 'undefined') {
                if (hora_int.length == 3) {
                    hora.push(hora_int[0]);
                    hora.push(hora_int.substring(1, 3));
                } else {
                    hora.push(hora_int.substring(0, 2));
                    hora.push(hora_int.substring(2, 4));
                }
            }

            var arrival = new Date(
                fecha[0],
                fecha[1] - 1,
                fecha[2],
                hora[0],
                parseInt(hora[1]) + parseInt(duration));
            var f = arrival.getFullYear() + '-' +
                    ('0' + (arrival.getMonth() + 1)).slice(-2) + '-' +
                    ('0' + arrival.getDate()).slice(-2);
            var h = ('0' + arrival.getHours()).slice(-2) + '' +
                    ('0' + arrival.getMinutes()).slice(-2);
            return [f, h];
            // En Chrome y IE no funciona la siguiente linea por culpa de
            // toLocaleFormat
            // return [arrival.toLocaleFormat("%Y-%m-%d"),
            // arrival.toLocaleFormat("%H%M")];
        } else {
            return [false, false];
        }
    }
};

// DEPRECATED: 2017-02-14
// change estimate date (departure and arrival)
function changeEstimatedDateFlight($scope) {
    if ($scope.FlightForm_status != flightForm_status_takeof) {
        if (typeof ($scope.ArrivalForm) != 'undefined' &&
            typeof ($scope.DepartureForm) != 'undefined' &&
            typeof ($scope.DepartureForm.DepartureForm_date) != 'undefined' &&
            typeof ($scope.ArrivalForm.ArrivalForm_date) != 'undefined' &&
            $scope.DepartureForm.DepartureForm_date != '' &&
            $scope.ArrivalForm.ArrivalForm_date != '') {
            var div = $scope.DepartureForm.DepartureForm_date;
            var fecha = div.split('-');
            var hora_int = $scope.DepartureForm.DepartureForm_date_time;
            var hora = [];
            if (typeof (hora_int) != 'undefined') {
                if (hora_int.length == 3) {
                    hora.push(hora_int[0]);
                    hora.push(hora_int.substring(1, 3));
                } else {
                    hora.push(hora_int.substring(0, 2));
                    hora.push(hora_int.substring(2, 4));
                }
                var depa = new Date(
                    fecha[0], fecha[1] - 1, fecha[2], hora[0], hora[1]);

                div = $scope.ArrivalForm.ArrivalForm_date;
                hora_int = $scope.ArrivalForm.ArrivalForm_date_time;

                if (typeof (hora_int) != 'undefined') {
                    fecha = div.split('-');
                    var hora = [];
                    if (hora_int.length == 3) {
                        hora.push(hora_int[0]);
                        hora.push(hora_int.substring(1, 3));
                    } else {
                        hora.push(hora_int.substring(0, 2));
                        hora.push(hora_int.substring(2, 4));
                    }
                    var arr = new Date(
                        fecha[0], fecha[1] - 1, fecha[2], hora[0], hora[1]);
                    var duration = (arr.getTime() / 1000 / 60) -
                                   (depa.getTime() / 1000 / 60);
                    if (typeof ($scope.FlightForm) == 'undefined') {
                        $scope.FlightFormConfirm.FlightFormConfirm_duration =
                            duration;
                    } else {
                        $scope.FlightForm.FlightForm_duration = duration;
                    }
                }
            }
        }
    }
};

function multisublist($scope, $uibModal, $templateCache, $http, $timeout) {
    modal_manager($scope, $timeout, $uibModal, $templateCache, $http, $scope);

    $scope.reload = undefined;
    $scope.onClickTab = function(url) {
        $templateCache.remove(url);
        $scope.currentTab = url;
        $scope.ws = url;
        $scope.wsbase = url + '/';

        modal_manager(
            $scope, $timeout, $uibModal, $templateCache, $http, $scope);

        $scope.base_reload = [$scope.refreshTab, url];
    };

    $scope.refreshTab = function(url) {
        /*
        function designed to make possible content tabs can be
        refreshed. the refresh is made with the following tab change
        simulation. but it does not work if $timeout is not used. it
        could be due to a unknown angular behaviour.
        */
        $templateCache.remove(url);
        $scope.currentTab = '';
        $timeout(function() {
            $scope.currentTab = url;
        }, 1);
    };

    $scope.addrecord = function(url) {
        $scope.add(url);
    };

    $scope.gotourl = function(url) {
        // Jump to new location
        window.location.href = url;
    };

    $scope.removerecord = function(id, msg, args) {
        // var url = $scope.initialbase+$scope.id_parent+"/addfile"
        var url = $scope.wsbase + id + '/delete';
        del_item_sublist(id, msg, url, $scope, $http, args);
        //$scope.add(url);
    };

    // DEPRECATED: 2017-02-14
    $scope.createpdf = function(type) {
        var url = '/documents/createpdf';
        var files = [];
        $('input[name=checkfile]:checked').each(function() {
            files.push($(this).val());
        });
        return false;
        /*
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
                                    reload1 =
        $(this).attr("ng-click").split("(")[1].split(")")[0].replace(/'/g, "");
                                    $(this).addClass('active');
                                }else{
                                    reload2 =
        $(this).attr("ng-click").split("(")[1].split(")")[0].replace(/'/g, "");
                                    $(this).removeClass('active')
                                }
                                $scope.$parent.refreshTab(reload2);
                                $scope.$parent.refreshTab(reload1);
                            });
                            alert(answer.msg);

                        }else{
                            $("#alertclipboard_ok").html('').hide();
                            $("#alertclipboard_error").html(answer.msg).show();
                            var reload =
        $("li.ng-isolate-scope.active").attr("ng-click").split("(")[1].split(")")[0].replace(/'/g,
        ""); $scope.$parent.refreshTab(reload); alert(answer.msg);
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
        */
    };
};

// Function that prints whatever URL you give to it
function printURL(xthis, url) {
    if ('_printIframe' in xthis) {
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
};

function angularmaterialchip(scope) {
    /**
     * Return the proper object when the append is called.
     */
    function transformChip(chip) {
        // If it is an object, it's already a known chip
        if (angular.isObject(chip)) {
            return chip;
        }
        // Otherwise, create a new one
        return {
            label: chip, id: 0
        }
    }

    /**
     * Search for elements.
     */
    function querySearch(query, items, id) {
        if (scope.amc_items == undefined) {
            scope.amc_items = [];
        }
        if (scope.amc_select[items] == undefined) {
            scope.amc_select[items] = [];
        }
        if (scope.amc_items[items] == undefined) {
            scope.amc_items[items] = {};
        }
        if (query == '*') {
            var results = scope.amc_items[items].slice(0, 50);
        } else {
            var results =
                query ? scope.amc_items[items].filter(createFilterFor(query)) :
                        [];
        }
        return results;
    }

    /**
     * Create filter function for a query string
     */
    function createFilterFor(query) {
        var lowercaseQuery = angular.lowercase(query);
        return function filterFn(option) {
            var results =
                (angular.lowercase(option.label).indexOf(lowercaseQuery) >=
                 0) ||
                (option.id == lowercaseQuery);
            return results;
            // return (angular.lowercase(option.label).indexOf(lowercaseQuery)
            // === 0) || (option.id == lowercaseQuery);
        };
    }

    // Link elements
    scope.amc_querySearch = querySearch;
    scope.amc_autocompleteDemoRequireMatch = true;
    scope.amc_transformChip = transformChip;

    // options values
    scope.amc_items = {};
    // options seleted
    scope.amc_select = {};
}
