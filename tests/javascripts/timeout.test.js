const helpers = require("./support/helpers.js");
require("../../app/assets/javascripts/timeout.js");

beforeAll(() => {
  document.body.innerHTML = "";
});

afterAll(() => {
  require("./support/teardown.js");
  jest.useRealTimers(); // revert back to real timers once finished tests
  document.body.innerHTML = "";
});

function isDialogOpen(dialog) {
  return dialog.hasAttribute("open");
}

const inactivity_period = window.GOVUK.inactivity_mins * 1.1; // 1.1 to ensure it doesn't test for as soon as soon as timeout has finished
const timeout_period = window.GOVUK.timeout_warning_mins * 1.1;

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
    inactivity_dialog = document.getElementById("activity");
    session_expiry_dialog = document.getElementById("expiry");
    inactivity_button = document.getElementById("hmrc-timeout-keep-signin-btn");
    link = document.getElementById("hmrc-timeout-sign-out-link");

    jest.useFakeTimers();
    window.GOVUK.sessionExpiryPopup();
    window.GOVUK.startInactivityTimeout();
    window.GOVUK.resetTimeouts();
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  test("Dialog opens after timeout", () => {
    expect(inactivity_dialog.open).toEqual(false);
    jest.advanceTimersByTime(60 * inactivity_period * 1000);
    if (window.GOVUK.isLoggedIn()) {
      expect(isDialogOpen(inactivity_dialog)).toEqual(true); // displays after period of inactivity
    } else {
      expect(isDialogOpen(inactivity_dialog)).toEqual(false);
    }
  });

  test("Inactivity dialog text appears in dialog", () => {
    jest.advanceTimersByTime(60 * inactivity_period * 1000);

    if (window.GOVUK.isLoggedIn()) {
      expect(isDialogOpen(inactivity_dialog)).toEqual(true);
      expect(inactivity_dialog.getElementsByTagName("h1")[0].textContent).toBe(
        "You're about to be signed out"
      );
      expect(inactivity_dialog.getElementsByTagName("p")[0].textContent).toBe(
        "For your security, we will sign you out in 2 minutes."
      );
    } else {
      expect(isDialogOpen(inactivity_dialog)).toEqual(false);
    }
  });

  test("Stay signed in button should close dialog and reset timeout ", () => {
    jest.advanceTimersByTime(60 * inactivity_period * 1000);
    if (window.GOVUK.isLoggedIn()) {
      expect(isDialogOpen(inactivity_dialog)).toEqual(true);

      helpers.triggerEvent(inactivity_button, "click");

      expect(isDialogOpen(inactivity_dialog)).toEqual(false);
    } else {
      expect(isDialogOpen(inactivity_dialog)).toEqual(false);
    }
  });

  test("Sign out button should close dialog and take to sign out screen", () => {
    const link = document.getElementById("hmrc-timeout-sign-out-link");
    const hasBeenClicked = jest.fn();
    link.addEventListener("click", hasBeenClicked);

    jest.advanceTimersByTime(60 * inactivity_period * 1000);
    if (window.GOVUK.isLoggedIn()) {
      expect(isDialogOpen(inactivity_dialog)).toEqual(true);

      helpers.triggerEvent(link, "click");

      expect(hasBeenClicked).toHaveBeenCalled();
    } else {
      expect(isDialogOpen(inactivity_dialog)).toEqual(false);
    }
  });
});

describe("Timeout dialog appears", () => {
  beforeEach(() => {
    document.body.innerHTML = html_content;
    jest.useFakeTimers();
    window.GOVUK.sessionExpiryPopup();
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  test("Dialog opens after timeout", () => {
    let session_expiry_dialog = document.getElementById("expiry");
    jest.advanceTimersByTime(60 * timeout_period * 1000);
    if (window.GOVUK.isLoggedIn()) {
      expect(isDialogOpen(session_expiry_dialog)).toEqual(true);

      helpers.triggerEvent(link, "click");

      expect(hasBeenClicked).toHaveBeenCalled();
    } else {
      expect(isDialogOpen(session_expiry_dialog)).toEqual(false);
    }
  });

  test("Expiry dialog text appears in dialog", () => {
    if (window.GOVUK.isLoggedIn()) {
      expect(session_expiry_dialog.getElementsByTagName("h1")[0].textContent).toBe(
        "You can no longer extend your session"
      );
    } else {
      expect(isDialogOpen(session_expiry_dialog)).toEqual(false);
      // not to be visible
    }
  });

  test("Sign in again button should close dialog and sign out ", () => {
    const expiry_button = document.getElementById(
      "hmrc-timeout-keep-signin-btn"
    );
    let session_expiry_dialog = document.getElementById("expiry");
    const hasBeenClicked = jest.fn();
    jest.advanceTimersByTime(60 * timeout_period * 1000);

    if (window.GOVUK.isLoggedIn()) {
      expiry_button.addEventListener("click", hasBeenClicked);
      helpers.triggerEvent(expiry_button, "click");

      window.GOVUK.signOutRedirect();
      expect(isDialogOpen(session_expiry_dialog)).toEqual(false);
      expect(hasBeenClicked).toHaveBeenCalled();
    } else {
      expect(isDialogOpen(session_expiry_dialog)).toEqual(false);
    }
  });
});

describe("Activity in another tab delays inactivity timeout", () => {
  beforeEach(() => {
    document.body.innerHTML = html_content;
    jest.useFakeTimers();
    window.GOVUK.startInactivityTimeout();
    inactivity_dialog = document.getElementById("activity");
  });

  afterEach(() => {
    document.body.innerHTML = "";
  });

  test("Popup doesn't appear after local storage updated", () => {
    later = new Date();
    later.setSeconds(later.getSeconds() + 20);
    localStorage.setItem("lastActivity", later);
    jest.advanceTimersByTime(60 * inactivity_period * 1000);
    if (window.GOVUK.isLoggedIn()) {
      expect(isDialogOpen(inactivity_dialog)).toEqual(false);
      jest.advanceTimersByTime(60 * 0.3 * 1000);
      expect(isDialogOpen(inactivity_dialog)).toEqual(true);
    } else {
      expect(isDialogOpen(inactivity_dialog)).toEqual(false);
    }
  });
});
