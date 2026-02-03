(function (window) {
  "use strict";
  window.GOVUK.addRecalculateStickinessOnMutation = () => {
    const targetElement = document.querySelector('.ajax-block-container');
    if (!targetElement) {
      return;
    }
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
          mutation.removedNodes.forEach(() => {
              window.GOVUK.stickAtBottomWhenScrolling.recalculate();
          });
      });
      return;
    });
    observer.observe(targetElement, {
      childList: true
    });
  };
  window.GOVUK.addRecalculateStickinessOnMutation();
}(window));
