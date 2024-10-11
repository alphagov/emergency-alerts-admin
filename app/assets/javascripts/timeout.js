const inactivityMins = Number(inactivity_mins); // Minutes until first popup displayed
const inactivityWarningDisplayedDuration = Number(inactivity_warning_duration); // Minutes until logout if no response after popup displayed
const expiryWarningMins = Number(expiry_warning_mins); // Minutes until popup displayed warning user of end of session
const sessionExpiryMins = Number(permanent_session_lifetime) / 60;
const inactivityDialog = document.getElementById("activity");
const sessionExpiryDialog = document.getElementById("expiry");
const loginTimestamp = new Date(logged_in_at);
let inactivityLogoutTimeout;
let lastActiveTimeout;
let inactivityDialogDisplayedTimeout;
let sessionExpiryTimeout;

(function (window) {
  "use strict";

  const {differenceInSeconds, addMinutes} = window.GOVUK.vendor;

  const isLoggedIn = function() {
    // Checking whether user logged in or not based on whether loginTimestamp exists and is a date
    return (loginTimestamp && !isNaN(new Date(loginTimestamp)));
  };

  const getTimeLeftUntilExpiryDialogDisplayed = function() {
    // calculates how long left in session before expiry dialog displayed, before final timeout, after each request
    const current_time = new Date();
    const expiry_warning_time = addMinutes(loginTimestamp, expiryWarningMins);
    return differenceInSeconds(expiry_warning_time, current_time) * 1000;
  };

  const getTimeLeftUntilSessionExpiry = function() {
    // calculates how long left in session, before final timeout, after each request
    const current_time = new Date();
    const expiry_time = addMinutes(loginTimestamp, sessionExpiryMins);
    return differenceInSeconds(expiry_time, current_time) * 1000;
  };

  const startInactivityTimeout = function(inactivityDialog) {
    // Initial timeout that is restarted by request activity
    if (isLoggedIn()) {
      inactivityDialogDisplayedTimeout = setTimeout(function () {
        if (checkLocalStorage()) { // if last activity was less than set time ago,
          setLastActiveTimeout(inactivityDialog);
        } else {
          setTimeRemainingMessage();
          inactivityDialog.showModal();
          inactivityDialog.focus();
          startInactivityDialogTimeout(inactivityDialog);
        }
      }, 1000 * 60 * inactivityMins);
    }
  };

  const setTimeRemainingMessage = function() {
    const inactivityTimeRemainingMsg = document.getElementById("time-remaining-message");
    let timeLeft = Math.floor(getTimeLeftUntilSessionExpiry() / 60000);
    let message;
    if (timeLeft == 1) {
      message = "You have 1 minute remaining in your session.";
    } else if (timeLeft > 1) {
      message = "You have "+timeLeft+" minutes remaining in your session.";
    } else {
      message = "You have less than a minute remaining in your session.";
    }
    inactivityTimeRemainingMsg.innerHTML = message;
  };

  const resetInactivityTimeouts = function(inactivityDialog) {
    // If stay signed in button is clicked then activity timeout is restarted
    const staySignedInButton = document.getElementById(
      "hmrc-timeout-keep-signin-btn"
    );
    if (staySignedInButton) {
      staySignedInButton.addEventListener("click", function () {
        inactivityDialog.close();
        clearTimeout(inactivityDialogDisplayedTimeout);
        clearTimeout(inactivityLogoutTimeout);
        startInactivityTimeout(inactivityDialog);
      });
    }
  };

  const startInactivityDialogTimeout = function(inactivityDialog) {
    // Logs user out if no response when the inactivity popup shows
    inactivityLogoutTimeout = setTimeout(function () {
      inactivityDialog.close();
      signOutRedirect('inactive');
    }, 1000 * 60 * inactivityWarningDisplayedDuration);
  };

  const startSessionExpiryTimeout = function(inactivityDialog, sessionExpiryDialog) {
    // Logs user out after session lifetime expires, flask terminates session
    if (isLoggedIn()) {
      sessionExpiryTimeout = setTimeout(function () {
        if (sessionExpiryDialog.hasAttribute('open')) {
          sessionExpiryDialog.close();
        }
        if (inactivityDialog.hasAttribute('open')) {
          inactivityDialog.close();
        }
        signOutRedirect('expired');
      }, getTimeLeftUntilSessionExpiry());
    }
  };

  const displaySessionExpiryDialog = function(inactivityDialog, sessionExpiryDialog) {
    let timeUntilDialogDisplay = getTimeLeftUntilExpiryDialogDisplayed();
    // displays session expiry popup after timeout
    if (isLoggedIn() && timeUntilDialogDisplay > 0) {
      inactivityLogoutTimeout = setTimeout(function () {
        if (sessionExpiryDialog)
        {
          if (inactivityDialog.hasAttribute('open')){
            inactivityDialog.close();
          }
          sessionExpiryDialog.showModal();
          sessionExpiryDialog.focus();
          clearTimeout(inactivityDialogDisplayedTimeout);
          clearTimeout(inactivityLogoutTimeout);
          clearTimeout(lastActiveTimeout);
        }
      }, timeUntilDialogDisplay);
    }
  };

  const updateLocalStorage = function() {
    // With each request in any tab, the lastActive attribute is updated
    localStorage.setItem("lastActivity", new Date());
  };

  const checkLocalStorage = function() {
    // Checking local storage for any activity in other tabs & returns true if last activity less than set time ago
    let lastActive = new Date(localStorage.getItem("lastActivity"));
    return (differenceInSeconds(new Date(), lastActive) < inactivityMins * 60);
  };

  const setLastActiveTimeout = function(inactivityDialog) {
    // If activity in another tab, inactivity timeout period adjusted
    let lastActive = new Date(localStorage.getItem("lastActivity"));
    lastActiveTimeout = setTimeout(() => {
      setTimeRemainingMessage();
      inactivityDialog.showModal();
      inactivityDialog.focus();
      startInactivityDialogTimeout(inactivityDialog);
    }, ((inactivityMins * 60) - differenceInSeconds(new Date(), lastActive)) * 1000);
  };

  const signOutRedirect = function(status) {
    // send logout request and redirect to previous page upon relogging in
    let currentPage = encodeURIComponent(window.location.pathname);
    $.ajax("/sign-out", {
      method: "GET",
      success: function() {
        window.location.href = "/sign-in?next="+currentPage+"&status="+status;
      },
      error: function(error) {
        console.log(error);
      },
    });
  };

  const closeExpiryDialog = function(sessionExpiryDialog) {
    const continueButton = document.getElementById(
      "continue-button"
    );
    if (continueButton) {
      continueButton.addEventListener("click", function () {
        sessionExpiryDialog.close();
      });
    }
  };

  updateLocalStorage();
  startSessionExpiryTimeout(inactivityDialog, sessionExpiryDialog);
  displaySessionExpiryDialog(inactivityDialog, sessionExpiryDialog);
  startInactivityTimeout(inactivityDialog);
  resetInactivityTimeouts(inactivityDialog);
  closeExpiryDialog(sessionExpiryDialog);

  window.GOVUK.startInactivityTimeout = startInactivityTimeout;
  window.GOVUK.displaySessionExpiryDialog = displaySessionExpiryDialog;
  window.GOVUK.signOutRedirect = signOutRedirect;
  window.GOVUK.resetInactivityTimeouts = resetInactivityTimeouts;
  window.GOVUK.updateLocalStorage = updateLocalStorage;
  window.GOVUK.inactivityMins = inactivityMins;
  window.GOVUK.expiryWarningMins = expiryWarningMins;
  window.GOVUK.inactivityWarningDisplayedDuration = inactivityWarningDisplayedDuration;
  window.GOVUK.isLoggedIn = isLoggedIn;
  window.GOVUK.startSessionExpiryTimeout = startSessionExpiryTimeout;

})(window);
