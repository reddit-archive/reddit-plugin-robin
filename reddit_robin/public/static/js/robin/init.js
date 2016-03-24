!function(r, $, _) {
  'use strict';

  var models = r.robin.models;
  var views = r.robin.views;

  var RobinChat = Backbone.View.extend({
    SYSTEM_USER_NAME: '[robin]',

    websocketEvents: {
      'connecting': function() {
        this.addSystemAction('connecting');
      },

      'connected': function() {
        this.addSystemAction('connected!');
      },

      'disconnected': function() {
        this.addSystemAction('disconnected :(');
      },

      'reconnecting': function(delay) {
        this.addSystemAction('reconnecting in ' + delay + ' seconds...');
      },

      'message:chat': function(message) {
        if (message.body.indexOf('/me ') === 0) {
          this.addUserAction(message.from, message.body.slice(4));
        } else {
          this.addUserMessage(message.from, message.body);
        }
      },

      'message:vote': function(message) {
        this.updateUserVote(message.from, message.vote);
      },

      'message:join': function(message) {
        this.addUserAction(message.user, 'joined the room');
      },

      'message:part': function(message) {
        this.addUserAction(message.user, 'left the room');
      },

      'message:please_vote': function(message) {
        this.addSystemAction('polls are closing soon, please vote');
      },

      'message:merge': function(message) {
        this.addSystemAction('merging with other room...');
        // TODO: add some jitter before refresh to avoid thundering herd
        $.refresh()
      },

      'message:users_abandoned': function(message) {
        // TODO: how to kick the users and prevent them from receiving
        // additional messages?
      },

      'message:abandon': function(message) {
        this.addSystemAction('room has been abandoned');
      },

      'message:continue': function(message) {
        this.addSystemAction('room has been continued');
      },

      'message:no_match': function(message) {
        this.addSystemAction('no compatible room found for matching');
      },

    },

    roomEvents: {
      'success:vote': function(room, data) {
        this.currentUser.set(data);
      },

      'request:message': function() {
        this.chatInput.disable();
      },

      'invalid:message error:message': function() {
        // TODO handle error better than this
        this.chatInput.clear();
      },

      'success:message': function() {
        this.chatInput.clear();
      },
    },

    roomParticipantsEvents: {
      add: function(user, userList) {
        this.userListWidget.addUser(user);
      },
    },

    roomMessagesEvents: {
      add: function(message, messageList) {
        this.chatWindow.addMessage(message);
      },
    },

    chatInputEvents: {
      'chat': function(messageText) {
        this.chatWindow.scrollToRecent();
      },

      'chat:message': function(messageText) {
        this.room.postMessage(messageText);
      },

      'chat:command': function(command, args) {
        if (typeof this.chatCommands[command] !== 'function') {
          args = [command]
          command = 'unknown';
        } else {
          this.chatInput.clear();
        }

        this.chatCommands[command].apply(this, args);
      },
    },

    voteWidgetEvents: {
      'vote': function(vote) {
        this.room.postVote(vote.toUpperCase());
      },
    },

    chatCommands: {
      'unknown': function(command) {
        this.addSystemMessage('"/' + command + '" is not a command');
      },

      'vote': function(vote) {
        if (!vote) {
          this.addSystemMessage('use: /vote [' + r.robin.VOTE_TYPES.join(',') + ']');
        } else if (r.robin.VOTE_TYPES.indexOf(vote.toUpperCase()) < 0) {
          this.addSystemMessage('that is not a valid vote type');
        } else if (vote.toUpperCase() === this.currentUser.get('vote')) {
          this.addSystemMessage('that is already your vote');
        } else {
          this.room.postVote(vote.toUpperCase());
          this.voteWidget.setActiveVote(vote);
        }
      },

      'me': function(/* args */) {
        var messageText = [].slice.call(arguments).join(' ');

        if (messageText.length > 0) {
          this.room.postMessage('/me ' + messageText);
        } else {
          this.addSystemMessage('use: /me your message here');
        }
      },
    },

    initialize: function(options) {
      this.websocketEvents = this._autobind(this.websocketEvents);
      this.chatCommands = this._autobind(this.chatCommands);

      // initialize some models for managing state
      this.room = new models.RobinRoom({
        room_id: this.options.room_id,
        room_name: this.options.room_name,
      });

      var currentUser;
      var participants = [];

      if (options.participants) {
        options.participants.forEach(function(user) {
          var isCurrentUser = (user.name === options.logged_in_username);
          var modelAttributes = _.clone(user);

          if (isCurrentUser) {
            modelAttributes.userClass = 'self';
            modelAttributes.present = true;
          }

          var userModel = new models.RobinUser(modelAttributes);
          
          if (isCurrentUser) {
            currentUser = userModel;
          }

          participants.push(userModel)
        });
      }

      if (!currentUser) {
        currentUser = new models.RobinUser({
          name: this.options.logged_in_username,
          userClass: 'self',
          present: true,
        });
      }

      this.currentUser = currentUser;
      this.roomParticipants = new models.RobinRoomParticipants(participants);
      this.roomMessages = new models.RobinRoomMessages();

      // initialize some child views 
      this.chatInput = new views.RobinChatInput({
        el: this.$el.find('#robinChatInput')[0],
      });

      this.chatWindow = new views.RobinChatWindow({
        el: this.$el.find('#robinChatWindow')[0],
      });
      
      this.voteWidget = new views.RobinVoteWidget({
        el: this.$el.find('#robinVoteWidget')[0],
      });

      this.userListWidget = new views.RobinUserListWidget({
        el: this.$el.find('#robinUserList')[0],
        participants: participants,
      });

      // set the button state in the voting widget
      if (this.currentUser.hasVoted()) {
        this.voteWidget.setActiveVote(this.currentUser.get('vote'));
      }

      // notifications
      if ('Notification' in window) {
        this.desktopNotifier = new r.robin.notifications.DesktopNotifier({
          model: this.roomMessages,
        });
        this.desktopNotifier.render();
        $('#robinDesktopNotifier')
          .removeAttr('hidden')
          .find('label')
          .prepend(this.desktopNotifier.$el);
      }

      // favicon
      this.faviconUpdater = new r.robin.favicon.UnreadUpdateCounter({
        model: this.roomMessages,
      });

      // wire up events
      this._listenToEvents(this.room, this.roomEvents);
      this._listenToEvents(this.roomParticipants, this.roomParticipantsEvents);
      this._listenToEvents(this.roomMessages, this.roomMessagesEvents);
      this._listenToEvents(this.chatInput, this.chatInputEvents);
      this._listenToEvents(this.voteWidget, this.voteWidgetEvents);

      // initialize websockets. should be last!
      this.websocket = new r.WebSocket(options.websocket_url);
      this.websocket.on(this.websocketEvents);
      this.websocket.start();
    },

    _listenToEvents: function(other, eventMap) {
      for (var key in eventMap) {
        this.listenTo(other, key, eventMap[key]);
      }
    },

    _autobind: function(hash) {
      var bound = {}
      for (var key in hash) {
        bound[key] = hash[key].bind(this);
      }
      return bound;
    },

    _ensureUser: function(userName, setAttrs) {
      var user = this.roomParticipants.get(userName);

      if (!user) {
        user = new models.RobinUser(_.defaults({
          name: userName,
        }, setAttrs));
        this.roomParticipants.add(user);
      } else if (setAttrs) {
        user.set(setAttrs);
      }

      return user;
    },

    addUserMessage: function(userName, messageText) {
      var user = this._ensureUser(userName, { present: true });
      
      var message = new models.RobinMessage({
        author: userName,
        message: messageText,
        userClass: user.get('userClass'),
        flairClass: user.flairClass,
      });

      this.roomMessages.add(message);
    },

    addUserAction: function(userName, actionText) {
      var user = this._ensureUser(userName, { present: true });

      var message = new models.RobinMessage({
        author: userName,
        message: actionText,
        messageClass: 'action',
        userClass: user.get('userClass'),
        flairClass: user.flairClass,
      });

      this.roomMessages.add(message);
    },

    addSystemMessage: function(messageText) {
      var message = new models.RobinMessage({
        author: this.SYSTEM_USER_NAME,
        message: messageText,
        userClass: 'system',
      });

      this.roomMessages.add(message);
    },

    addSystemAction: function (actionText) {
      var message = new models.RobinMessage({
        author: this.SYSTEM_USER_NAME,
        message: actionText,
        messageClass: 'action',
        userClass: 'system',
      });

      this.roomMessages.add(message);
    },

    updateUserVote: function(userName, vote) {
      var setAttrs = {
        vote: vote,
        present: true,
      };
      var user = this._ensureUser(userName, setAttrs);

      this.addUserAction(userName, 'voted to ' + vote);
    },
  });

  $(function() {
    new RobinChat({
      el: document.getElementById('robinChat'),
      room_name: r.config.robin_room_name,
      room_id: r.config.robin_room_id,
      websocket_url: r.config.robin_websocket_url,
      participants: r.config.robin_user_list,
      logged_in_username: r.config.logged,
    });
  });
}(r, jQuery, _);
