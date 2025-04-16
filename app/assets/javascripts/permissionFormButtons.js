(function (Modules) {
  "use strict";

  // PermissionFormButtons will dynamically adjust the submit button text if sensitive permissions are added.
  // It expects to be given a parent <form> element, and will note those with "data-permission-sensitive".
  Modules.PermissionFormButtons = function () {
    this.start = function (permissionForm) {
      var $permissionForm = $(permissionForm)
      var submitButton = $permissionForm.find(":submit");
      var initialSubmitButtonText = submitButton.text();

      var sensitivePermissionCheckboxes = $("[data-permission-sensitive]");
      var sensitivePermissionValues = sensitivePermissionCheckboxes.map(function () { return this.value }).get();

      // Note the form's initial state for editing a user
      var initialPermissions = $("#permissions_field input:checked").map(function () { return this.value }).get();

      sensitivePermissionCheckboxes.on("change", function () {
        var currentPermissions = $("#permissions_field input:checked").map(function () { return this.value }).get();
        var newPermissions = currentPermissions.filter(function (permission) { return !initialPermissions.includes(permission) })

        if (newPermissions.some(function (permission) { return sensitivePermissionValues.includes(permission) })) {
          submitButton.text("Submit for approval");
        } else {
          submitButton.text(initialSubmitButtonText);
        }
      })
    };
  };

})(window.GOVUK.NotifyModules);
