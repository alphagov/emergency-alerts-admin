const inactivityMins = Number(inactivity_mins); // Minutes until first popup displayed
const inactivityWarningDisplayedDuration = Number(inactivity_warning_duration); // Minutes until logout if no response after popup displayed
const expiryWarningMins = Number(expiry_warning_mins); // Minutes until popup displayed warning user of end of session
const sessionExpiryMins = Number(permanent_session_lifetime);
let inactivityLogoutTimeout;
let lastActiveTimeout;

let inactivityDialog = document.getElementById("activity");
let sessionExpiryDialog = document.getElementById("expiry");
let inactivityDialogDisplayedTimeout;
const loginTimestamp = new Date(logged_in_at);

(function (window) {
  "use strict";

  const {differenceInSeconds, addMinutes} = window.GOVUK.vendor;

  function isLoggedIn() {
    // Checking whether user logged in or not based on whether loginTimestamp exists and is a date
    return (loginTimestamp && !isNaN(new Date(loginTimestamp)));
  }

  function getTimeLeftUntilExpiry() {
    // calculates how long left in session, before final timeout, after each request
    const current_time = new Date();
    const expiry_time = addMinutes(loginTimestamp, expiryWarningMins);
    return differenceInSeconds(expiry_time, current_time) * 1000;
  }

  function displayInactivityPopup() {
    // Check if user logged in and there is enough time left before session expires
    let timeLeft = getTimeLeftUntilExpiry();
    return (
      isLoggedIn() &
      (timeLeft > (expiryWarningMins - inactivityMins) * 60 * 1000)
    );
  }

  function startInactivityTimeout(inactivityDialog) {
    // Initial timeout that is restarted by request activity
    if (displayInactivityPopup(inactivityDialog, addMinutes)) {
      inactivityDialogDisplayedTimeout = setTimeout(function () {
        if (checkLocalStorage()) { // if last activity was less than set time ago,
          setLastActiveTimeout(inactivityDialog);
        } else {
          inactivityDialog.showModal();
          startInactivityPopupTimeout(inactivityDialog);
        }
      }, 1000 * 60 * inactivityMins);
    }
  }

  function resetTimeouts(inactivityDialog) {
    // If stay signed in button is clicked then activity timeout is restarted
    const staySignedInButton = document.getElementById(
      "hmrc-timeout-keep-signin-btn"
    );
    if (staySignedInButton) {
      staySignedInButton.addEventListener("click", function () {
        clearTimeout(inactivityDialogDisplayedTimeout);
        clearTimeout(inactivityLogoutTimeout);
        inactivityDialog.close();
        startInactivityTimeout(inactivityDialog);
      });
    }
  }

  function startInactivityPopupTimeout(inactivityDialog) {
    // Logs user out if no response when the inactivity popup shows
    inactivityLogoutTimeout = setTimeout(function () {
      inactivityDialog.close();
      signOutRedirect();
    }, 1000 * 60 * inactivityWarningDisplayedDuration);
  }

  function sessionExpiryPopup(sessionExpiryDialog) {
    // displays session expiry popup after timeout
    if (isLoggedIn()) {
      inactivityLogoutTimeout = setTimeout(function () {
        if (sessionExpiryDialog)
        {
          sessionExpiryDialog.showModal();
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
    return (differenceInSeconds(new Date(), lastActive) < inactivityMins * 60);
  }

  function setLastActiveTimeout(inactivityDialog) {
    // If activity in another tab, inactivity timeout period adjusted
    let lastActive = new Date(localStorage.getItem("lastActivity"));
    lastActiveTimeout = setTimeout(() => {
      inactivityDialog.showModal();
      startInactivityPopupTimeout(inactivityDialog);
    }, ((inactivityMins * 60) - differenceInSeconds(new Date(), lastActive)) * 1000);
  }

  function signOutRedirect() {
    // send logout request and redirect to previous page upon relogging in
    let currentPage = encodeURIComponent(window.location.pathname);
    $.ajax("/sign-out", {
      method: "GET",
      success: function() {
        window.location.href = "/sign-in?next="+currentPage+"&status=inactive";
      },
      error: function(error) {
        console.log(error);
      },
    });
  }

  updateLocalStorage();
  sessionExpiryPopup(sessionExpiryDialog);
  startInactivityTimeout(inactivityDialog);
  resetTimeouts(inactivityDialog);

  window.GOVUK.startInactivityTimeout = startInactivityTimeout;
  window.GOVUK.sessionExpiryPopup = sessionExpiryPopup;
  window.GOVUK.signOutRedirect = signOutRedirect;
  window.GOVUK.resetTimeouts = resetTimeouts;
  window.GOVUK.updateLocalStorage = updateLocalStorage;
  window.GOVUK.inactivityMins = inactivityMins;
  window.GOVUK.expiryWarningMins = expiryWarningMins;
  window.GOVUK.inactivityWarningDisplayedDuration = inactivityWarningDisplayedDuration;
  window.GOVUK.isLoggedIn = isLoggedIn;

})(window);
