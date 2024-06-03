const inactivity_mins = 28; // Minutes until first popup displayed
const initial_warning_mins = 2; // Minutes until logout if no response after popup displayed
const timeout_warning_mins = 58; // Minutes until popup displayed warning user of end of session
let inactivity_logout;
let inactivity_dialog = document.getElementById("activity");
let session_expiry_dialog = document.getElementById("expiry");
let inactivity_dialog_displayed;
const loginTimestamp = new Date(logged_in_at);

(function (window) {
  "use strict";

  function isLoggedIn() {
    // Checking whether user logged in or not based on whether loginTimestamp exists and is a date
    return (loginTimestamp && !isNaN(new Date(loginTimestamp)));
  }

  function getTimeLeftUntilExpiry() {
    // calculates how long left in session, before final timeout, after each request
    let expiry_time = new Date();
    expiry_time.setMinutes(
      loginTimestamp.getMinutes() + timeout_warning_mins
    );
    let current_time = new Date();
    return expiry_time - current_time;
  }

  function displayInactivityPopup() {
    // Check if user logged in and there is enough time left before session expires
    let timeLeft = getTimeLeftUntilExpiry();
    return (
      isLoggedIn() &
      (timeLeft > (timeout_warning_mins - inactivity_mins) * 60 * 1000)
    );
  }

  function startInactivityTimeout(inactivity_dialog) {
    // Initial timeout that is restarted by request activity
    if (displayInactivityPopup(inactivity_dialog)) {
      inactivity_dialog_displayed = setTimeout(function () {
        if (checkLocalStorage()) { // if last activity was less than set time ago,
          lastActiveTimeout(inactivity_dialog);
        } else {
          inactivity_dialog.showModal();
          startInactivityPopupTimeout(inactivity_dialog);
        }
      }, 1000 * 60 * inactivity_mins);
    }
  }

  function resetTimeouts(inactivity_dialog) {
    // If stay signed in button is clicked then activity timeout is restarted
    const staySignedInButton = document.getElementById(
      "hmrc-timeout-keep-signin-btn"
    );
    if (staySignedInButton) {
      staySignedInButton.addEventListener("click", function () {
        clearTimeout(inactivity_dialog_displayed);
        clearTimeout(inactivity_logout);
        inactivity_dialog.close();
        startInactivityTimeout(inactivity_dialog);
      });
    }
  }

  function startInactivityPopupTimeout(inactivity_dialog) {
    // Logs user out if no response when the inactivity popup shows
    inactivity_logout = setTimeout(function () {
      inactivity_dialog.close();
      signOutRedirect();
    }, 1000 * 60 * initial_warning_mins);
  }

  function sessionExpiryPopup(session_expiry_dialog) {
    // displays session expiry popup after timeout
    if (isLoggedIn()) {
      inactivity_logout = setTimeout(function () {
        if (session_expiry_dialog)
        {
          session_expiry_dialog.showModal();
        }
      }, getTimeLeftUntilExpiry());
    }
  }

  function updateLocalStorage() {
    // With each request in any tab, the lastActive attribute is updated
    localStorage.setItem("lastActivity", new Date());
  }

  function checkLocalStorage() {
    // Checking local storage for any activity in other tabs
    let lastActive = new Date(localStorage.getItem("lastActivity"));
    let time = new Date();
    return ((time - lastActive) < (inactivity_mins * 60 * 1000));
  }

  function lastActiveTimeout(inactivity_dialog) {
    // If activity in another tab, inactivity timeout period adjusted
    let time = new Date();
    let lastActive = new Date(localStorage.getItem("lastActivity"));
    setTimeout(() => {
      inactivity_dialog.showModal();
      startInactivityPopupTimeout(inactivity_dialog);
    }, (inactivity_mins * 60 * 1000) - (time - lastActive));
  }

  function signOutRedirect() {
    // send logout request and redirect to previous page upon relogging in
    let current_page = encodeURIComponent(window.location.pathname);
    $.ajax("/sign-out", {
      method: "GET",
      success: function() {
        window.location.href = "/sign-in?next="+current_page+"&status=inactive";
      },
      error: function(error) {
        console.log(error);
      },
    });
  }

  updateLocalStorage();
  sessionExpiryPopup(session_expiry_dialog);
  startInactivityTimeout(inactivity_dialog);
  resetTimeouts(inactivity_dialog);

  window.GOVUK.startInactivityTimeout = startInactivityTimeout;
  window.GOVUK.sessionExpiryPopup = sessionExpiryPopup;
  window.GOVUK.signOutRedirect = signOutRedirect;
  window.GOVUK.resetTimeouts = resetTimeouts;
  window.GOVUK.updateLocalStorage = updateLocalStorage;
  window.GOVUK.inactivity_mins = inactivity_mins;
  window.GOVUK.timeout_warning_mins = timeout_warning_mins;
  window.GOVUK.initial_warning_mins = initial_warning_mins;
  window.GOVUK.isLoggedIn = isLoggedIn;

})(window);
