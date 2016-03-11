!function(r) {
  function joinRoom() {
    r.ajax({
      type: 'POST',
      url: '/api/join_room',
    });

    var d = $.Deferred();

    (function waitForAssignment (i) {
      setTimeout(function () {
        var res = getAssignment();
        if ('roomId' in res.responseJSON) {
          var roomId = res.responseJSON.roomId;
          r.log('got roomId: ' + roomId);
          d.resolve(roomId);
        } else if (i > 0) {
          waitForAssignment(i - 1);
        } else {
          r.log('ran out of time waiting');
          d.reject();
        }
      }, 1000);
    })(10);

    return d.promise();
  }

  function getAssignment() {
    return r.ajax({
      type: 'GET',
      async: false,
      url: '/api/room_assignment.json',
      dataType: 'json',
    });
  }

  $(function() {
    var $theButton = $('#joinRobin');
    var $theButtonContainer = $('#joinRobinContainer');
    
    var mollyGaurded = true;
    var unlocked = false;

    var LOCKED_STATE = 'robin--thebutton-state--locked';
    var UNLOCKING_STATE = 'robin--thebutton-state--unlocking';
    var UNLOCKED_STATE = 'robin--thebutton-state--unlocked';
    var PRESSED_STATE = 'robin--thebutton-state--pressed';


    $theButtonContainer.on('click', function(e) {
      if (mollyGaurded) {
        $theButtonContainer.removeClass(LOCKED_STATE).addClass(UNLOCKING_STATE);

        setTimeout(function() {
          $theButtonContainer.removeClass(UNLOCKING_STATE).addClass(UNLOCKED_STATE);
          unlocked = true;
        }, 300);
      }
    });

    $theButton.on('click', function(e) {
      if (!unlocked) {
        return false;
      }

      e.target.disabled = true;
      $theButtonContainer.addClass(PRESSED_STATE)
      
      joinRoom().then(function onDone(roomId) {
        $.redirect("/robin/" + roomId);
      }, function onFail() {
        e.target.disabled = false;
        $theButtonContainer.removeClass(PRESSED_STATE);
      });

      return false;
    });
  });
}(r);
