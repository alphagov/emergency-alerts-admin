let initial_logout;
let initial_popup;
let timeLeft;

const inactivity_mins = 0.2; // to display first popup
const initial_warning_mins = 0.5; // to logout if no response after popup displayed
const timeout_warning_mins = 2; // // to display final popup before logged out by flask
let logged_in_at_var = "Test"|| logged_in_at; // NEED TO REMOVE BUT FOR NOW FOR TESTS


(function (window) {
  "use strict";

  function isLoggedIn() {
    let loggedInTimestamp;
    if (logged_in_at_var != "Test") {
      console.log('Logged In');
      let loggedInTimestamp = new Date(logged_in_at_var);
    } else {
      console.log('Not logged in');
      let loggedInTimestamp = "";
    }
    return (loggedInTimestamp instanceof Date) & !isNaN(loggedInTimestamp);
  }
  function loggedInAt() {
    let loggedInTimestamp = new Date(logged_in_at_var);
    return loggedInTimestamp;
  }

  function getTimeLeftUntilExpiry() {
    // calculates how long left in session before final timeout after each request
    let expiry_time = new Date();
    expiry_time.setMinutes(
      loggedInAt().getMinutes() + timeout_warning_mins
    );
    let current_time = new Date();
    let timeLeft = expiry_time - current_time;
    return timeLeft;
  }

  function displayInactivityPopup() {
    // check if user logged in and there is enough time left before session expires
    timeLeft = getTimeLeftUntilExpiry();
    console.log(timeLeft);
    return (
      isLoggedIn() &
      (timeLeft > (timeout_warning_mins - inactivity_mins) * 60 * 1000)
    );
  }

  function startInactivityTimeout() {
    // initial timeout that is restarted by request activity
    if (displayInactivityPopup()) {
      initial_popup = setTimeout(function () {
        if (checkLocalStorage()) {
          console.log('Time updated!');
          lastActiveTimeout();
        } else {
          const inactivity_popup = document.getElementById("activity");
          inactivity_popup.setAttribute('open', 'true');
          startInactivityPopupTimeout();
        }
      }, 1000 * 60 * inactivity_mins);
    }
  }

  function resetTimeouts() {
    // if stay signed in button is clicked then activity timeout is restarted
    const staySignedInButton = document.getElementById(
      "hmrc-timeout-keep-signin-btn"
    );
    const inactivity_popup = document.getElementById("activity");
    if (staySignedInButton) {
      staySignedInButton.addEventListener("click", function () {
        clearTimeout(initial_popup);
        clearTimeout(initial_logout);
        console.log('clicked button');
        inactivity_popup.removeAttribute('open');
        startInactivityTimeout();
      });
    }
  }

  function startInactivityPopupTimeout() {
    const inactivity_popup = document.getElementById("activity");
    // logs user out if no response when the inactivity popup shows
    initial_logout = setTimeout(function () {
      inactivity_popup.removeAttribute('open');
      window.location.href = "/sign-out";

    }, 1000 * 60 * initial_warning_mins);
  }

  function sessionExpiryPopup() {
    // displays session expiry popup after timeout
    const session_expiry_popup = document.querySelector("#expiry");
    if (isLoggedIn()) {
      initial_logout = setTimeout(function () {
        if (session_expiry_popup)
        {session_expiry_popup.setAttribute('open', true);}
      }, getTimeLeftUntilExpiry());
    }
  }

  function signInAgain() {
    const signInAgainButton = document.getElementById(
      "hmrc-timeout-sign-in-again-btn"
    );
    const session_expiry_popup = document.querySelector("#expiry");
    // if signin button in final timeout popup is clicked, user is signed out and upon logging back in is redirected to previous page
    if (signInAgainButton) {
      signInAgainButton.addEventListener("click", function () {
        session_expiry_popup.removeAttribute('open');
        signOutRedirect();
      });
    }
  }

  function updateLocalStorage() {
    // with each request in any tab, the lastActive attribute is updated
    localStorage.setItem("lastActivity", new Date());
  }

  function checkLocalStorage() {
    // checking local storage for any activity in other tabs
    let lastActive = new Date(localStorage.getItem("lastActivity"));
    let time = new Date();
    return time - lastActive < inactivity_mins * 60 * 1000;
  }

  function lastActiveTimeout() {
    // if activity in another tab, inactivity timeout period adjusted
    let time = new Date();
    let lastActive = new Date(localStorage.getItem("lastActivity"));
    setTimeout(() => {
      inactivity_popup.setAttribute('open', true);
      startInactivityPopupTimeout();
    }, inactivity_mins * 60 * 1000 - (time - lastActive));
  }

  function signOutRedirect() {
    // send logout request and redirect to previous page upon relogging in
    let current_page = window.location.pathname;
    $.ajax("/sign-out", {
      method: "get",
    })
      .done((response) => {
        window.location.href = current_page;
        console.log(response);
      })
      .fail((response) => {
        console.log(response);
      });
  }

  updateLocalStorage();
  sessionExpiryPopup();
  startInactivityTimeout();
  resetTimeouts();
  signInAgain();

  window.GOVUK.startInactivityTimeout = startInactivityTimeout;
  window.GOVUK.sessionExpiryPopup = sessionExpiryPopup;
  window.GOVUK.signOutRedirect = signOutRedirect;
  window.GOVUK.resetTimeouts = resetTimeouts;
  window.GOVUK.updateLocalStorage = updateLocalStorage;
  window.GOVUK.inactivity_mins = inactivity_mins;
  window.GOVUK.timeout_warning_mins = timeout_warning_mins;
  window.GOVUK.isLoggedIn = isLoggedIn;

})(window);
