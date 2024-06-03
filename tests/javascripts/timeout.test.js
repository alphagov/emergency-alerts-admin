const helpers = require("./support/helpers.js");
require("../../app/assets/javascripts/timeout.js");

afterAll(() => {
  require("./support/teardown.js");
  jest.useRealTimers(); // revert back to real timers once finished tests
  document.body.innerHTML = "";
});

const inactivity_period = window.GOVUK.inactivity_mins; // 1.1 to ensure it doesn't test for as soon as soon as timeout has finished
const timeout_period = window.GOVUK.timeout_warning_mins;
const warning_period = window.GOVUK.initial_warning_mins;
const inactivity_dialog = {open: false, getElementsByTagName: jest.fn(), showModal: jest.fn(), close: jest.fn()}
const session_expiry_dialog = {open: false, getElementsByTagName: jest.fn(), showModal: jest.fn(), close: jest.fn()}
const html_content = `
<dialog id="activity" tabindex="-1" aria-modal="true" class="hmrc-timeout-dialog"
aria-labelledby="hmrc-timeout-heading hmrc-timeout-message">
<div>
    <h1 id="hmrc-timeout-heading" class="govuk-heading-m push--top">You're about to be signed out</h1>
    <p class="govuk-body hmrc-timeout-dialog__message" aria-hidden="true">For your security, we will sign you out in 2 minutes.</p>
    <p id="hmrc-timeout-message" class="govuk-visually-hidden screenreader-content" aria-live="assertive">For your
        security, we will sign you out in 2 minutes.</p><button id="hmrc-timeout-keep-signin-btn"
        class="govuk-button">Stay signed in</button>
    <div class="hmrc-timeout-dialog__link-wrapper"><a id="hmrc-timeout-sign-out-link"
            class="govuk-link hmrc-timeout-dialog__link" href="/sign-out">Sign out</a></div>
</div>
</dialog>

<dialog id="expiry" tabindex="-1" aria-modal="true" class="hmrc-timeout-dialog"
aria-labelledby="hmrc-timeout-heading hmrc-timeout-message">
<div>
<h1 id="hmrc-timeout-heading" class="govuk-heading-m push--top">You can no longer extend your session</h1>
<p class="govuk-body hmrc-timeout-dialog__message" aria-hidden="true">For your security, we will sign you out in 2 minutes.</p>
<p id="hmrc-timeout-message" class="govuk-visually-hidden screenreader-content" aria-live="assertive">For your security, we will sign you out in 2 minutes.</p><button id="hmrc-timeout-sign-in-again-btn"
    class="govuk-button">Sign in again</button>
<div class="hmrc-timeout-dialog__link-wrapper"><a id="hmrc-timeout-sign-out-link"
        class="govuk-link hmrc-timeout-dialog__link" href="/sign-out">Sign out</a></div>
</div>
</dialog>
`;

describe("Inactivity dialog appears and components within it function correctly", () => {
  beforeEach(() => {
    document.body.innerHTML = html_content;
    inactivity_button = document.getElementById("hmrc-timeout-keep-signin-btn");
    link = document.getElementById("hmrc-timeout-sign-out-link");

    jest.useFakeTimers();
    window.GOVUK.sessionExpiryPopup(session_expiry_dialog);
    window.GOVUK.startInactivityTimeout(inactivity_dialog);
    window.GOVUK.resetTimeouts(inactivity_dialog);
  });

  afterEach(() => {
    document.body.innerHTML = "";
    jest.clearAllMocks();
  });

  test("User is logged in for the tests", () => {
    expect(window.GOVUK.isLoggedIn()).toBe(true);
  })

  test("Dialog opens after timeout", () => {
    expect(inactivity_dialog.showModal).not.toHaveBeenCalled();
    jest.advanceTimersByTime(60 * inactivity_period * 1000);
    expect(inactivity_dialog.showModal).toHaveBeenCalled();
  });

  test("Stay signed in button should close dialog and reset timeouts", () => {
    jest.spyOn(global, 'clearTimeout');
    jest.advanceTimersByTime(60 * inactivity_period * 1000);
    expect(inactivity_dialog.close).not.toHaveBeenCalled();
    helpers.triggerEvent(inactivity_button, "click");
    expect(clearTimeout).toHaveBeenCalledTimes(2);
    expect(inactivity_dialog.close).toHaveBeenCalled();
  });

});

describe("Timeout dialog appears", () => {
  beforeEach(() => {
    document.body.innerHTML = html_content;
    expiry_button = document.getElementById("hmrc-timeout-sign-in-again-btn");
    jest.useFakeTimers();
    window.GOVUK.sessionExpiryPopup(session_expiry_dialog);
  });

  afterEach(() => {
    document.body.innerHTML = "";
    jest.clearAllMocks();
  });

  test("Dialog opens after timeout", () => {
    expect(session_expiry_dialog.showModal).not.toHaveBeenCalled();
    jest.advanceTimersByTime(60 * timeout_period * 1000);
    expect(session_expiry_dialog.showModal).toHaveBeenCalled();
  });
});

describe("Activity in another tab delays inactivity timeout", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    document.body.innerHTML = html_content;
    jest.useFakeTimers();
    window.GOVUK.startInactivityTimeout(inactivity_dialog);
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  test("Popup doesn't appear after local storage updated", () => {
    expect(inactivity_dialog.showModal).not.toHaveBeenCalled();
    later = new Date();
    later.setSeconds(window.logged_in_at.getSeconds() + 30);
    localStorage.setItem("lastActivity", later); // Set lastActivity to 30s later so timeout should appear 30s later
    jest.advanceTimersByTime(60 * inactivity_period * 1000);
    expect(inactivity_dialog.showModal).not.toHaveBeenCalled();
    jest.advanceTimersByTime(60 * 0.5 * 1000);
    expect(inactivity_dialog.showModal).toHaveBeenCalled();
  });
});
