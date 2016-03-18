!function(r, undefined) {
  r.robin = r.robin || {};

  var VOTE_TYPES = ['INCREASE', 'CONTINUE', 'ABANDON'];
  var NO_VOTE_TYPE = 'NOVOTE';

  var DEFAULT_USER_CLASS = 'user';
  var USER_CLASSES = ['user', 'self', 'system'];

  var DEFAULT_MESSAGE_CLASS = 'message';
  var MESSAGE_CLASSES = ['message', 'action'];

  function OneOf(attrName, values) {
    return function(model) {
      var value = model.get(attrName);
      if (values.indexOf(value) < 0) {
        return new Error('INVALID_OPTION');
      }
    }
  }

  function IsBool(attrName) {
    return function(model) {
      if (typeof model.get(attrName) !== 'boolean') {
        return new Error('NOT_BOOLEAN')
      }
    }
  }

  function IsString(attrName) {
    return function(model) {
      if (typeof model.get(attrName) !== 'string') {
        return new Error('NOT_STRING');
      }
    }
  }

  /*
    Going to abuse backbone models a little bit for validation
   */
  var _RobinModel = Backbone.Model.extend({
    validate: function(attrs) {
      return r.models.validators.validate(this, this.validators);
    },

    sync: function() {
      throw new Error('UNIMPLEMENTED');
    },
  });


  var RobinMessage = _RobinModel.extend({
    MAX_LENGTH: 140,

    validators: [
      r.models.validators.StringLength('message', 1, this.MAX_LENGTH),
      OneOf('messageClass', MESSAGE_CLASSES),
      OneOf('userClass', USER_CLASSES),
    ],

    defaults: {
      author: '',
      message: '',
      messageClass: DEFAULT_MESSAGE_CLASS,
      userClass: DEFAULT_USER_CLASS,
    },
  });


  var RobinVote = _RobinModel.extend({
    validators: [
      OneOf('vote', VOTE_TYPES),
    ],

    defaults: {
      vote: NO_VOTE_TYPE,
    },
  });


  var RobinUser = _RobinModel.extend({
    idAttribute: 'name',

    validators: [
      IsString('name'),
      OneOf('userClass', USER_CLASSES),
      OneOf('vote', VOTE_TYPES),
      IsBool('present'),
    ],

    defaults: {
      name: null,
      userClass: DEFAULT_USER_CLASS,
      vote: NO_VOTE_TYPE,
      present: false,
    },

    
    hasVoted: function() {
      return this.get('vote') !== NO_VOTE_TYPE;
    },

    set: function(attrs, options) {
      var _args = [attrs].concat(Object.keys(RobinUser.prototype.defaults));
      attrs = _.pick.apply(_, _args);
      return RobinUser.__super__.set.call(this, attrs, options);
    },
  });


  var RobinRoomParticipants = Backbone.Collection.extend({
    model: RobinUser,
  });


  var RobinRoomMessages = Backbone.Collection.extend({
    model: RobinMessage,
  });


  var RobinRoom = Backbone.Model.extend({
    idAttribute: 'room_id',

    defaults: {
      room_id: null,
      room_name: null,
      api_type: 'json',
    },

    postMessage: function(messageText) {
      var message = new RobinMessage({
        message: messageText,
      });
      var err = message.validate();

      if (err) {
        this.trigger('invalid:message', this, err);
      } else {
        this._post('message', message);
      }

    },

    postVote: function(voteType) {
      var vote = new RobinVote({
        vote: voteType,
      });

      var err = vote.validate();
      
      if (err) {
        this.trigger('invalid:vote', this, err);
        this.trigger('invalid', this, err);
      } else {
        this._post('vote', vote);
      }
    },

    _getPostData: function(models) {
      var models = [this].concat(models);
      var jsonBlobs = models.map(function(m) { return m.toJSON() });
      return _.defaults.apply(_, jsonBlobs);
    },

    _post: function(endpoint /*, models*/) {
      var models = [].slice.call(arguments, 1);
      var data = this._getPostData(models);

      this.trigger('request:endpoint', this);
      this.trigger('request', this);

      r.ajax({
        type: 'POST',
        url: '/api/robin/' + r.config.robin_room_id + '/' + endpoint,
        data: data,
        success: function(res) {
          var errors = r.errors.getAPIErrorsFromResponse(res);
        
          if (errors) {
            this.trigger('error:' + endpoint, this, errors);
            this.trigger('error', this, errors);
          } else {
            this.trigger('success:' + endpoint, this, data);
            this.trigger('success', this, data);
          }
        }.bind(this),

        error: function(res) {
          this.trigger('error:' + endpoint, this, res);
          this.trigger('error', this, res);
        }.bind(this),
      });
    },
  });


  r.robin.VOTE_TYPES = VOTE_TYPES;
  r.robin.models = {
    RobinUser: RobinUser,
    RobinMessage: RobinMessage,
    RobinRoomParticipants: RobinRoomParticipants,
    RobinRoomMessages: RobinRoomMessages,
    RobinVote: RobinVote,
    RobinRoom: RobinRoom,
  };
}(r);
