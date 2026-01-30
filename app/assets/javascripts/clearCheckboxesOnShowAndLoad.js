(function (window) {
  "use strict";
  window.GOVUK.clearCheckboxesOnShowAndLoad = () => {
    function clearCheckboxes() {
      document.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
        checkbox.checked = false;
      });
    }
    // Clear on page show (handles back button)
    window.addEventListener('pageshow', clearCheckboxes);
    // Clear on page load
    window.addEventListener('load', clearCheckboxes);
  };
  window.GOVUK.clearCheckboxesOnShowAndLoad();
}(window));
