// Polyfill holes in JSDOM
require('./polyfills.js');

// set up jQuery
window.jQuery = require('jquery');
$ = window.jQuery;

// load module code
require('../../../app/assets/javascripts/modules.js');

const mockDate = new Date();
window.logged_in_at = mockDate;

inactivity_mins = 0.8;
inactivity_warning_mins = 0.5;
inactivity_warning_duration = 0.5;
expiry_warning_mins = 1.5;
permanent_session_lifetime = 2;
