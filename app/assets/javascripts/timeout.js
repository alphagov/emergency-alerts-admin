let initial_popup;
let initial_logout;

const inactivity_mins = 0.5; // to display first popup
const initial_warning_mins = 1; // to logout if no response after popup displayed
const timeout_warning_mins = 4; // // to display final popup before logged out by flask

let loggedInTimestamp = new Date(logged_in_at);
let isLoggedIn =
  (loggedInTimestamp instanceof Date) & !isNaN(loggedInTimestamp);

let inactivity_popup = document.getElementById("activity");
let session_expiry_popup = document.getElementById("expiry");

let staySignedInButton = document.getElementById(
  "hmrc-timeout-keep-signin-btn"
);
let signInAgainButton = document.getElementById(
  "hmrc-timeout-sign-in-again-btn"
);

function getTimeLeftUntilExpiry() {
  // calculates how long left in session before final timeout after each request
  let expiry_time = new Date();
  expiry_time.setMinutes(loggedInTimestamp.getMinutes() + timeout_warning_mins);
  let current_time = new Date();
  let timeLeft = expiry_time - current_time;
  return timeLeft;
}

function displayInactivityPopup() {
  // check if user logged in and there is enough time left before session expires
  timeLeft = getTimeLeftUntilExpiry();
  return (
    isLoggedIn &
    (timeLeft > (timeout_warning_mins - inactivity_mins) * 60 * 1000)
  );
}

function startInactivityTimeout() {
  // initial timeout that is restarted by request activity
  if (displayInactivityPopup()) {
    initial_popup = setTimeout(function () {
      if (checkLocalStorage()) {
        lastActiveTimeout();
      } else {
        inactivity_popup.open = true;
        startInactivityPopupTimeout();
      }
    }, 1000 * 60 * inactivity_mins);
  }
}

function resetTimeouts() {
  // if stay signed in button is clicked then activity timeout is restarted
  if (staySignedInButton) {
    staySignedInButton.addEventListener("click", function () {
      clearTimeout(initial_popup);
      clearTimeout(initial_logout);
      inactivity_popup.open = false;
      startInactivityTimeout();
    });
  }
}

function startInactivityPopupTimeout() {
  // logs user out if no response when the inactivity popup shows
  initial_logout = setTimeout(function () {
    window.location.href = "/sign-out";
  }, 1000 * 60 * initial_warning_mins);
}

function sessionExpiryPopup() {
  // displays session expiry popup after timeout
  if (isLoggedIn) {
    initial_logout = setTimeout(function () {
      session_expiry_popup.open = true;
    }, getTimeLeftUntilExpiry());
  }
}

function signInAgain() {
  // if signin button in final timeout popup is clicked, user is signed out and upon logging back in is redirected to previous page
  if (signInAgainButton) {
    signInAgainButton.addEventListener("click", function () {
      signOutRedirect();
      session_expiry_popup.open = false;
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
    inactivity_popup.open = true;
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
