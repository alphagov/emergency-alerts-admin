(function (window) {
  "use strict";

  const addDiscardDraftsClickHandler = function () {
    const btn = document.getElementById("discard-alerts-button");
    if (btn) {
      btn.addEventListener("click", function () {
        const checkboxes = document.querySelectorAll(
          'input[type="checkbox"]:checked'
        );
        const checkedIds = Array.from(checkboxes).map((cb) => cb.id);
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
            });
            window.location.reload();
        }
        btn.blur();
      });
    }
  };

  addDiscardDraftsClickHandler();
  window.GOVUK.addDiscardDraftsClickHandler = addDiscardDraftsClickHandler;
})(window);
