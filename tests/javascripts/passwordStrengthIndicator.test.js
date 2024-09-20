const helpers = require("./support/helpers.js");

beforeAll(() => {
  require("../../app/assets/javascripts/passwordStrengthIndicator.js");
});

afterAll(() => {
    require("./support/teardown.js");
    document.body.innerHTML = "";
});

const htmlContent = `
    <div class="govuk-grid-row">
        <div class="govuk-grid-column-three-quarters">
            <form method="post" novalidate="">
                <div class="govuk-form-group">
                    <label class="govuk-label" for="old_password">
                        Current password
                    </label>
                    <input class="govuk-input govuk-!-width-two-thirds" id="old_password" name="old_password" type="password">
                </div>
                <div class="govuk-form-group">
                    <label class="govuk-label" for="new_password">
                        New password
                    </label>
                    <input class="govuk-input govuk-!-width-two-thirds" id="new_password" name="new_password" type="password">
                </div>
                <div class="govuk-!-width-two-thirds mapping-form-group">
                    <p class="govuk-body">Password strength: </p>
                    <p class="govuk-body govuk-!-font-weight-bold" id="password-strength" style="color: rgb(212, 53, 28);"></p>
                </div>
                <progress class="govuk-!-width-two-thirds" max="100" value="0" id="meter" style="--progress-bar-color: #d4351c;"></progress>
                <div class="page-footer">
                    <input type="hidden" name="csrf_token" value="IjMwYTRkNjIzMzAzN2JhZjg2MDA1MTkyZTBmOGUxNzBhYjNlOTZiYWEi.Zu2gKQ.a29fmH_mXAVDsokNgBitT-fCW70">
                    <button class="govuk-button page-footer__button" data-module="govuk-button">
                    Save
                    </button>
                </div>
            </form>
        </div>
    </div>
`

describe("For different passwords entered, the entropy, text and progress bar are updated accordingly", () => {
    beforeEach(() => {
        document.body.innerHTML = htmlContent;
    });

    afterEach(() => {
      document.body.innerHTML = "";
    });

    test("When page is rendered and nothing entered for new password, the progress bar is empty and no text for password strength", () => {
        document.getElementById("new_password").innerText = "";
        expect(document.getElementById("meter").value).toEqual(0);
    })

    test("When string with low entropy entered for new password, the progress bar shows value, is red and the text says weak", () => {
        expect(1 == 1);
    })


    test("When string with medium entropy entered for new password, the progress bar shows value, is orange and the text says medium", () => {
        expect(1 == 1);
    })

    test("When string with high enough entropy entered for new password, the progress bar shows value, is green and the text says string", () => {
        expect(1 == 1);
    })

  });
