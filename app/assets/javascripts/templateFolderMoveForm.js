(function(Modules) {
  "use strict";

  Modules.TemplateFolderMoveForm = function() {

    this.start = function(templateFolderMoveForm) {
      this.$form = $(templateFolderMoveForm);
      this.$form.on('click', 'button.govuk-button--secondary', (event) => this.actionButtonClicked(event));
      this.removeFoldersFromList();
      this.disableCurrentLevelFolder();

    };


    // Remove selected folders and their children from the list
    this.removeFoldersFromList = function() {
      let raw = $("input[name='template_folders_to_move']").val();
      raw = raw.replace(/'/g, '"');
      let targetValues = JSON.parse(raw);
      targetValues.forEach(function (value) {
        $("input[type=radio][name=move_to][value='" + value + "']")
            .closest("li")
            .remove();
      });
    }


    // Disable folder radio button at the current level
    this.disableCurrentLevelFolder = function() {
      let currentId = $("input[name='current_folder_id']").val();
      if (currentId == 'None') {
        currentId = '__NONE__';
      }
      let $radio = $("input[type=radio][name=move_to][value='" + currentId + "']");

      if ($radio.length) {
        $radio.prop("disabled", true);
        $radio.next("label").append(" <-- current location");
      }
    }


    this.actionButtonClicked = function(event) {
      event.preventDefault();
      this.currentState = $(event.currentTarget).val();

    };


  };

})(window.GOVUK.NotifyModules);
