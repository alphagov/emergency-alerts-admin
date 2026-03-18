(function (window) {
  "use strict";
  window.GOVUK.addSelectSubmitHandler = () => {
    document.querySelectorAll('select[data-auto-submit="true"]').forEach(function(select) {
        select.addEventListener('change', function() {
            this.form.submit();
        });
    });
  };
  window.GOVUK.addSelectSubmitHandler();
})(window);
