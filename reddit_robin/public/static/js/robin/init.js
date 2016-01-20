!function(r, $, _) {
  'use strict';

  var $chat = $('#chat');
  function addChatMessage(message) {
    var scrollOffset = ($chat.prop('scrollHeight') - $chat.scrollTop());
    var wasScrolledDown = (scrollOffset === $chat.height());

    console.log('scroll state = ' + wasScrolledDown);

    var $el = $('<p>').text(message);
    $chat.append($el);

    if (wasScrolledDown) {
      chat.scrollTop = chat.scrollHeight;
    }
  }

  var websocket = new r.WebSocket(r.config.robin_websocket_url);
  websocket.on({
    'connecting': function() {
      addChatMessage('connecting');
    },

    'connected': function() {
      addChatMessage('connected!');
    },

    'disconnected': function() {
      addChatMessage('disconnected :(');
    },

    'reconnecting': function(delay) {
      addChatMessage('reconnecting in ' + delay + ' seconds...');
    },

    'message:chat': function(message) {
      addChatMessage('<' + message.from + '> ' + message.body);
    },
  });
  websocket.start();

  $('#send-message').submit(function (ev) {
    ev.preventDefault();

    var $form = $(this);
    post_pseudo_form('#send-message', 'robin/' + r.config.robin_room_id + '/message');

    $form.find('[type=text]').val('');
  });
}(r, jQuery, _);
