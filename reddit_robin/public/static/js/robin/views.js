!function(r, $, _) {
  r.robin = r.robin || {};

  var RobinChatWindow = Backbone.View.extend({
    TEMPLATE_NAME: 'robin/robinmessage',

    CHAR_CLASS: 'robin-message--character',
    SPACE_CHAR_CLASS: 'robin-message--space-character',
    JUICE_CLASS: 'robin--animation-class--juicy-pop',

    JUICY_POP_INTERVAL: 200,
    _juicyPopInterval: null,

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
        this.scrollToRecent();
      }
    },

    scrollToRecent: function() {
      this.el.scrollTop = this.el.scrollHeight;
    },

    juicyPop: function() {
      var $el = this.$chatList.children(':not(.' + this.JUICE_CLASS + ')').last();
      if (!$el.length) { return false; }

      this.lastMessageFrom = null;

      var $message = $el.find('.robin-message--message');
      var messageText = $message.text();
      var charElements = [];
      var $char;

      for (var i = 0; i < messageText.length; i++) {
        $char = $($.parseHTML('<span></span>'));
        $char.text(messageText[i]);
        if (messageText[i] !== ' ') {
          $char.addClass(this.CHAR_CLASS);
        } else {
          $char.addClass(this.SPACE_CHAR_CLASS);
        }
        $char.css({
          'transition-delay': Math.floor(Math.random() * 1000) + 'ms',
        })
        charElements.push($char);
      }

      $message.empty().append(charElements);

      setTimeout(function() {
        $el.addClass(this.JUICE_CLASS);
      }.bind(this), 10);

      setTimeout(function() {
        $el.remove();
      }.bind(this), 1500);

      return true;
    },

    startJuicyPoppin: function() {
      console.log('started');
      this._juicyPopInterval = setInterval(function() {
        console.log('poppin');
        var popped = this.juicyPop();
        if (!popped) {
          this.stopJuicyPoppin();
        }
      }.bind(this), this.JUICY_POP_INTERVAL);
    },

    stopJuicyPoppin: function() {
      console.log('stopped');
      this._juicyPopInterval = clearInterval(this._juicyPopInterval);
    },
  });


  var RobinChatInput = Backbone.View.extend({
    LAST_WORD_REGEX: /[^\s]+$/,
    _autoCompleting: false,
    _autoCompleteIndex: 0,
    _autoCompleteValues: null,

    events: {
      'submit #robinSendMessage': '_onMessage',
      'keydown input[type=text]': '_onKeydown',
    },

    initialize: function() {
      this.form = $('#robinSendMessage')[0];
    },

    _onMessage: function(e) {
      e.preventDefault();
      var messageText = this.form.message.value;
      if (messageText[0] !== '/') {
        this.trigger('chat', messageText);
        this.trigger('chat:message', messageText);
      } else {
        var commandArgs = messageText.slice(1).split(/\s+/);
        if (commandArgs[0]) {
          this.trigger('chat', messageText);
          this.trigger('chat:command', commandArgs[0], commandArgs.slice(1));
        }
      }
    },

    _onKeydown: function(e) {
      if (!this.collection) { return;}
      
      if (e.keyCode !== 9) {
        // keyCode 9 == tab key, ignore everything but tabs
        this._autoCompleting = false;
        return;
      }

      if (this._autoCompleting) {
        // cycle to the next match
        e.preventDefault();
        this._nextAutoComplete();
        return;
      }
        
      var messageText = this.form.message.value;
      if (!messageText) { return; }

      var match = messageText.match(this.LAST_WORD_REGEX);
      if (!match) { return; }

      e.preventDefault();
      this._startAutoComplete(match[0]);
   },

   _startAutoComplete: function(term) {
      var regExp = new RegExp('^' + term);
      var modelMatches = this.collection.filter(function(model) {
        return regExp.test(model.get('name'));
      });

      if (!modelMatches.length) { return; }

      this._autoCompleting = true;
      this._autoCompleteIndex = 0;
      this._autoCompleteValues = modelMatches.map(function(model) {
        return model.get('name');
      });
      this._nextAutoComplete();
    },

    _nextAutoComplete: function() {
      var messageText = this.form.message.value;
      var suggestedWord = this._autoCompleteValues[this._autoCompleteIndex];
      var replacedText = messageText.replace(this.LAST_WORD_REGEX, suggestedWord);
      this.form.message.value = replacedText;
      this._autoCompleteIndex = (this._autoCompleteIndex + 1) % this._autoCompleteValues.length;
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


  var RobinButtonWidget = Backbone.View.extend({
    ACTIVE_STATE_CLASS: 'robin--active',

    isHidden: false,
    currentTarget: null,

    initialize: function(options) {
      this.isHidden = !!options.isHidden;

      if (this.isHidden) {
        this.$el.hide();
      } else if (!this.isHidden) {
        this.$el.show();
      }

      this.$el.removeAttr('hidden');
    },

    hide: function() {
      this.isHidden = true;
      this.$el.slideUp();
    },

    show: function() {
      this.isHidden = false;
      this.$el.slideDown();
    },

    _setActiveTarget: function(el) {
      if (this.currentTarget) {
        $(this.currentTarget).removeClass(this.ACTIVE_STATE_CLASS);
      }

      if (el) {
        this.currentTarget = el;
        $(this.currentTarget).addClass(this.ACTIVE_STATE_CLASS);
      }
    },
  })

  var RobinVoteWidget = RobinButtonWidget.extend({
    VOTE_BUTTON_CLASS: 'robin-chat--vote',
    VOTE_LABEL_CLASS: 'robin-chat--vote-label',

    events: {
      'click .robin-chat--vote': '_onVote',
    },

    _onVote: function(e) {
      if (this.isHidden) { return; }
      var target = $(e.target).closest('button')[0];
      if (target === this.currentTarget) { return; }

      var value = target.value;
      this.trigger('vote', value);
      this._setActiveTarget(target);
    },

    setActiveVote: function(voteType) {
      var selector = '.' + this.VOTE_BUTTON_CLASS + '-' + voteType.toLowerCase();
      var el = this.$el.find(selector)[0];
      this._setActiveTarget(el);
    },
  });


  var RobinQuitWidget = RobinButtonWidget.extend({
    isHidden: true,

    events: {
      'click .robin-chat--quit': '_onQuit',
    },

    _onQuit: function(e) {
      if (this.isHidden) { return; }

      this.trigger('quit');
      this._setActiveTarget(e.target);
    },
  });


  var RobinUserListOverflowIndicator = Backbone.View.extend({
    className: 'robin-user-list-overflow-indicator',

    initialize: function(options) {
      this.render({ count: options.count || 0 })
    },

    render: function(params) {
      this.$el.text(r._('and %(count)s more').format(params));
    },
  });


  var RobinUserListWidget = Backbone.View.extend({
    TEMPLATE_NAME: 'robin/robinroomparticipant',

    length: 0,
    maxDisplayLength: Infinity,

    initialize: function(options) {
      this.userNamesToEl = {};

      if (_.isNumber(options.maxDisplayLength) && !_.isNaN(options.maxDisplayLength)) {
        this.maxDisplayLength = options.maxDisplayLength;
      }

      if (options.participants) {
        options.participants.forEach(this.addUser.bind(this));
      }
    },

    addUser: function(user) {
      this.length += 1;

      if (this.length <= this.maxDisplayLength) {
        var $el = $(this.render(user));
        this.$el.append($el);
        this.userNamesToEl[user.get('name')] = $el;

        this.listenTo(user, 'change', function() {
          var $newEl = $(this.render(user));
          $el.before($newEl);
          $el.remove();
          $el = $newEl;
          this.userNamesToEl[user.get('name')] = $el;
        });
      } else if (this.length === this.maxDisplayLength + 1) {
        this.overflowIndicator = new RobinUserListOverflowIndicator({
          count: this.length - this.maxDisplayLength,
        });
        this.$el.append(this.overflowIndicator.el);
      } else {
        this.overflowIndicator.render({
          count: this.length - this.maxDisplayLength,
        });
      }
    },

    removeUser: function(user) {
      this.stopListening(user);
      var $el = this.userNamesToEl[user.get('name')];

      if (!$el) { return; }

      $el.remove();
    },

    render: function(user) {
      var templateData = {
        from: user.get('name'),
        userClass: user.get('userClass'),
        voteClass: user.get('vote').toLowerCase(),
        presenceClass: user.get('present') ? 'present' : 'away',
      };
      return r.templates.make(this.TEMPLATE_NAME, templateData);
    },
  });


  r.robin.views = {
    RobinChatWindow: RobinChatWindow,
    RobinChatInput: RobinChatInput,
    RobinVoteWidget: RobinVoteWidget,
    RobinQuitWidget: RobinQuitWidget,
    RobinUserListWidget: RobinUserListWidget,
  };
}(r, jQuery, _);
