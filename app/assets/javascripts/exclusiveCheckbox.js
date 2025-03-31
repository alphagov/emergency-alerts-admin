(function (window) {
    "use strict";

    const addExclusiveCheckboxClickHandler = function() {
        const checkboxes = document.getElementsByName("networks");

        if (checkboxes.length === 0)
            return;

        let exclusiveCheckbox = null;
        const otherCheckboxes = [];

        checkboxes.forEach(function(checkbox) {
            if (checkbox.value == "all") {
                exclusiveCheckbox = checkbox;
            } else {
                otherCheckboxes.push(checkbox);
            }
        });

        exclusiveCheckbox.addEventListener("click", function() {
            if (this.checked) {
                otherCheckboxes.forEach(function(checkbox) {
                    checkbox.checked = false;
                });
            }
        });

        otherCheckboxes.forEach(function(checkbox) {
            checkbox.addEventListener("click", function() {
                if (this.checked) {
                    exclusiveCheckbox.checked = false;
                }
            });
        });
    };

    addExclusiveCheckboxClickHandler();

  })(window);
