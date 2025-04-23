/*
Session Timeouts
- - - - - - - - - - - - - - -
This file contains all of the JavaScript functionality necessary for the session inactivity
and expiry dialogs.

Dialogs:
* inactivityWarningDialog
  - Displayed after inactivityWarningMins minutes of inactivity
  - Contains the text "You've been inactive for 30 minutes You'll be signed out if you're inactive for 60 minutes."
  - User can click 'Close' button to close the dialog

* inactivityLogoutDialog
  - Displayed after inactivityWarningMins minutes of inactivity
  - Contains the text "You've been inactive for 58 minutes You'll be signed out if you're inactive for 60 minutes."
  - User can either click 'Stay signed in' or 'Sign out now'

* sessionExpiryDialog
  - Displayed after expiryWarningMins minutes
  - Contains the text "You can no longer extend your session You’ll be signed out in 2 minutes. We do
  this to keep your information secure."
  - User can either click 'Ok, continue' or 'Sign out now'

Timeouts:
* inactivityWarningDialogDisplayedTimeout
  - Opens the inactivityWarningDialog after inactivityWarningMins minutes of inactivity
  - If recent activity is detected in another tab, defers to setLastActiveInactivityTimeout

* inactivityLogoutDialogDisplayedTimeout
  - Opens the inactivityLogoutDialog after inactivityMins minutes of inactivity
  - If recent activity is detected in another tab, defers to setLastActiveInactivityTimeout

* inactivityLogoutTimeout
  - Starts when inactivityDialog is displayed
  - Logs the user out if they don't respond within inactivityWarningDisplayedDuration minutes

* lastActiveTimeout
  - Used to delay displaying dialogs if recent activity in another tab
  - Resets the dialog timeouts (both inactivityLogoutDialog and inactivityWarningDialog)
  based on how much time has passed since last activity recorded (stored with lastActivity attribute in local storage)

* expiryDialogDisplayedTimeout
  - Opens the sessionExpiryDialog after expiryWarningMins minutes
  - Alerts the user that they have 2 minutes remaining in their session before they are logged out

* expiryLogoutTimeout
  - Logs the user out when their session reaches its maximum duration, sessionExpiryMins minutes
  - Mirrors Flask's session lifetime
*/

const inactivityMins = Number(inactivity_mins); // Minutes until inactivity logout popup displayed
const inactivityWarningMins = Number(inactivity_warning_mins); // Minutes until inactivity warning popup displayed
const inactivityWarningDisplayedDuration = Number(inactivity_warning_duration); // Minutes until logout if no response after popup displayed
const expiryWarningMins = Number(expiry_warning_mins); // Minutes until popup displayed warning user of end of session
const sessionExpiryMins = Number(permanent_session_lifetime) / 60;
const inactivityLogoutDialog = document.getElementById("activity");
const inactivityWarningDialog = document.getElementById("activity-warning");
const sessionExpiryDialog = document.getElementById("expiry");
const loginTimestamp = new Date(logged_in_at);
let inactivityLogoutTimeout;
let lastActiveTimeout;
let inactivityLogoutDialogDisplayedTimeout;
let inactivityWarningDialogDisplayedTimeout;
let expiryLogoutTimeout;
let expiryDialogDisplayedTimeout;

