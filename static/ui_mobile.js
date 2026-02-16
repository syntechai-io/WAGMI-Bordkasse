(function() {
  'use strict';

  function init() {
    var stickyQuickFill = document.getElementById('sticky-quick-fill');
    var stickySave = document.getElementById('sticky-save');

    if (stickyQuickFill) {
      stickyQuickFill.addEventListener('click', function() {
        var originalBtn = document.getElementById('quick-fill-button');
        if (originalBtn) {
          originalBtn.click();
        }
      });
    }

    if (stickySave) {
      stickySave.addEventListener('click', function() {
        var submitBtn = document.getElementById('logbook-submit-btn');
        if (submitBtn) {
          submitBtn.click();
        }
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
