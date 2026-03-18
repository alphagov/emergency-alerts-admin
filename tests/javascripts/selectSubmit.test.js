beforeAll(() => {
  require("../../app/assets/javascripts/selectSubmit.js");
});

afterAll(() => {
  require("./support/teardown.js");
});

const htmlContent = `
<form method="POST" id="myForm">
    <select name="my_select" id="mySelect" data-auto-submit="true">
        <option value="option1">Option 1</option>
        <option value="option2">Option 2</option>
        <option value="option3">Option 3</option>
    </select>
</form>
`;

describe("Form auto-submit", () => {
  beforeEach(() => {
    document.body.innerHTML = htmlContent;

    form = document.getElementById("myForm");
    form.submit = jest.fn();

    window.GOVUK.addSelectSubmitHandler();
  });

  afterEach(() => {
    document.body.innerHTML = "";
    jest.clearAllMocks();
  });

  test("should submit form when select value changes", () => {
    select = document.getElementById("mySelect");

    // Trigger the change event
    const changeEvent = new Event("change", { bubbles: true });
    select.dispatchEvent(changeEvent);

    expect(form.submit).toHaveBeenCalledTimes(1);
  });
});
