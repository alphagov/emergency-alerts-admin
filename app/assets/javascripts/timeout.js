const inactivityMins = Number(inactivity_mins); // Minutes until inactivity logout popup displayed
const inactivityWarningMins = Number(inactivity_warning_mins); // Minutes until inactivity warning popup displayed
const inactivityWarningDisplayedDuration = Number(inactivity_warning_duration); // Minutes until logout if no response after popup displayed
const expiryWarningMins = Number(expiry_warning_mins); // Minutes until popup displayed warning user of end of session
const sessionExpiryMins = Number(permanent_session_lifetime) / 60;
const inactivityDialog = document.getElementById("activity");
const inactivityWarningDialog = document.getElementById("activity-warning");
const sessionExpiryDialog = document.getElementById("expiry");
const loginTimestamp = new Date(logged_in_at);
let inactivityLogoutTimeout;
let lastActiveTimeout;
let inactivityDialogDisplayedTimeout;
let inactivityWarningDialogDisplayedTimeout;
let sessionExpiryTimeout;

(function (window) {
  "use strict";

  const {differenceInSeconds, addMinutes} = window.GOVUK.vendor;

  // Utility functions

  const isLoggedIn = function() {
    // Checking whether user logged in or not based on whether loginTimestamp exists and is a date
    return (loginTimestamp && !isNaN(new Date(loginTimestamp)));
  };

  const resetInactivityTimeouts = function(inactivityDialog, inactivityWarningDialog, sessionExpiryDialog){
    clearTimeout(inactivityDialogDisplayedTimeout); // inactivity dialog
    clearTimeout(inactivityLogoutTimeout); // inactivity logout
    clearTimeout(inactivityWarningDialogDisplayedTimeout); // warning dialog displayed
    clearTimeout(lastActiveTimeout);
    updateLocalStorage(); // Ensures this 'activity' captured and updates lastActive time
    // Restarts any activity related timeouts
    startInactivityTimeout(inactivityDialog, inactivityWarningDialog, sessionExpiryDialog);
    startInactivityWarningTimeout(inactivityDialog, inactivityWarningDialog, sessionExpiryDialog);
  };

  const checkLocalStorage = function(minutes) {
    // Checking local storage for any activity in other tabs & returns true if last activity less than set time ago
    let lastActive = new Date(localStorage.getItem("lastActivity"));
    return (differenceInSeconds(new Date(), lastActive) < minutes * 60);
  };

  const updateLocalStorage = function() {
    // With each request in any tab, the lastActivity attribute is updated
    localStorage.setItem("lastActivity", new Date());
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

  const closeDialogIfOpen = function(dialog){
    if (dialog.hasAttribute('open')) {
      dialog.close();
    }
  };

  const getTimeDifferenceMilliseconds = function(minutes_later) {
    // calculates how long left in session before expiry dialog displayed, before final timeout, after each request
    const current_time = new Date();
    const later_time = addMinutes(loginTimestamp, minutes_later);
    return differenceInSeconds(later_time, current_time) * 1000;
  };

  // Inactivity warning functions - regarding the 'soft' warning that lets user know they've been inactive
  // for inactivity_warning_mins

  const startInactivityWarningTimeout = function(inactivityDialog, inactivityWarningDialog, sessionExpiryDialog) {
    // Initial inactivity warning timeout that is restarted by request activity
    if (isLoggedIn()) {
      inactivityWarningDialogDisplayedTimeout = setTimeout(function () {
        if (checkLocalStorage(inactivityWarningMins)) { // if last activity was less than set time ago,
            setLastActiveInactivityWarningTimeout(inactivityDialog, inactivityWarningDialog, sessionExpiryDialog);
                }
        else if (!(inactivityDialog.hasAttribute('open')) && !(sessionExpiryDialog.hasAttribute('open'))) {
          // Only open this dialog if the other dialogs are closed
                    inactivityWarningDialog.showModal();
                    inactivityWarningDialog.focus();
                    startInactivityWarningTimeout(inactivityDialog, inactivityWarningDialog, sessionExpiryDialog);
                  }
      }, 1000 * 60 * inactivityWarningMins);
    }
  };

  const closeWarningDialog = function(inactivityWarningDialog) {
    const closeButton = document.getElementById(
      "close-button"
    );
    if (closeButton) {
      closeButton.addEventListener("click", function () {
        // if close button clicked, timeouts are reset and the 'activity' is recorded and lastActive updated
        resetInactivityTimeouts(inactivityDialog, inactivityWarningDialog, sessionExpiryDialog);
        inactivityWarningDialog.close();
      });
    }
  };

  const setLastActiveInactivityWarningTimeout = function(inactivityDialog, inactivityWarningDialog, sessionExpiryDialog) {
    // If activity in another tab, inactivity warning timeout period adjusted
    let lastActive = new Date(localStorage.getItem("lastActivity"));
    lastActiveTimeout = setTimeout(() => {
      if (!(inactivityWarningDialog.hasAttribute('open'))) {
        inactivityWarningDialog.showModal();
        inactivityWarningDialog.focus();
        clearTimeout(inactivityWarningDialogDisplayedTimeout);
        startInactivityWarningTimeout(inactivityDialog, inactivityWarningDialog, sessionExpiryDialog);
      }
    }, ((inactivityWarningMins * 60) - differenceInSeconds(new Date(), lastActive)) * 1000);
  };

  // Inactivity logout functions - regarding the warning that lets user know they've been inactive for
  // inactivity_mins and in 2 mins they'll be logged out

  const startInactivityTimeout = function(inactivityDialog, inactivityWarningDialog, sessionExpiryDialog) {
    // Inactivity logout timeout that is restarted by request activity
    if (isLoggedIn()) {
      inactivityDialogDisplayedTimeout = setTimeout(function () {
        if (checkLocalStorage(inactivityMins)) { // if last activity was less than set time ago,
          setLastActiveInactivityTimeout(inactivityDialog, inactivityWarningDialog, sessionExpiryDialog);
        } else {
          closeDialogIfOpen(inactivityWarningDialog);
          inactivityDialog.showModal();
          inactivityDialog.focus();
          startInactivityDialogTimeout(inactivityDialog);
        }
      }, 1000 * 60 * inactivityMins);
    }
  };

  const startInactivityDialogTimeout = function(inactivityDialog) {
    // Logs user out if no response when the inactivity popup shows
    inactivityLogoutTimeout = setTimeout(function () {
      inactivityDialog.close();
      signOutRedirect('inactive');
    }, 1000 * 60 * inactivityWarningDisplayedDuration);
  };

  const staySignedIn = function(inactivityDialog, inactivityWarningDialog, sessionExpiryDialog) {
    // If stay signed in button is clicked then activity timeout is restarted
    const staySignedInButton = document.getElementById(
      "hmrc-timeout-keep-signin-btn"
    );
    if (staySignedInButton) {
      staySignedInButton.addEventListener("click", function () {
        inactivityDialog.close();
        resetInactivityTimeouts(inactivityDialog, inactivityWarningDialog, sessionExpiryDialog);
      });
    }
  };

  const setLastActiveInactivityTimeout = function(inactivityDialog, inactivityWarningDialog, sessionExpiryDialog) {
    // If activity in another tab, inactivity timeout period adjusted
    let lastActive = new Date(localStorage.getItem("lastActivity"));
    lastActiveTimeout = setTimeout(() => {
      closeDialogIfOpen(inactivityWarningDialog);
      if (!(inactivityDialog.hasAttribute('open'))) {
        inactivityDialog.showModal();
        inactivityDialog.focus();
        clearTimeout(inactivityLogoutTimeout);
        startInactivityDialogTimeout(inactivityDialog);
      }
    }, ((inactivityMins * 60) - differenceInSeconds(new Date(), lastActive)) * 1000);
  };

  // Session expiry functions - regarding the warning that lets user know they have 2 mins remaining in their session

  const startSessionExpiryTimeout = function(inactivityDialog, sessionExpiryDialog, inactivityWarningDialog) {
    // Logs user out after session lifetime expires, flask terminates session
    if (isLoggedIn()) {
      sessionExpiryTimeout = setTimeout(function () {
        closeDialogIfOpen(sessionExpiryDialog);
        closeDialogIfOpen(inactivityDialog);
        closeDialogIfOpen(inactivityWarningDialog);
        signOutRedirect('expired');
      }, getTimeDifferenceMilliseconds(sessionExpiryMins));
    }
  };

  const displaySessionExpiryDialog = function(inactivityDialog, sessionExpiryDialog, inactivityWarningDialog) {
    let timeUntilDialogDisplay = getTimeDifferenceMilliseconds(expiryWarningMins);
    // displays session expiry popup after timeout
    if (isLoggedIn() && timeUntilDialogDisplay > 0) {
      inactivityLogoutTimeout = setTimeout(function () {
        if (sessionExpiryDialog)
        {
          // Close any open dialogs to replace with this one
          closeDialogIfOpen(inactivityDialog);
          closeDialogIfOpen(inactivityWarningDialog);

          sessionExpiryDialog.showModal();
          sessionExpiryDialog.focus();

          // Clears any timeouts to ensure no contradicting dialogs displayed in final 2 mins of session
          clearTimeout(inactivityDialogDisplayedTimeout);
          clearTimeout(inactivityLogoutTimeout);
          clearTimeout(inactivityWarningDialogDisplayedTimeout);
          clearTimeout(lastActiveTimeout);
        }
      }, timeUntilDialogDisplay);
    }
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
  startSessionExpiryTimeout(inactivityDialog, sessionExpiryDialog, inactivityWarningDialog);
  displaySessionExpiryDialog(inactivityDialog, sessionExpiryDialog, inactivityWarningDialog);
  startInactivityTimeout(inactivityDialog, inactivityWarningDialog, sessionExpiryDialog);
  startInactivityWarningTimeout(inactivityDialog, inactivityWarningDialog, sessionExpiryDialog);
  staySignedIn(inactivityDialog, inactivityWarningDialog, sessionExpiryDialog);
  closeExpiryDialog(sessionExpiryDialog);
  closeWarningDialog(inactivityWarningDialog);

  window.GOVUK.startInactivityTimeout = startInactivityTimeout;
  window.GOVUK.startInactivityWarningTimeout = startInactivityWarningTimeout;
  window.GOVUK.displaySessionExpiryDialog = displaySessionExpiryDialog;
  window.GOVUK.signOutRedirect = signOutRedirect;
  window.GOVUK.staySignedIn = staySignedIn;
  window.GOVUK.updateLocalStorage = updateLocalStorage;
  window.GOVUK.inactivityMins = inactivityMins;
  window.GOVUK.expiryWarningMins = expiryWarningMins;
  window.GOVUK.inactivityWarningMins = inactivityWarningMins;
  window.GOVUK.inactivityWarningDisplayedDuration = inactivityWarningDisplayedDuration;
  window.GOVUK.isLoggedIn = isLoggedIn;
  window.GOVUK.startSessionExpiryTimeout = startSessionExpiryTimeout;
  window.GOVUK.closeWarningDialog = closeWarningDialog;

})(window);
