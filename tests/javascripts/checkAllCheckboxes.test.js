beforeAll(() => {
  require("../../app/assets/javascripts/checkAllCheckboxes.js");
});

afterAll(() => {
  require("./support/teardown.js");
});

const htmlContent = `
<div>
    <div>
        <input class="govuk-checkboxes__input" id="checkbox-1" name="checkbox" type="checkbox" value="checkbox1">
        <label for="checkbox-1">Checkbox1</label>
    </div>
    <div>
        <input class="govuk-checkboxes__input" id="checkbox-2" name="checkbox" type="checkbox" value="checkbox2">
        <label for="checkbox-2">Checkbox2</label>
    </div>
    <div>
        <input class="govuk-checkboxes__input" id="checkbox-3" name="checkbox" type="checkbox" value="checkbox3">
        <label for="checkbox-3">Checkbox3</label>
    </div>
    <div>
        <input class="govuk-checkboxes__input" id="checkbox-4" name="checkbox" type="checkbox" value="checkbox4">
        <label for="checkbox-4">Checkbox4</label>
    </div>
    <button id="check-all-checkboxes-button">
        Select all
    </button>
</div>
`;

describe("Checkboxes", () => {
  beforeEach(() => {
    document.body.innerHTML = htmlContent;
    window.GOVUK.addCheckAllCheckboxesClickHandler();
  });

  afterEach(() => {
    document.body.innerHTML = "";
    jest.clearAllMocks();
  });

  test("should be checked when select all button is clicked", () => {
    const btn = document.getElementById("check-all-checkboxes-button");
    const checkboxes = [
      document.getElementById("checkbox-1"),
      document.getElementById("checkbox-2"),
      document.getElementById("checkbox-3"),
      document.getElementById("checkbox-4"),
    ];
    btn.click();
    for (const checkbox of checkboxes) {
      expect(checkbox.checked).toBe(true);
    }
  });

  test("should be checked when some are pre-checked and select all button is clicked", () => {
    const btn = document.getElementById("check-all-checkboxes-button");
    const checkboxes = [
      document.getElementById("checkbox-1"),
      document.getElementById("checkbox-2"),
      document.getElementById("checkbox-3"),
      document.getElementById("checkbox-4"),
    ];
    checkboxes[1].checked = true;
    checkboxes[3].checked = true;
    btn.click();
    for (const checkbox of checkboxes) {
      expect(checkbox.checked).toBe(true);
    }
  });

  test("should allow unchecking after select all button is clicked", () => {
    const btn = document.getElementById("check-all-checkboxes-button");
    const checkboxes = [
      document.getElementById("checkbox-1"),
      document.getElementById("checkbox-2"),
      document.getElementById("checkbox-3"),
      document.getElementById("checkbox-4"),
    ];
    btn.click();
    for (const checkbox of checkboxes) {
      expect(checkbox.checked).toBe(true);
    }
    checkboxes[0].click();
    checkboxes[2].click();
    expect(checkboxes[0].checked).toBe(false);
    expect(checkboxes[2].checked).toBe(false);
  });
});
