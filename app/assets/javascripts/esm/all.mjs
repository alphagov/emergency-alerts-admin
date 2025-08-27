// JS Module used to combine all the JS modules used in the application into a single entry point,
// a bit like `app/__init__` in the Flask app.
//
// When processed by a bundler, this is turned into a Immediately Invoked Function Expression (IIFE)
// The IIFE format allows it to run in browsers that don't support JS Modules.
//
// Exported items will be added to the window.GOVUK namespace.
// For example, `export { Frontend }` will assign `Frontend` to `window.Frontend`

// GOVUK Frontend modules
import { createAll, Header, PasswordInput, Button, Radios, ErrorSummary, SkipLink, Tabs } from 'govuk-frontend';

// Modules from 3rd party vendors
import morphdom from 'morphdom';
import {differenceInSeconds} from 'date-fns/differenceInSeconds';
import {addMinutes} from 'date-fns/addMinutes';

// Copy of the initAll function from https://github.com/alphagov/govuk-frontend/blob/v2.13.0/src/all.js
// except it only includes, and initialises, the components used by this application.
function initAll (options) {
  // Set the options to an empty object by default if no options are passed.
  options = typeof options !== 'undefined' ? options : {};

  // Allow the user to initialise GOV.UK Frontend in only certain sections of the page
  // Defaults to the entire document if nothing is set.
  var scope = typeof options.scope !== 'undefined' ? options.scope : document; // eslint-disable-line no-undef

  createAll(Button);

  createAll(PasswordInput);

  // Find first header module to enhance.
  const $toggleButton = scope.querySelectorAll('[data-module="govuk-header"]');
  $toggleButton.forEach(($toggleButton) => {
    new Header($toggleButton);
  });

  const $radios = scope.querySelectorAll('[data-module="govuk-radios"]');
  $radios.forEach(($radios) => {
    new Radios($radios);
  });

  const $skipLinks = scope.querySelectorAll('[data-module="govuk-skip-link"]');
  $skipLinks.forEach(($skipLink) => {
    new SkipLink($skipLink);
  });

  const $tabs = scope.querySelectorAll('[data-module="govuk-tabs"]');
  $tabs.forEach(($tabs) => {
    new Tabs($tabs);
  });

  // There will only every be one error-summary per page
  const $errorSummary = scope.querySelectorAll('[data-module="govuk-error-summary"]');
  $errorSummary.forEach(($errorSummary) => {
    new ErrorSummary($errorSummary);
  });
}

// Create separate namespace for GOVUK Frontend.
var Frontend = {
  "Header": Header,
  "Button": Button,
  "Radios": Radios,
  "ErrorSummary": ErrorSummary,
  "SkipLink": SkipLink,
  "PasswordInput": PasswordInput,
  "initAll": initAll
};

var vendor = {
  "morphdom": morphdom,
  "differenceInSeconds": differenceInSeconds,
  "addMinutes": addMinutes
};

// The exported object will be assigned to window.GOVUK in our production code
// (bundled into an IIFE by RollupJS)
export {
  Frontend,
  vendor
};
