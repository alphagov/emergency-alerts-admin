(function (window) {
  "use strict";
  window.GOVUK.addSelectAllCheckboxClickHandler = () => {
    const btn = document.getElementById("select-all-checkboxes-button");
    if (btn) {
      btn.addEventListener("click", () => {
        const checkboxes = document.querySelectorAll(".govuk-checkboxes__input");
        if (checkboxes.length) {
            for (const checkbox of checkboxes) {
              checkbox.checked = true;
            }
        }
        btn.blur();
      });
    }
  };
  window.GOVUK.addSelectAllCheckboxClickHandler();
})(window);
