(function (window) {
    "use strict";

    const lcase = "abcdefghijklmnopqrstuvwxyz";
    const ucase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    const numb = "1234567890";
    const symbol = "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~ ";

    let strengthBar = document.getElementById("meter");
    let strengthText = document.getElementById("password-strength");

    const setColour = function(entropy, strengthBar) {
        if (entropy < 33 ){
            strengthBar.style.setProperty('--progress-bar-color', "#D4351C");
        } else if (33 < entropy && entropy < 66) {
            strengthBar.style.setProperty('--progress-bar-color', "#F47738");
        }
        if (entropy > 70) {
            strengthBar.style.setProperty('--progress-bar-color', '#00703C');
        }
    };

    const setText = function(entropy) {
        if (entropy < 33 ){
            strengthText.innerText = "Weak";
            strengthText.style.color = "#D4351C";
        } else if (33 < entropy && entropy < 66) {
            strengthText.innerText = "Medium";
            strengthText.style.color = "#F47738";
        }
        if (entropy > 70) {
            strengthText.innerText = "Strong";
            strengthText.style.color = "#00703C";
        }
    };

    const _includesChar = function(text, charlist) {
        for (let i = 0;i < text.length; i++) {
        if (charlist.includes(text[i]))
            return true;
        }
        return false;
    };

    const calculateEntropy = function(password) {
        if (typeof password !== "string")
        return 0;
        let pool = 0;
        if (_includesChar(password, lcase))
        pool += lcase.length;
        if (_includesChar(password, ucase))
        pool += ucase.length;
        if (_includesChar(password, numb))
        pool += numb.length;
        if (_includesChar(password, symbol))
        pool += symbol.length;
        if (!_includesChar(password, lcase + ucase + numb + symbol))
        pool += 100;
        if (pool == 0)
        return 0;
        return (password.length * Math.log(pool) / Math.LN2).toFixed(2);
    };

    window.GOVUK.setColour = setColour;
    window.GOVUK.setText = setText;
    window.GOVUK._includesChar = _includesChar;
    window.GOVUK.calculateEntropy = calculateEntropy;

})(window);
