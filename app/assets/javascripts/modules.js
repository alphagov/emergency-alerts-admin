(function (global) {
  'use strict';

  var $ = global.jQuery;
  var GOVUK = global.GOVUK || {};
  GOVUK.EmergencyAlertsModules = GOVUK.EmergencyAlertsModules || {};

  GOVUK.emergencyAlertsModules = {
    find: function (container) {
      container = container || $('body');

      var modules;
      var moduleSelector = '[data-emergency-alerts-module]';

      modules = container.find(moduleSelector);

      // Container could be a module too
      if (container.is(moduleSelector)) {
        modules = modules.add(container);
      }

      return modules;
    },

    start: function (container) {
      var modules = this.find(container);

      for (var i = 0, l = modules.length; i < l; i++) {
        var module;
        var element = $(modules[i]);
        var type = camelCaseAndCapitalise(element.data('emergencyAlertsModule'));
        var started = element.data('module-started');

        if (typeof GOVUK.EmergencyAlertsModules[type] === 'function' && !started) {
          module = new GOVUK.EmergencyAlertsModules[type]();
          module.start(element);
          element.data('module-started', true);
        }
      }

      // eg selectable-table to SelectableTable
      function camelCaseAndCapitalise (string) {
        return capitaliseFirstLetter(camelCase(string));
      }

      // http://stackoverflow.com/questions/6660977/convert-hyphens-to-camel-case-camelcase
      function camelCase (string) {
        return string.replace(/-([a-z])/g, function (g) {
          return g.charAt(1).toUpperCase();
        });
      }

      // http://stackoverflow.com/questions/1026069/capitalize-the-first-letter-of-string-in-javascript
      function capitaliseFirstLetter (string) {
        return string.charAt(0).toUpperCase() + string.slice(1);
      }
    }
  };

  global.GOVUK = GOVUK;
})(window);
