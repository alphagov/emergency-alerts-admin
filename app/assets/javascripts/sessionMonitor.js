let initial_popup;
let initial_logout;

let mins = 0.2; // to display first popup
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
    console.log(loggedInTimestamp);
    console.log(new Date() - loggedInTimestamp);
    if (new Date() - loggedInTimestamp > 1000 * 60 * timeout_warning_mins) {
      timeout_popup.style.display = "block";
    }
  }
}

// document.addEventListener('mousemove', function() {
//     resetTimeouts();
// })

sessionExpiryPopup();
startInactivityTimeout();
resetTimeouts();
