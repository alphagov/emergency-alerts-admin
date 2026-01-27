(function (window) {
  "use strict";
  window.GOVUK.addDiscardDraftsClickHandler = () => {
    const btn = document.getElementById("discard-alerts-button");
    if (btn) {
      btn.addEventListener("click", (e) => {
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
              "Content-Security-Policy": "connect-src 'self';",
            },
            body: JSON.stringify({ draft_alerts: checkedIds }),
          })
          .catch(error => {
            console.error('Fetch error:', error);
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
  window.GOVUK.addDiscardDraftsClickHandler();
})(window);
