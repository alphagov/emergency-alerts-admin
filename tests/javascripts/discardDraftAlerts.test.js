beforeAll(() => {
  require("../../app/assets/javascripts/discardDraftAlerts.js");
  window.fetch = () => { }
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
    <button id="discard-alerts-button" data-csrf-token="random_token_goes_here">
        Select all
    </button>
</div>
`;

describe("Discard drafts endpoint", () => {
  beforeEach(() => {
    document.body.innerHTML = htmlContent;
    window.GOVUK.addDiscardDraftsClickHandler();
  });

  afterEach(() => {
    document.body.innerHTML = "";
    jest.clearAllMocks();
  });

  test("should be called when discard-alerts-button button is clicked", () => {
    const fetchSpy = jest.spyOn(window, 'fetch').mockResolvedValue({
        ok: true
    });

    delete window.location;
    window.location = { pathname: '/services/228098f8-43b5-4072-8673-d5e6e9cf7ca1/discard-drafts' };

    const service_id = "228098f8-43b5-4072-8673-d5e6e9cf7ca1";

    const btn = document.getElementById("discard-alerts-button");
    const checkboxes = [
      document.getElementById("checkbox-1"),
      document.getElementById("checkbox-2"),
      document.getElementById("checkbox-3"),
      document.getElementById("checkbox-4"),
    ];
    for (const checkbox of checkboxes) {
      checkbox.checked = true;
    }
    btn.click();

    expect(fetchSpy).toHaveBeenCalledTimes(1);

    expect(fetchSpy).toHaveBeenCalledWith(
        `/services/${service_id}/discard-drafts`,
        expect.objectContaining({
            method: "POST",
            headers: expect.objectContaining({
                "Content-Type": "application/json",
                "X-CSRFToken": expect.any(String),
            }),
            body: expect.any(String)
        })
    );

    const callArgs = fetchSpy.mock.calls[0];
    const requestBody = JSON.parse(callArgs[1].body);
    expect(requestBody.draft_alerts).toEqual(expect.arrayContaining([
        "checkbox-1",
        "checkbox-2",
        "checkbox-3",
        "checkbox-4"
    ]));
    expect(requestBody.draft_alerts).toHaveLength(4);
  });
});
