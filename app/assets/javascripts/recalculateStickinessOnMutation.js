(function (global) {
  "use strict";

  const addRecalculateStickinessOnMutation = function () {
    const GOVUK = global.GOVUK;
    const targetElement = document.querySelector('.ajax-block-container');

    if (!targetElement)
      return;

    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
          mutation.removedNodes.forEach(() => {
              GOVUK.stickAtBottomWhenScrolling.recalculate();
          });
      });
    });

    observer.observe(targetElement, {
      childList: true
    });
  };

  addRecalculateStickinessOnMutation();
  window.GOVUK.addRecalculateStickinessOnMutation =
    addRecalculateStickinessOnMutation;

}(window));
