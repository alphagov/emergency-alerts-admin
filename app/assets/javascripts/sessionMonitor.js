let initial_popup;
let initial_logout;

let mins = 28; // to display first popup
let warning_mins = 2; // to logout if popup not clicked
let timeout_warning_mins = 58; // // to display final popup before logged out

var loggedInTimestamp = new Date(logged_in_at);
var logged_in = (loggedInTimestamp instanceof Date) & !isNaN(loggedInTimestamp);

var inactivity_popup = document.getElementById("popup");
var session_expiry_popup = document.getElementById("timeout_popup");
var resetButton = document.getElementById("popup-button");

function startInactivityTimeout() {
  if (logged_in) {
    console.log("Starting timeout");
    initial_popup = setTimeout(function () {
      inactivity_popup.style.display = "block";
      startInactivityPopupTimeout();
    }, 1000 * 60 * mins);
  } else {
    console.log("Not logged in");
  }
}

function startInactivityPopupTimeout() {
  initial_logout = setTimeout(function () {
    window.location.href = "/sign-out";
  }, 1000 * 60 * warning_mins);
}

function resetTimeouts() {
  if (resetButton) {
    resetButton.addEventListener("click", function () {
      clearTimeout(initial_popup);
      clearTimeout(initial_logout);
      inactivity_popup.style.display = "none";
      startInactivityTimeout();
    });
  }
}

function sessionExpiryPopup() {
  if (logged_in) {
    expiry_time = new Date();
    current_time = new Date();
    expiry_time.setMinutes(
      loggedInTimestamp.getMinutes() + timeout_warning_mins
    );
    initial_logout = setTimeout(function () {
      timeout_popup.style.display = "block";
    }, expiry_time - current_time);
  }
}

sessionExpiryPopup();
startInactivityTimeout();
resetTimeouts();
