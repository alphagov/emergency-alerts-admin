(function(Modules) {
  "use strict";

  Modules.FileUpload = function() {

    this.submit = () => this.$form.trigger('submit');

    this.addCancelButton = () => {

      var $cancelButton = $(`
        <a href="" role="button" class="file-upload-button govuk-button govuk-button--warning">
          Cancel upload
        </a>
      `);

      $('button.file-upload-button', this.$form).replaceWith($cancelButton);

      // add GOVUK Frontend behaviours
      new window.GOVUK.Frontend.Button(this.$form[0]).init();

      // move focus to the cancel button, it is lost when the upload button is removed
      $cancelButton.focus();

    };

    // Add a button that passes a click to the input[type=file]
    this.addFakeButton = function () {

      const buttonText = this.$field.data('buttonText');

      // Build the button element safely
      const $button = $('<button type="button" class="file-upload-button govuk-button govuk-!-margin-right-1" id="file-upload-button">')// Styled as a submit button to raise prominence. The type shouldn't change.
        .text(buttonText);

      // If errors with the upload, copy into a label above the button
      // Buttons don't need labels by default as the accessible name comes from their text but
      // errors need to be added to that.
      let $label;
      if (this.$fieldErrors.length > 0) {
        $label = $('<label class="file-upload-button-label error-message" for="file-upload-button">');

        // Span with sanitised text
        $('<span class="govuk-visually-hidden">')
          .text(buttonText + ' ')
          .appendTo($label);

        // fieldErrors text is already sanitised text from `.text()`
        $label.append(this.$fieldErrors.eq(0).text());
      }

      // Insert into DOM
      if ($label) {
        $label.insertAfter(this.$field);
        $button.insertAfter($label);
      } else {
        $button.insertAfter(this.$field);
      }

      // Wire up click handler
      $button.on('click', () => this.$field.click());

    };

    this.start = function(component) {

      this.$form = $(component);
      this.$field = this.$form.find('.file-upload-field');
      this.$fieldErrors = this.$form.find('.file-upload-label .error-message');

      // Note: label.file-upload-label, input.file-upload-field and button.file-upload-submit
      // are all hidden by CSS that uses the .js-enabled class on the body tag

      this.addFakeButton();

      // Clear the form if the user navigates back to the page
      $(window).on("pageshow", () => this.$form[0].reset());

      // Need to put the event on the container, not the input for it to work properly
      this.$form.on(
        'change', '.file-upload-field',
        () => this.submit() && this.addCancelButton()
      );

    };

  };

})(window.GOVUK.NotifyModules);
