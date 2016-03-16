/* page visibility api polyfill by spladug. MIT license. */
;(function(window, document, undefined) {
  if (document.hidden !== undefined) {
    return;
  }

  var prefixes = ['webkit', 'o', 'ms', 'moz'];
  for (var i = 0; i < prefixes.length; i++) {
    var prefix = prefixes[i];

    if (document[prefix + 'Hidden'] !== undefined) {
      var event = new Event('visibilitychange');
      document.addEventListener(prefix + 'visibilitychange', function () {
        document.dispatchEvent(event);
      });

      Object.defineProperty(document, 'hidden', {
        get: function () {
          return document[prefix + 'Hidden'];
        }
      });

      Object.defineProperty(document, 'visibilityState', {
        get: function () {
          return document[prefix + 'VisibilityState'];
        }
      });

      return;
    }
  }
}(this, document));
