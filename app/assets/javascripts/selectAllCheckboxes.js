(function (window) {
  "use strict";

  const addSelectAllCheckboxClickHandler = function () {
    const btn = document.getElementById("select-all-checkboxes-button");
    if (btn) {
      btn.addEventListener("click", function () {
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

  addSelectAllCheckboxClickHandler();
  window.GOVUK.addSelectAllCheckboxClickHandler =
    addSelectAllCheckboxClickHandler;
})(window);
