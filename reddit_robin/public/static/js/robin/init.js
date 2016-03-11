!function(r, $, _) {
  'use strict';

  var models = r.robin.models;
  var views = r.robin.views;

  var RobinChat = Backbone.View.extend({
    websocketEvents: {
      'connecting': function() {
        this.addSystemMessage('connecting');
      },

      'connected': function() {
        this.addSystemMessage('connected!');
      },

      'disconnected': function() {
        this.addSystemMessage('disconnected :(');
      },

      'reconnecting': function(delay) {
        this.addSystemMessage('reconnecting in ' + delay + ' seconds...');
      },

      'message:chat': function(message) {
        this.addChatMessage(message.from, message.body);
      },

      'message:vote': function(message) {
        this.updateUserVote(message.from, message.vote, message.confirmed);
      },

      'message:join': function(message) {
        this.addSystemMessage(message.user + ' has joined the room');
      },

      'message:part': function(message) {
        this.addSystemMessage(message.user + ' has left the room');
      },
    },

    roomEvents: {
      'success:vote': function(room, data) {
        if (data.confirmed) {
          this.addSystemMessage('you have confirmed your vote of ' + data.vote);
        } else {
          this.addSystemMessage('you have voted: ' + data.vote);
        }

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

    chatInputEvents: {
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

      'confirm': function() {
        var vote = this.currentUser.get('vote');
        this.room.postVote(vote, true);
      },
    },

    chatCommands: {
      'unknown': function(command) {
        this.addSystemMessage('"/' + command + '" is not a command');
      },

      'vote': function(vote) {
        if (!this.currentUser.canVote()) {
          this.addSystemMessage('you have already confirmed your vote of ' + this.currentUser.get('vote'));
        } else if (!vote) {
          this.addSystemMessage('use: /vote [' + r.robin.VOTE_TYPES.join(',') + ']');
        } else if (r.robin.VOTE_TYPES.indexOf(vote.toUpperCase()) < 0) {
          this.addSystemMessage('that is not a valid vote type');
        } else {
          this.room.postVote(vote.toUpperCase());
          this.voteWidget.setActiveVote(vote);
        }
      },

      'confirm': function() {
        var vote = this.currentUser.get('vote');
        var confirmed = this.currentUser.get('confirmed');

        if (this.currentUser.canConfirm()) {
          this.room.postVote(vote, true);
          this.voteWidget.setConfirmedState();
        } else if (confirmed) {
          this.addSystemMessage('you have already confirmed your vote of ' + vote);
        } else {
          this.addSystemMessage('you have not voted yet');
        }
      },
    },

    initialize: function(options) {
      this.websocketEvents = this._autobind(this.websocketEvents);
      this.chatCommands = this._autobind(this.chatCommands);

      // initialize some models for managing state
      this.room = new models.RobinRoom({
        room_id: this.options.room_id,
      });

      this.systemUser = new models.RobinUser({
        name: '[robin]',
        userClass: 'system',
        present: true,
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
      if (this.currentUser.canConfirm() || this.currentUser.isConfirmed()) {
        this.voteWidget.setActiveVote(this.currentUser.get('vote'));
      }

      if (this.currentUser.isConfirmed()) {
        this.voteWidget.setConfirmedState();
      }

      // wire up events
      this._listenToEvents(this.room, this.roomEvents);
      this._listenToEvents(this.roomParticipants, this.roomParticipantsEvents);
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

    addChatMessage: function(userName, messageText) {
      var user = this._ensureUser(userName, { present: true });
      var message = new models.RobinMessage({
        message: messageText,
      });

      this.chatWindow.addMessage(user, message);
    },

    addSystemMessage: function(messageText) {
      var message = new models.RobinMessage({
        message: messageText,
      });

      this.chatWindow.addMessage(this.systemUser, message);
    },

    updateUserVote: function(userName, vote, confirmed) {
      var setAttrs = {
        vote: vote,
        confirmed: confirmed,
        present: true,
      };
      var user = this._ensureUser(userName, setAttrs);

      if (confirmed) {
        this.addSystemMessage(userName + ' confirmed their vote to ' + vote);
      } else {
        this.addSystemMessage(userName + ' voted to ' + vote);
      }
    },
  });

  $(function() {
    new RobinChat({
      el: document.getElementById('robinChat'),
      room_id: r.config.robin_room_id,
      websocket_url: r.config.robin_websocket_url,
      participants: r.config.robin_user_list,
      logged_in_username: r.config.logged,
    });
  });
}(r, jQuery, _);