(function (window) {
  "use strict";

  const {differenceInSeconds, addMinutes} = window.GOVUK.vendor;

  // Utility functions

  const isLoggedIn = function() {
    // Checking whether user logged in or not based on whether loginTimestamp exists and is a date
    return (loginTimestamp && !isNaN(new Date(loginTimestamp)));
  };

  const resetInactivityTimeouts = function(inactivityLogoutDialog, inactivityWarningDialog, sessionExpiryDialog){
    clearTimeout(inactivityLogoutDialogDisplayedTimeout); // inactivity dialog
    clearTimeout(inactivityLogoutTimeout); // inactivity logout
    clearTimeout(inactivityWarningDialogDisplayedTimeout); // warning dialog displayed
    clearTimeout(lastActiveTimeout);
    updateLocalStorage(); // Ensures this 'activity' captured and updates lastActive time
    // Restarts any activity related timeouts
    startInactivityTimeout(inactivityLogoutDialog, inactivityWarningDialog, sessionExpiryDialog);
    startInactivityWarningTimeout(inactivityLogoutDialog, inactivityWarningDialog, sessionExpiryDialog);
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

  const sessionIsAboutToExpire = function(){
    // if time from session start to when expiry dialog appears
    if (isLoggedIn()) {
      const current_time = new Date();
      const expiry_timestamp = addMinutes(loginTimestamp, expiryWarningMins);
      return (expiry_timestamp < current_time);
    }
    return false;
  };

  const getTimeDifferenceMilliseconds = function(minutes_later) {
    // calculates how many milliseconds between each time, returned in milliseconds as
    // setTimeout delay unit is milliseconds
    const current_time = new Date();
    const later_time = addMinutes(loginTimestamp, minutes_later);
    return differenceInSeconds(later_time, current_time) * 1000;
  };

  // Inactivity warning functions - regarding the 'soft' warning that lets user know they've been inactive
  // for inactivity_warning_mins

  const startInactivityWarningTimeout = function(inactivityLogoutDialog, inactivityWarningDialog, sessionExpiryDialog) {
    // Initial inactivity warning timeout that is restarted by request activity
    if (isLoggedIn() && !sessionIsAboutToExpire()) {
      inactivityWarningDialogDisplayedTimeout = setTimeout(function () {
        if (checkLocalStorage(inactivityWarningMins)) { // if last activity was less than set time ago,
            setLastActiveInactivityWarningTimeout(inactivityLogoutDialog, inactivityWarningDialog, sessionExpiryDialog);
                }
        else if ((inactivityLogoutDialog && !(inactivityLogoutDialog.hasAttribute('open'))) && (sessionExpiryDialog && !(sessionExpiryDialog.hasAttribute('open')))) {
          // Only open this dialog if the other dialogs are closed
                    inactivityWarningDialog.showModal();
                    inactivityWarningDialog.focus();
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
        resetInactivityTimeouts(inactivityLogoutDialog, inactivityWarningDialog, sessionExpiryDialog);
        inactivityWarningDialog.close();
      });
    }
  };

  const setLastActiveInactivityWarningTimeout = function(inactivityLogoutDialog, inactivityWarningDialog, sessionExpiryDialog) {
    // If activity in another tab, inactivity warning timeout period adjusted
    let lastActive = new Date(localStorage.getItem("lastActivity"));
    lastActiveTimeout = setTimeout(() => {
      if (!(inactivityWarningDialog.hasAttribute('open'))) {
        inactivityWarningDialog.showModal();
        inactivityWarningDialog.focus();
        clearTimeout(inactivityWarningDialogDisplayedTimeout);
        startInactivityWarningTimeout(inactivityLogoutDialog, inactivityWarningDialog, sessionExpiryDialog);
      }
    }, ((inactivityWarningMins * 60) - differenceInSeconds(new Date(), lastActive)) * 1000);
  };

  // Inactivity logout functions - regarding the warning that lets user know they've been inactive for
  // inactivity_mins and in 2 mins they'll be logged out

  const startInactivityTimeout = function(inactivityLogoutDialog, inactivityWarningDialog, sessionExpiryDialog) {
    // Inactivity logout timeout that is restarted by request activity
    if (isLoggedIn() && !sessionIsAboutToExpire()) {
      inactivityLogoutDialogDisplayedTimeout = setTimeout(function () {
        if (checkLocalStorage(inactivityMins)) { // if last activity was less than set time ago,
          setLastActiveInactivityTimeout(inactivityLogoutDialog, inactivityWarningDialog, sessionExpiryDialog);
        } else {
          closeDialogIfOpen(inactivityWarningDialog);
          inactivityLogoutDialog.showModal();
          inactivityLogoutDialog.focus();
          startInactivityDialogTimeout(inactivityLogoutDialog);
        }
      }, 1000 * 60 * inactivityMins);
    }
  };

  const startInactivityDialogTimeout = function(inactivityLogoutDialog) {
    // Logs user out if no response when the inactivity popup shows
    inactivityLogoutTimeout = setTimeout(function () {
      inactivityLogoutDialog.close();
      signOutRedirect('inactive');
    }, 1000 * 60 * inactivityWarningDisplayedDuration);
  };

  const staySignedIn = function(inactivityLogoutDialog, inactivityWarningDialog, sessionExpiryDialog) {
    // If stay signed in button is clicked then activity timeout is restarted
    const staySignedInButton = document.getElementById(
      "hmrc-timeout-keep-signin-btn"
    );
    if (staySignedInButton) {
      staySignedInButton.addEventListener("click", function () {
        inactivityLogoutDialog.close();
        resetInactivityTimeouts(inactivityLogoutDialog, inactivityWarningDialog, sessionExpiryDialog);
      });
    }
  };

  const setLastActiveInactivityTimeout = function(inactivityLogoutDialog, inactivityWarningDialog, sessionExpiryDialog) {
    // If activity in another tab, inactivity timeout period adjusted
    let lastActive = new Date(localStorage.getItem("lastActivity"));
    lastActiveTimeout = setTimeout(() => {
      closeDialogIfOpen(inactivityWarningDialog);
      if (!(inactivityLogoutDialog.hasAttribute('open'))) {
        inactivityLogoutDialog.showModal();
        inactivityLogoutDialog.focus();
        clearTimeout(inactivityLogoutTimeout);
        startInactivityDialogTimeout(inactivityLogoutDialog);
      }
    }, ((inactivityMins * 60) - differenceInSeconds(new Date(), lastActive)) * 1000);
  };

  // Session expiry functions - regarding the warning that lets user know they have 2 mins remaining in their session

  const startSessionExpiryTimeout = function(inactivityLogoutDialog, sessionExpiryDialog, inactivityWarningDialog) {
    // Logs user out after session lifetime expires, flask terminates session
    if (isLoggedIn()) {
      expiryLogoutTimeout = setTimeout(function () {
        closeDialogIfOpen(sessionExpiryDialog);
        closeDialogIfOpen(inactivityLogoutDialog);
        closeDialogIfOpen(inactivityWarningDialog);
        signOutRedirect('expired');
      }, getTimeDifferenceMilliseconds(sessionExpiryMins));
    }
  };

  const displaySessionExpiryDialog = function(inactivityLogoutDialog, sessionExpiryDialog, inactivityWarningDialog) {
    let timeUntilDialogDisplay = getTimeDifferenceMilliseconds(expiryWarningMins);
    // displays session expiry popup after timeout
    if (isLoggedIn() && timeUntilDialogDisplay > 0) {
      expiryDialogDisplayedTimeout = setTimeout(function () {
        if (sessionExpiryDialog)
        {
          // Close any open dialogs to replace with this one
          closeDialogIfOpen(inactivityLogoutDialog);
          closeDialogIfOpen(inactivityWarningDialog);

          sessionExpiryDialog.showModal();
          sessionExpiryDialog.focus();

          // Clears any timeouts to ensure no contradicting dialogs displayed in final 2 mins of session
          clearTimeout(inactivityLogoutDialogDisplayedTimeout);
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
  startSessionExpiryTimeout(inactivityLogoutDialog, sessionExpiryDialog, inactivityWarningDialog);
  displaySessionExpiryDialog(inactivityLogoutDialog, sessionExpiryDialog, inactivityWarningDialog);
  startInactivityTimeout(inactivityLogoutDialog, inactivityWarningDialog, sessionExpiryDialog);
  startInactivityWarningTimeout(inactivityLogoutDialog, inactivityWarningDialog, sessionExpiryDialog);
  staySignedIn(inactivityLogoutDialog, inactivityWarningDialog, sessionExpiryDialog);
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
