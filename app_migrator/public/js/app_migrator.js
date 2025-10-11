// App Migrator - Frontend JavaScript
// This file contains frontend scripts for the App Migrator application

frappe.provide('app_migrator');

// App initialization
app_migrator.init = function() {
    console.log('App Migrator v5.0.0 loaded');
};

// Initialize on page load
$(document).ready(function() {
    app_migrator.init();
});
