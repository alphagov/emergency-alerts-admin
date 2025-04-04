beforeAll(() => {
  require("../../app/assets/javascripts/exclusiveCheckbox.js");
});

afterAll(() => {
  require("./support/teardown.js");
});

const htmlContent = `
<div>
    <div>
        <input id="networks-0" name="networks" type="checkbox" value="all">
        <label for="networks-0">All mobile networks</label>
    </div>
    <div>
        <input id="networks-1" name="networks" type="checkbox" value="ee">
        <label for="networks-1">EE</label>
    </div>
    <div>
        <input id="networks-2" name="networks" type="checkbox" value="o2">
        <label for="networks-2">O2</label>
    </div>
    <div>
        <input id="networks-3" name="networks" type="checkbox" value="vodafone">
        <label for="networks-3">Vodafone</label>
    </div>
    <div>
        <input id="networks-4" name="networks" type="checkbox" value="three">
        <label for="networks-4">Three</label>
    </div>
</div>
`;

describe("Exclusive checkbox", () => {
  beforeEach(() => {
    document.body.innerHTML = htmlContent;
    window.GOVUK.addExclusiveCheckboxClickHandler();
  });

  afterEach(() => {
    document.body.innerHTML = "";
    jest.clearAllMocks();
  });

  test("should be checked when clicked", () => {
    const exclusiveCheckbox = document.getElementById("networks-0");
    const otherCheckboxes = [
      document.getElementById("networks-1"),
      document.getElementById("networks-2"),
      document.getElementById("networks-3"),
      document.getElementById("networks-4"),
    ];

    exclusiveCheckbox.click();
    expect(exclusiveCheckbox.checked).toBe(true);

    otherCheckboxes.forEach((checkbox) => {
      expect(checkbox.checked).toBe(false);
    });
  });

  test("should uncheck other checkboxes when clicked", () => {
    const exclusiveCheckbox = document.getElementById("networks-0");
    const otherCheckboxes = [
      document.getElementById("networks-1"),
      document.getElementById("networks-2"),
      document.getElementById("networks-3"),
      document.getElementById("networks-4"),
    ];

    otherCheckboxes.forEach((checkbox) => {
      checkbox.click();
    });
    otherCheckboxes.forEach((checkbox) => {
      expect(checkbox.checked).toBe(true);
    });

    exclusiveCheckbox.click();
    expect(exclusiveCheckbox.checked).toBe(true);
    otherCheckboxes.forEach((checkbox) => {
      expect(checkbox.checked).toBe(false);
    });
  });

  test("should uncheck when another checkbox is checked", () => {
    const exclusiveCheckbox = document.getElementById("networks-0");
    const otherCheckboxes = [
      document.getElementById("networks-1"),
      document.getElementById("networks-2"),
      document.getElementById("networks-3"),
      document.getElementById("networks-4"),
    ];

    exclusiveCheckbox.click();
    expect(exclusiveCheckbox.checked).toBe(true);

    otherCheckboxes[2].click();
    expect(otherCheckboxes[2].checked).toBe(true);
    expect(exclusiveCheckbox.checked).toBe(false);

    expect(otherCheckboxes[0].checked).toBe(false);
    expect(otherCheckboxes[1].checked).toBe(false);
    expect(otherCheckboxes[3].checked).toBe(false);
  });
});
