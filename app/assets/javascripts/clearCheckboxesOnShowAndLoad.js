(function (window) {
  "use strict";
  window.GOVUK.clearCheckboxesOnShowAndLoad = () => {
    function clearCheckboxes() {
      const checkboxes = document.querySelectorAll('input[type="checkbox"]');
      if (checkboxes.length) {
        for (const checkbox of checkboxes) {
          checkbox.checked = false;
        }
      }
    }
    // Clear on page show (handles back button)
    window.addEventListener('pageshow', clearCheckboxes);
    // Clear on page load
    window.addEventListener('load', clearCheckboxes);
  };
  window.GOVUK.clearCheckboxesOnShowAndLoad();
}(window));
