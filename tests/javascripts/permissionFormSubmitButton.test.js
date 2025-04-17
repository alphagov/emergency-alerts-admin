const helpers = require('./support/helpers.js');

beforeAll(() => {
  require('../../app/assets/javascripts/permissionFormSubmitButton.js');
});

afterAll(() => {
  require('./support/teardown.js');
});

describe('Permission form dynamic submit button text', () => {
  let submitButton;

  beforeEach(() => {

    // set up DOM
    document.body.innerHTML = `
      <form
        method="post"
        autocomplete="off"
        data-notify-module="permission-form-submit-button"
        novalidate=""
      >
        <div class="govuk-form-group">
          <fieldset
            class="govuk-fieldset"
            id="permissions_field"
          >
            <legend class="govuk-fieldset__legend govuk-fieldset__legend--s">
              Permissions
            </legend>

            <div class="govuk-checkboxes" data-module="govuk-checkboxes">
              <div class="govuk-checkboxes__item">
                <input
                  class="govuk-checkboxes__input"
                  id="permissions_field-0"
                  name="permissions_field"
                  type="checkbox"
                  value="manage_templates"
                />
                <label
                  class="govuk-label govuk-checkboxes__label"
                  for="permissions_field-0"
                >
                  Add and edit templates
                </label>
              </div>

              <div class="govuk-checkboxes__item">
                <input
                  class="govuk-checkboxes__input"
                  id="permissions_field-1"
                  name="permissions_field"
                  type="checkbox"
                  value="create_broadcasts"
                  data-permission-sensitive="true"
                />
                <label
                  class="govuk-label govuk-checkboxes__label"
                  for="permissions_field-1"
                >
                  Create new alerts
                </label>
              </div>

              <div class="govuk-checkboxes__item">
                <input
                  class="govuk-checkboxes__input"
                  id="permissions_field-2"
                  name="permissions_field"
                  type="checkbox"
                  value="approve_broadcasts"
                  data-permission-sensitive="true"
                />
                <label
                  class="govuk-label govuk-checkboxes__label"
                  for="permissions_field-2"
                >
                  Approve alerts
                </label>
              </div>
            </div>
          </fieldset>
        </div>

        <div class="page-footer">
          <button
            id="submit-button"
            type="submit"
            class="govuk-button page-footer__button"
            data-module="govuk-button"
          >Save</button>
        </div>
      </form>`;

    submitButton = document.getElementById("submit-button");
  });

  afterEach(() => {
    document.body.innerHTML = '';
  });

  describe("When the page loads", () => {
    test("The submit button should have its initial text value", () => {
      window.GOVUK.notifyModules.start();
      expect(submitButton.textContent).toBe("Save");
    });
  });

  describe("Checkbox change events", () => {
    test("The submit button changes to approval when a sensitive permission is checked", () => {
      window.GOVUK.notifyModules.start();
      expect(submitButton.textContent).toBe("Save");

      // create_broadcasts
      document.getElementById("permissions_field-1").click();
      expect(submitButton.textContent).toBe("Submit for approval");

      // Uncheck again
      document.getElementById("permissions_field-1").click();
      expect(submitButton.textContent).toBe("Save");
    });

    test("The submit button does not change when a sensitive permission is unchecked", () => {
      document.getElementById("permissions_field-1").click(); // Checked initially

      window.GOVUK.notifyModules.start();
      expect(submitButton.textContent).toBe("Save");

      // create_broadcasts
      document.getElementById("permissions_field-1").click(); // Uncheck
      expect(submitButton.textContent).toBe("Save");
    });

    test("The submit button does not change when an unsensitive permission is checked", () => {

      window.GOVUK.notifyModules.start();
      expect(submitButton.textContent).toBe("Save");

      // manage_templates
      document.getElementById("permissions_field-0").click();
      expect(submitButton.textContent).toBe("Save");
    });
  });


});
