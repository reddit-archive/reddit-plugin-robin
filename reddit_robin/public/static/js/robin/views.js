!function(r, $, _) {
  r.robin = r.robin || {};

  var RobinChatWindow = Backbone.View.extend({
    TEMPLATE_NAME: 'robin/robinmessage',

    initialize: function() {
      this.$chatList = this.$el.find('#robinChatMessageList');
      this.lastMessageFrom = null;
    },

    addMessage: function(message) {
      var date = new Date();
      var time = date.toLocaleTimeString ? date.toLocaleTimeString() : date.toTimeString();      
      var scrollOffset = (this.$el.prop('scrollHeight') - this.$el.scrollTop());
      var wasScrolledDown = (scrollOffset === this.$el.height());

      var templateData = _.extend(message.toJSON(), {
        isoDate: date.toISOString(),
        timestamp: time,
      });

      if (message.get('messageClass') !== 'message') {
        this.lastMessageFrom = null;
      } else if (message.get('author') === this.lastMessageFrom) {
        templateData.displayCompact = true;
      } else {
        this.lastMessageFrom = message.get('author');
      }

      var el = r.templates.make(this.TEMPLATE_NAME, templateData);
      this.$chatList.append(el);

      if (wasScrolledDown) {
        this.el.scrollTop = this.el.scrollHeight;
      }
    },
  });


  var RobinChatInput = Backbone.View.extend({
    events: {
      'submit #robinSendMessage': '_onMessage',
    },

    initialize: function() {
      this.form = $('#robinSendMessage')[0];
    },

    _onMessage: function(e) {
      e.preventDefault();
      var messageText = this.form.message.value;
      if (messageText[0] !== '/') {
        this.trigger('chat:message', messageText);
      } else {
        var commandArgs = messageText.slice(1).split(/\s+/);
        if (commandArgs[0]) {
          this.trigger('chat:command', commandArgs[0], commandArgs.slice(1));
        }
      }
    },

    disable: function() {
      this.form.message.disabled = true;
    },

    enable: function() {
      this.form.message.disabled = false;
    },

    clear: function() {
      this.enable();
      this.form.message.value = '';
    },
  });


  var RobinVoteWidget = Backbone.View.extend({
    ACTIVE_STATE_CLASS: 'robin--active',
    CONFIRM_BUTTON_CLASS: 'robin-chat--confirm',
    VOTE_BUTTON_CLASS: 'robin-chat--vote',
    CONFIRMED_STATE_CLASS: 'robin--vote-confirmed',

    currentTarget: null,

    events: {
      'click .robin-chat--vote': '_onVote',
      'click .robin-chat--confirm': '_onConfirm',
    },

    initialize: function() {
      this._confirmed = false;
    },

    _onVote: function(e) {
      if (this._confirmed) {
        e.target.blur();
        return;
      }

      var value = e.target.value;
      this.trigger('vote', value);
      this._setActiveTarget(e.target);
    },

    _onConfirm: function(e) {
      if (!this.currentTarget) { return; }
      if (this._confirmed) { return; }

      this.trigger('confirm');
      this.setConfirmedState();
    },

    _setActiveTarget: function(el) {
      if (this.currentTarget) {
        $(this.currentTarget).removeClass(this.ACTIVE_STATE_CLASS);
      } else {
        this.$el.find('.' + this.CONFIRM_BUTTON_CLASS).removeAttr('disabled');
      }

      if (el) {
        this.currentTarget = el;
        $(this.currentTarget).addClass(this.ACTIVE_STATE_CLASS);
      }
    },

    setConfirmedState: function() {
      if (this._confirmed) {
        throw new Error('RobinVoteWidget: cannot set confirmed state, vote is already confirmed');
      }

      this.$el.find('.' + this.CONFIRM_BUTTON_CLASS).addClass(this.ACTIVE_STATE_CLASS);
      this.$el.addClass(this.CONFIRMED_STATE_CLASS);
      this._confirmed = true;
      this.$el.find('button').attr('disabled', true);
    },

    setActiveVote: function(voteType) {
      if (this._confirmed) {
        throw new Error('RobinVoteWidget: channot change active vote, vote is already confirmed');
      }

      var selector = '.' + this.VOTE_BUTTON_CLASS + '-' + voteType.toLowerCase();
      var el = this.$el.find(selector)[0];
      this._setActiveTarget(el);
    },
  });


  var RobinUserListWidget = Backbone.View.extend({
    TEMPLATE_NAME: 'robin/robinroomparticipant',

    initialize: function(options) {
      if (options.participants) {
        options.participants.forEach(this.addUser.bind(this));
      }
    },

    addUser: function(user) {
      var $el = $(this.render(user));
      this.$el.append($el);

      this.listenTo(user, 'change', function() {
        var $newEl = $(this.render(user));
        $el.before($newEl);
        $el.remove();
        $el = $newEl;
      });
    },

    render: function(user) {
      var templateData = {
        from: user.get('name'),
        userClass: user.get('userClass'),
        voteClass: user.get('vote').toLowerCase(),
        confirmClass: user.get('confirmed') ? 'confirmed' : 'unconfirmed',
        presenceClass: user.get('present') ? 'present' : 'away',
      };
      return r.templates.make(this.TEMPLATE_NAME, templateData);
    },
  });


  r.robin.views = {
    RobinChatWindow: RobinChatWindow,
    RobinChatInput: RobinChatInput,
    RobinVoteWidget: RobinVoteWidget,
    RobinUserListWidget: RobinUserListWidget,
  };
}(r, jQuery, _);
