/*
 * django-pam
 *
 * by Carl J. Nobile
 */

"use strict";


window.onload = function() {
  var button = document.getElementsByClassName('close-message');

  var handler = function() {
    var alertError = document.getElementsByClassName('alert-error');

    if(alertError.length > 0) {
      alertError[0].style.display = 'none';
    }
  }

  if(button.length > 0) {
    if(button[0].addEventListener) {
      button[0].addEventListener('click', handler, false);
    } else if(button[0].attachEvent) {
      button[0].attachEvent('click', handler);
    }
  }
};
