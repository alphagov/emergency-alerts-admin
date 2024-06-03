// Polyfill holes in JSDOM
require('./polyfills.js');

// set up jQuery
window.jQuery = require('jquery');
$ = window.jQuery;

// load module code
require('../../../app/assets/javascripts/modules.js');

const mockDate = new Date();
window.logged_in_at = mockDate;
