const helpers = require("./support/helpers.js");

beforeAll(() => {
  window.GOVUK.vendor = {
    differenceInSeconds: require('date-fns/differenceInSeconds').differenceInSeconds,
    addMinutes: require('date-fns/addMinutes').addMinutes,
  };
  require("../../app/assets/javascripts/timeout.js");
});

afterAll(() => {
  require("./support/teardown.js");
  jest.useRealTimers(); // revert back to real timers once finished tests
  document.body.innerHTML = "";
});

const inactivityDialog = {open: false, showModal: jest.fn(), close: jest.fn(), hasAttribute: jest.fn(), focus: jest.fn()}
const inactivityWarningDialog = {open: false, showModal: jest.fn(), close: jest.fn(), hasAttribute: jest.fn(), focus: jest.fn()}
const sessionExpiryDialog = {open: false, showModal: jest.fn(), close: jest.fn(), hasAttribute: jest.fn(), focus: jest.fn()}
const htmlContent = `
  <dialog id="activity" tabindex="-1" aria-modal="true" class="hmrc-timeout-dialog"
    role="dialog" aria-labelledby="hmrc-timeout-heading hmrc-timeout-message">
    <div class="hmrc-timeout-dialog-content">
        <h2 id="hmrc-timeout-heading" class="govuk-heading-m push--top">You're about to be signed out</h2>
        <h2 class="govuk-body hmrc-timeout-dialog__message" aria-hidden="true" id="time-remaining-message">You have n minutes remaining in your session.</h2>
        <h2 id="hmrc-timeout-message" class="govuk-visually-hidden screenreader-content" aria-live="assertive">If you do not sign in within 2 mins, your session will end. We do this to keep your information secure.</h2>
        {{ govukButton({
            "text": "Stay signed in",
            "classes": "govuk-button",
            "id": "hmrc-timeout-keep-signin-btn",
            "name": "stay-signed-in-btn"
        }) }}
        <div class="hmrc-timeout-dialog__link-wrapper">
            <a id="hmrc-timeout-sign-out-link" class="govuk-link hmrc-timeout-dialog__link" href="/sign-out">Sign out now</a>
        </div>
    </div>
  </dialog>
  <dialog id="expiry" tabindex="-1" aria-modal="true" class="hmrc-timeout-dialog" role="dialog" aria-labelledby="hmrc-timeout-heading hmrc-timeout-message">
    <div class="hmrc-timeout-dialog-content">
        <h2 id="hmrc-timeout-heading" class="govuk-heading-m push--top">You can no longer extend your session</h2>
        <h2 class="govuk-body hmrc-timeout-dialog__message" aria-hidden="true">You’ll be signed out in 2 minutes. We do this to keep your information secure.</h2>
        <h2 id="hmrc-timeout-message" class="govuk-visually-hidden screenreader-content" aria-live="assertive">You’ll be signed out in 2 minutes. We do this to keep your information secure.</h2>
        {{ govukButton({
            "text": "OK, continue",
            "classes": "govuk-button",
            "id": "continue-button",
            "name": "continue-btn"
        }) }}
        <div class="hmrc-timeout-dialog__link-wrapper">
            <a id="hmrc-timeout-sign-out-link" class="govuk-link hmrc-timeout-dialog__link" href="/sign-out">Sign out now</a>
        </div>
    </div>
  </dialog>
  <dialog id="activity-warning" tabindex="-1" aria-modal="true" class="hmrc-timeout-dialog"
      role="dialog" aria-labelledby="hmrc-timeout-heading hmrc-timeout-message">
      <div class="hmrc-timeout-dialog-content">
          <h2 id="hmrc-timeout-heading" class="govuk-heading-m push--top">You've been inactive for 28 minutes</h2>
          <h2 class="govuk-body hmrc-timeout-dialog__message" aria-hidden="true">You'll be signed out if you're inactive for 60 minutes.</h2>
          <a id="close-button" class="govuk-link hmrc-timeout-dialog__link">Close</a>
      </div>
  </dialog>
`;

describe("Inactivity dialog appears and components within it function correctly", () => {
  beforeEach(() => {
    document.body.innerHTML = htmlContent;
    link = document.getElementById("hmrc-timeout-sign-out-link");
    jest.useFakeTimers();
    window.GOVUK.displaySessionExpiryDialog(inactivityDialog, sessionExpiryDialog, inactivityWarningDialog);
    window.GOVUK.startInactivityTimeout(inactivityDialog, inactivityWarningDialog, sessionExpiryDialog);
    window.GOVUK.resetInactivityTimeouts(inactivityDialog, inactivityWarningDialog, sessionExpiryDialog);
  });

  afterEach(() => {
    document.body.innerHTML = "";
    jest.clearAllMocks();
  });

  test("User is logged in for the tests", () => {
    expect(window.GOVUK.isLoggedIn()).toBe(true);
  })

  test("Dialog opens after inactivity timeout", () => {
    expect(inactivityDialog.showModal).not.toHaveBeenCalled();
    jest.advanceTimersByTime(60 * window.GOVUK.inactivityMins * 1000);
    expect(inactivityDialog.showModal).toHaveBeenCalled();
  });

});

describe("Timeout dialog appears", () => {
  beforeEach(() => {
    document.body.innerHTML = htmlContent;
    jest.useFakeTimers();
    window.GOVUK.displaySessionExpiryDialog(inactivityDialog, sessionExpiryDialog, inactivityWarningDialog);
  });

  afterEach(() => {
    document.body.innerHTML = "";
    jest.clearAllMocks();
  });

  test("Dialog opens after timeout", () => {
    expect(sessionExpiryDialog.showModal).not.toHaveBeenCalled();
    jest.advanceTimersByTime(60 * window.GOVUK.expiryWarningMins * 1000);
    expect(sessionExpiryDialog.showModal).toHaveBeenCalled();
  });
});

describe("Activity in another tab delays inactivity timeout", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    document.body.innerHTML = htmlContent;
    jest.useFakeTimers();
    window.GOVUK.startInactivityTimeout(inactivityDialog, inactivityWarningDialog, sessionExpiryDialog);
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  test("Inactivity warning dialog doesn't appear after local storage updated", () => {
    expect(inactivityWarningDialog.showModal).not.toHaveBeenCalled();
    later = new Date();
    later.setSeconds(window.logged_in_at.getSeconds() + 30);
    localStorage.setItem("lastActivity", later); // Set lastActivity to 30s later so timeout should appear 30s later
    jest.advanceTimersByTime(60 * window.GOVUK.inactivityMins * 1000);
    expect(inactivityWarningDialog.showModal).not.toHaveBeenCalled();
    jest.advanceTimersByTime(60 * 1 * 1000);
    expect(inactivityWarningDialog.showModal).toHaveBeenCalled();
  });

  test("Inactivity dialog doesn't appear after local storage updated", () => {
    expect(inactivityDialog.showModal).not.toHaveBeenCalled();
    later = new Date();
    later.setSeconds(window.logged_in_at.getSeconds() + 30);
    localStorage.setItem("lastActivity", later); // Set lastActivity to 30s later so timeout should appear 30s later
    jest.advanceTimersByTime(60 * window.GOVUK.inactivityMins * 1000);
    expect(inactivityDialog.showModal).not.toHaveBeenCalled();
    jest.advanceTimersByTime(60 * 0.8 * 1000);
    expect(inactivityDialog.showModal).toHaveBeenCalled();
  });
});
