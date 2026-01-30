beforeAll(() => {
    require("../../app/assets/javascripts/clearCheckboxesOnShowAndLoad.js");
});

afterAll(() => {
  require("./support/teardown.js");
});

const htmlContent = `
<main>
  <form id="test-form">
    <input type="checkbox" id="checkbox1" checked>
    <input type="checkbox" id="checkbox2" checked>
    <input type="checkbox" id="checkbox3">
    <input type="text" id="textfield" value="test">
  </form>
</main>
`;

describe("Function clearCheckboxesOnShowAndLoad", () => {
  let addEventListenerSpy;

  beforeEach(() => {
    document.body.innerHTML = htmlContent;
    addEventListenerSpy = jest.spyOn(window, 'addEventListener');
    window.GOVUK.clearCheckboxesOnShowAndLoad();
  });

  afterEach(() => {
    document.body.innerHTML = "";
    jest.clearAllMocks();
  });

  test('should clear all checkboxes on pageshow event', () => {
    window.GOVUK.clearCheckboxesOnShowAndLoad();

    // Get the pageshow event handler
    const pageshowHandler = addEventListenerSpy.mock.calls.find(
      call => call[0] === 'pageshow'
    )[1];

    let mockCheckbox1 = document.getElementById("checkbox1");
    let mockCheckbox2 = document.getElementById("checkbox2");

    // Verify checkboxes are checked before event
    expect(mockCheckbox1.checked).toBe(true);
    expect(mockCheckbox2.checked).toBe(true);

    // Trigger the pageshow event handler
    pageshowHandler();

    // Verify checkboxes are unchecked after event
    expect(mockCheckbox1.checked).toBe(false);
    expect(mockCheckbox2.checked).toBe(false);
  });

  // test('should clear all checkboxes on load event', () => {
  //   window.GOVUK.clearCheckboxesOnShowAndLoad();

  //   // Get the load event handler
  //   const loadHandler = addEventListenerSpy.mock.calls.find(
  //     call => call[0] === 'load'
  //   )[1];

  //   let mockCheckbox1 = document.getElementById("checkbox1");
  //   let mockCheckbox2 = document.getElementById("checkbox2");

  //   // Verify checkboxes are checked before event
  //   expect(mockCheckbox1.checked).toBe(true);
  //   expect(mockCheckbox2.checked).toBe(true);

  //   // Trigger the load event handler
  //   loadHandler();

  //   // Verify checkboxes are unchecked after event
  //   expect(mockCheckbox1.checked).toBe(false);
  //   expect(mockCheckbox2.checked).toBe(false);
  // });
});
