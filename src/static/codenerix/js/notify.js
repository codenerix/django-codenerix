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

// Angular codenerix Controllers
angular.module('codenerixNotify', ['ngResource'])

.factory('Notifications', ['$resource', function($resource){
    return $resource('/alarmspopups/:pk/:action', { pk:null, action:null },{
        query:{ method: "GET", params: {}, isArray: false, ignoreLoadingBar: true },
        get:{ method: "GET", params: { pk:'@pk', action:'@action' }, isArray: false, ignoreLoadingBar: true },
    }); 
}])

.controller('AlarmsCtrl', ['$scope', '$rootScope', '$timeout', '$filter', 'Notifications',
    function($scope, $rootScope, $timeout, $filter, Notifications) {
        $scope.onscreen = [];
        $scope.pubdata = {};
        
        // HIDE
        $scope.notify_hide = function (id,kind) {
            // console.log("AngularJS NOTIFY: hide "+id);
            Notifications.get({pk:id,action:"hide"});
        };
        // YES
        $scope.notify_yes  = function (id,kind) {
            // console.log("AngularJS NOTIFY: yes "+id);
            Notifications.get({pk:id,action:"yes"});
        };
        // NO
        $scope.notify_no   = function (id,kind) {
            // console.log("AngularJS NOTIFY: no "+id);
            Notifications.get({pk:id,action:"no"});
        };
        // ALL
        $scope.notify_showall = function() {
            // console.log("AngularJS NOTIFY: no "+id);
            Notifications.get({action:"all"});
            location.reload();
        };
        
        (function tick() {
//            if (!withfocus) {
//                    // Set a new timeout in 1 seconds because we don't have focus and we will not do anything
//                    $timeout(tick,cnf_alarms_quickloop);
//            } else {
                $scope.data = Notifications.query({}, function() {
                    // Everything went ok
                    $scope.connectionlost=0;
                    // Update our public structure here to avoid flicking the screen values
                    $scope.pubdata = $scope.data;
                    // Show alerts that are waiting to be shown and we haven't shown yet
                    if ($scope.pubdata.head != undefined && $scope.pubdata.head.order != undefined){
                        angular.forEach( $scope.pubdata.head.order , function ( alarm_id ) {
                            var found=false;
                            var alarm=$scope.pubdata.body[alarm_id];
                            angular.forEach( $scope.onscreen , function ( screen_id ) {
                                if (screen_id==alarm_id) {
                                    found=true;
                                    return;
                                }
                            });
                            if (found) {
                                // The alarm was already in the screen
                                if ((alarm==null) || (!alarm.popup)) {
                                    // Remove alert
                                    $scope.onscreen=$filter('filter')($scope.onscreen, '!'+alarm_id);
                                    // Close alert
                                    inotify_close(alarm_id);
                                } else {
                                    // Remove alert
                                    $scope.onscreen=$filter('filter')($scope.onscreen, '!'+alarm_id);
                                    // Close alert
                                    inotify_close(alarm_id);
                                    
                                    // Decide alertdate
                                    if (alarm.alertdate == null ) {
                                        var alertdate="";
                                    } else {
                                        var alertdate = alarm.alertdate+" ";
                                    }
                                    // Kind compatibility
                                    if (alarm.kind===undefined) {
                                        alarm.kind='';
                                    }
                                    // Open alert
                                    inotify(notify_msg(alarm, alertdate, alarm_id), alarm,alarm_id, true);
                                    
                                    // If no style was selected, apply general one
                                    if (alarm.style=='custom') {
                                        // Calculate font color
                                        var yiqcolor=getContrastYIQ(alarm.color.substr(1))
                                        // Set color
                                        $('#notify'+alarm_id).parent().parent().css({
                                            "border-color":"#FFFFFF",
                                            "background-color":alarm.color,
                                            "color":yiqcolor,
                                            "font-size":"11px",
                                        });
                                    }
                                    // Add alert
                                    $scope.onscreen.push(alarm_id);
                                }
                            } else {
                                // The alarm is not in the screen
                                if ((alarm!=null) && (alarm.popup)) {
                                    // Decide alertdate
                                    if (alarm.alertdate == null ) {
                                        var alertdate="";
                                    } else {
                                        var alertdate = alarm.alertdate+" ";
                                    }
                                    // Kind compatibility
                                    if (alarm.kind===undefined) {
                                        alarm.kind='';
                                    }
                                    // Open alert
                                    inotify(notify_msg(alarm, alertdate, alarm_id), alarm,alarm_id, true);
                                    
                                    // If no style was selected, apply general one
                                    if (alarm.style=='custom') {
                                        // Calculate font color
                                        var yiqcolor=getContrastYIQ(alarm.color.substr(1))
                                        // Set color
                                        $('#notify'+alarm_id).parent().parent().css({
                                            "border-color":"#FFFFFF",
                                            "background-color":alarm.color,
                                            "color":yiqcolor,
                                            "font-size":"11px",
                                        });
                                    }
                                    // Add alert
                                    $scope.onscreen.push(alarm_id);
                                }
                            }
                        });
                    }
                        
                    // Remove from the screen all alarms that dissapeared
                    angular.forEach( $scope.onscreen , function ( screen_id ) {
                        var found=false;
                        angular.forEach( $scope.pubdata.head.order , function ( alarm_id ) {
                            if (screen_id==alarm_id) {
                                found=true;
                                return;
                            }
                        });
                        if (!found) {
                            // Delete old alerts from the screen
                            inotify_close(screen_id);
                        }
                    });
                    
                    // Refresh now
                    $rootScope.now = (new Date).getTime();
                    $rootScope.lastconnection = $rootScope.now;
                    // Set a new timeout in 10 seconds
                    $timeout(tick,cnf_alarms_looptime);
                }, function () {
                    // Refresh now
                    $rootScope.now = (new Date).getTime();
                    $timeout(tick,cnf_alarms_errorloop);
                });
//            }
        })();
        
        // Cancel timeout on page changes
        $scope.$on('$destroy', function(){
            if (angular.isDefined(promise)) {
                $timeout.cancel(promise);
                promise = undefined;
            }
        });
    }
]);
