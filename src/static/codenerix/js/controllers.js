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
angular.module('codenerixControllers', [])

// List Controllers
.controller('ListCtrl', ['$scope', '$rootScope', '$timeout', '$location', '$uibModal', '$templateCache', '$http', '$state', 'Register', 'ListMemory',
    function($scope, $rootScope, $timeout, $location, $uibModal, $templateCache, $http, $state, Register, ListMemory) {
        if (ws_entry_point==undefined) { ws_entry_point=""; }
        multilist($scope, $rootScope, $timeout, $location, $uibModal, $templateCache, $http, $state, Register, ListMemory, 0, "/"+ws_entry_point);
    }
])
.controller('DetailsCtrl', ['$scope', '$rootScope', '$timeout', '$http', '$window', '$uibModal', '$state', '$stateParams', '$templateCache', 'Register',
    function($scope, $rootScope, $timeout, $http, $window, $uibModal, $state, $stateParams, $templateCache, Register) {
        if (ws_entry_point==undefined) { ws_entry_point=""; }
        multidetails($scope, $rootScope, $timeout, $http, $window, $uibModal, $state, $stateParams, $templateCache, Register, 0, "/"+ws_entry_point);
    }
])
.controller('FormAddCtrl', ['$scope', '$rootScope', '$timeout', '$http', '$window', '$uibModal', '$state', '$stateParams', '$templateCache', 'Register',
    function ($scope, $rootScope, $timeout, $http, $window, $uibModal, $state, $stateParams, $templateCache, Register) {
        if (ws_entry_point==undefined) { ws_entry_point=""; }
        $scope.options = [];
        multiadd($scope, $rootScope, $timeout, $http, $window, $uibModal, $state, $stateParams, $templateCache, Register, 0, "/"+ws_entry_point);
    }
])
.controller('FormEditCtrl', ['$scope', '$rootScope', '$timeout', '$http', '$window', '$uibModal', '$state', '$stateParams', '$templateCache', 'Register',
    function($scope, $rootScope, $timeout, $http, $window, $uibModal, $state, $stateParams, $templateCache, Register) {
        if (ws_entry_point==undefined) { ws_entry_point=""; }
        $scope.options = [];
        multiedit($scope, $rootScope, $timeout, $http, $window, $uibModal, $state, $stateParams, $templateCache, Register, 0, "/"+ws_entry_point);
    }
])
.controller('AlarmsCtrl', ['$scope', '$rootScope', '$timeout', '$location', '$uibModal', '$templateCache', '$http', '$state', 'Register', 'ListMemory',
    function($scope, $rootScope, $timeout, $location, $uibModal, $templateCache, $http, $state, Register, ListMemory) {
        if (ws_entry_point==undefined) { ws_entry_point=""; }
        multilist($scope, $rootScope, $timeout, $location, $uibModal, $templateCache, $http, $state, Register, ListMemory, 0, "/"+ws_entry_point);
    }
])
.controller('SubListCtrl', ['$scope', '$rootScope', '$timeout', '$location', '$uibModal', '$templateCache', '$http', '$state', 'Register', 'ListMemory',
    function($scope, $rootScope, $timeout, $location, $uibModal, $templateCache, $http, $state, Register, ListMemory) {
        if (ws_entry_point==undefined) { ws_entry_point=""; }
        var listid=$state.params.listid;
        if (listid!='') {
            if (CDNX_tabsref==undefined) {
                angular.forEach($scope.tabs_autorender, function(value,key) {
                    $scope.tabs_autorender['t'+key]=false;
                });
                $scope.tabs_autorender['t'+$scope.tabsref[listid]]=true;
                CDNX_tabsref=$scope.tabsref;
            }
            $state.go('details0.sublist'+listid+'.rows',{'listid':listid});
            var register = angular.injector(['codenerixInlineServices']).get('Register'+listid);
            multilist($scope, $rootScope, $timeout, $location, $uibModal, $templateCache, $http, $state, register, ListMemory, listid, subws_entry_point[listid], undefined, true);
        } else {
            // Activate autorender tabs
            angular.forEach(tabs_js, function(tab, i){
                if (tab.auto_open) {
                    $state.go('details0.sublist'+i+'.rows',{'listid':i});
                    return;
                }
            });
        }
    }

])
.controller("SubListStaticCtrl", ["$scope", "$uibModal","$templateCache", "$http", "$timeout","$state", 
    function($scope, $uibModal, $templateCache, $http, $timeout, $state) {
        multisublist($scope, $uibModal, $templateCache, $http, $timeout);
        // Activate non-autorender tabs
        angular.forEach(tabs_js, function(tab, i){
            if (!tab.auto) {
                $state.go('details0.sublist'+i+'.rows',{'listid':i});
                return;
            }
        });
    }
]);
var CDNX_tabsref = undefined;
