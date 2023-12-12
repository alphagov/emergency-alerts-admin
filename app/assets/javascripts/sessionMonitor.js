sessionMonitor = function(options) {
    "use strict";
    console.log('Before defaults')
    var defaults = {
            // Session lifetime (milliseconds)
            sessionLifetime: 2 * 60 * 1000,
            // Amount of time before session expiration when the warning is shown (milliseconds)
            timeBeforeWarning: 1 * 60 * 1000,
            // Minimum time between pings to the server (milliseconds)
            minPingInterval: 1 * 60 * 1000,
            // Space-separated list of events passed to $(document).on() that indicate a user is active
            activityEvents: 'mouseup',
            // URL used to log out when the user clicks a "Log out" button
            logoutUrl: '/sign-out',
            // URL used to log out when the session times out
            timeoutUrl: '/sign-out?timeout=1',
            logout: function() {
                // Go to the logout page.
                window.location.href = self.logoutUrl;
                console.log('logout')
            },
            onwarning: function() {
                // Below is example code to demonstrate basic functionality. Use this to warn
                // the user that the session will expire and allow the user to take action.
                // Override this method to customize the warning.
            },
            onbeforetimeout: function() {
                // By default this does nothing. Override this method to perform actions
                // (such as saving draft data) before the user is automatically logged out.
                // This may optionally return a jQuery Deferred object, in which case
                // ontimeout will be executed when the deferred is resolved or rejected.
            },
            ontimeout: function() {
                // Go to the timeout page.
                window.location.href = self.logoutUrl;
                console.log('logging out')
            }
        },
        self = {},
        _warningTimeoutID,
        _expirationTimeoutID,
        // The time of the last ping to the server.
        _lastPingTime = 0;

    function extendsess() {
        // Extend the session expiration. Ping the server and reset the timers if
        // the minimum interval has passed since the last ping.
        var now = $.now(),
            timeSinceLastPing = now - _lastPingTime;

        if (timeSinceLastPing > self.minPingInterval) {
            _lastPingTime = now;
            _resetTimers();
            self.ping();
        }
    }

    function _resetTimers() {
        // Reset the session warning and session expiration timers.
        var warningTimeout = self.sessionLifetime - self.timeBeforeWarning;

        window.clearTimeout(_warningTimeoutID);
        window.clearTimeout(_expirationTimeoutID);
        _warningTimeoutID = window.setTimeout(self.onwarning, warningTimeout);
        _expirationTimeoutID = window.setTimeout(_onTimeout, self.sessionLifetime);
    }

    function _onTimeout() {
        // A wrapper that calls onbeforetimeout and ontimeout and supports asynchronous code.
        $.when(self.onbeforetimeout()).always(self.ontimeout);
        console.log('Ping')
    }

    // Add default variables and methods, user specified options, and non-overridable
    // public methods to the session monitor instance.
    $.extend(self, defaults, options, {
        extendsess: extendsess
    });
    // Set an event handler to extend the session upon user activity (e.g. mouseup).
    $(document).on(self.activityEvents, extendsess);
    // Start the timers and ping the server to ensure they are in sync with the backend session expiration.
    extendsess();

    return self;
};
