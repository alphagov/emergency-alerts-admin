(function (window) {
  "use strict";
  window.GOVUK.addCheckAllCheckboxesClickHandler = () => {
    const btn = document.getElementById("check-all-checkboxes-button");
    if (btn) {
      btn.addEventListener("click", () => {
        const checkboxes = document.querySelectorAll('input[type="checkbox"]');
        if (checkboxes.length) {
            for (const checkbox of checkboxes) {
              checkbox.checked = true;
            }
        }
        btn.blur();
      });
    }
  };
  window.GOVUK.addCheckAllCheckboxesClickHandler();
})(window);
