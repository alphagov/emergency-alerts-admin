(function (window) {
  "use strict";

  const addDiscardDraftsClickHandler = function () {
    const btn = document.getElementById("discard-alerts-button");
    if (btn) {
      btn.addEventListener("click", function () {
        const checkboxes = document.querySelectorAll(
          'input[type="checkbox"]:checked'
        );
        const checkedIds = Array.from(checkboxes).map(function (cb) {
          return cb.id;
        });
        if (checkedIds.length) {
          const service_id = window.location.pathname
            .split("/")
            .filter(Boolean)[1];
          fetch(`/services/${service_id}/discard-drafts`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": btn.getAttribute("data-csrf-token"),
            },
            body: JSON.stringify({ draft_alerts: checkedIds }),
          })
          .then((response) => {
            if (!response.ok) {
              throw Error(response.statusText);
            }
          });
        }
        const newPath = window.location.pathname.replace(
          "/select-drafts",
          "/current-alerts"
        );
        window.location.href = newPath;
      });
    }
  };

  addDiscardDraftsClickHandler();
  window.GOVUK.addDiscardDraftsClickHandler = addDiscardDraftsClickHandler;
})(window);
