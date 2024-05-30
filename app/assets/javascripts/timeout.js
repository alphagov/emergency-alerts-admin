const inactivity_mins = 28; // Minutes until first popup displayed
const initial_warning_mins = 2; // Minutes until logout if no response after popup displayed
const timeout_warning_mins = 58; // Minutes until popup displayed warning user of end of session

(function (window) {
  "use strict";

  function isLoggedIn() {
    // Checking whether user logged in or not based on whether logged_in_at exists
    let timestamp;
    if (typeof logged_in_at == 'undefined' || logged_in_at == 'None') {
      timestamp =  'Test';
    } else {
      timestamp = new Date(logged_in_at);
    }
    return (timestamp instanceof Date) & !isNaN(timestamp);
  }
  function loggedInAt() {
    if (typeof logged_in_at == 'undefined') {
      return new Date(); // This needs to be created for the tests
    }
    return new Date(logged_in_at);
  }

  function getTimeLeftUntilExpiry() {
    // calculates how long left in session, before final timeout, after each request
    let expiry_time = new Date();
    expiry_time.setMinutes(
      loggedInAt().getMinutes() + timeout_warning_mins
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

  function startInactivityTimeout() {
    // Initial timeout that is restarted by request activity
    if (displayInactivityPopup()) {
      inactivity_dialog = setTimeout(function () {
        if (checkLocalStorage()) {
          lastActiveTimeout();
        } else {
          const inactivity_popup = document.getElementById("activity");
          inactivity_popup.showModal();
          startInactivityPopupTimeout();
        }
      }, 1000 * 60 * inactivity_mins);
    }
  }

  function resetTimeouts() {
    // If stay signed in button is clicked then activity timeout is restarted
    const staySignedInButton = document.getElementById(
      "hmrc-timeout-keep-signin-btn"
    );
    const inactivity_popup = document.getElementById("activity");
    if (staySignedInButton) {
      staySignedInButton.addEventListener("click", function () {
        clearTimeout(inactivity_dialog);
        clearTimeout(inactivity_logout);
        inactivity_popup.close();
        startInactivityTimeout();
      });
    }
  }

  function startInactivityPopupTimeout() {
    const inactivity_popup = document.getElementById("activity");
    // Logs user out if no response when the inactivity popup shows
    inactivity_logout = setTimeout(function () {
      inactivity_popup.close();
      signOutRedirect();
    }, 1000 * 60 * initial_warning_mins);
  }

  function sessionExpiryPopup() {
    // displays session expiry popup after timeout
    const session_expiry_popup = document.getElementById("expiry");
    if (isLoggedIn()) {
      inactivity_logout = setTimeout(function () {
        if (session_expiry_popup)
        {
          session_expiry_popup.showModal();
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
    return (time - lastActive) < (inactivity_mins * 60 * 1000);
  }

  function lastActiveTimeout() {
    // If activity in another tab, inactivity timeout period adjusted
    const inactivity_popup = document.getElementById("activity");
    let time = new Date();
    let lastActive = new Date(localStorage.getItem("lastActivity"));
    setTimeout(() => {
      inactivity_popup.showModal();
      startInactivityPopupTimeout();
    }, inactivity_mins * 60 * 1000 - (time - lastActive));
  }

  function signOutRedirect() {
    // send logout request and redirect to previous page upon relogging in
    let current_page = window.location.pathname;
    $.ajax("/sign-out", {
      method: "GET",
      success: function() {
        window.location.href = "/sign-in?next="+current_page+"&status=inactive";
      }
    })
      .fail((response) => {
        console.log(response);
      });
  }

  updateLocalStorage();
  sessionExpiryPopup();
  startInactivityTimeout();
  resetTimeouts();

  window.GOVUK.startInactivityTimeout = startInactivityTimeout;
  window.GOVUK.sessionExpiryPopup = sessionExpiryPopup;
  window.GOVUK.signOutRedirect = signOutRedirect;
  window.GOVUK.resetTimeouts = resetTimeouts;
  window.GOVUK.updateLocalStorage = updateLocalStorage;
  window.GOVUK.inactivity_mins = inactivity_mins;
  window.GOVUK.timeout_warning_mins = timeout_warning_mins;
  window.GOVUK.isLoggedIn = isLoggedIn;

})(window);
