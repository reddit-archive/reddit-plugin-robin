!function(r, Backbone, $, _, store) {
  'use strict'

  var exports = r.robin.notifications = {}
  var NOTIFICATION_TTL_SECONDS = 10

  function ellipsize(text, limit) {
    if (text.length > limit) {
      return text.substring(0, limit) + '…'
    }
    return text
  }

  exports.DesktopNotifier = Backbone.View.extend({
    tagName: 'input',
    
    attributes: {
      'type': 'checkbox',
      'name': 'robin-desktop-notifier'
    },

    events: {
      'change': 'onSettingsChange',
    },

    initialize: function() {
      this.storageKey = 'robin.notifications'
      this.requestingPermission = false
      if (Notification.permission === 'granted') {
        this.notificationsDesired = store.safeGet(this.storageKey)
      } else {
        this.notificationsDesired = false
      }
      this.notifications = []
      this.listenTo(this.model, 'add', this.onNewUpdate)
      $(document).on('visibilitychange', $.proxy(this, 'onVisibilityChange'))
    },

    shouldNotify: function() {
      return (
          this.notificationsDesired &&
          Notification.permission === 'granted' &&
          document.hidden
      )
    },

    onNewUpdate: function(update, collection, options) {
      // don't want to notify anyway
      if (!this.shouldNotify()) {
        return
      }

      var author = update.get('author');
      var message = update.get('message');

      if (author === r.config.logged) {
        // never notify a user about their own posts
        return
      } else if (message.indexOf(r.config.logged) < 0) {
        // only notify a user if the message contains their name;
        return;
      }

      var notification = new Notification(author, {
        body: ellipsize(message, 160),
        icon: r.utils.staticURL('robin-icons/robin-icon-robin-big.png'),
      })
      this.notifications.push(notification)

      notification.onclick = function(ev) {
        window.focus()
        ev.preventDefault()
      }

      notification.onclose = function(ev) {
        var index = this.notifications.indexOf(ev.target)
        this.notifications.splice(index, 1)
      }.bind(this);

      setTimeout(function() {
        notification.close()
      }, NOTIFICATION_TTL_SECONDS * 1000)
    },

    onVisibilityChange: function() {
      if (!document.hidden) {
        this.clearNotifications()
      }
    },

    onSettingsChange: function() {
      this.notificationsDesired = this.$el.prop('checked')

      store.safeSet(this.storageKey, this.notificationsDesired)

      if (this.notificationsDesired && Notification.permission !== 'granted') {
        this.requestPermission()
      }
    },

    requestPermission: function() {
      this.requestingPermission = true

      Notification.requestPermission(_.bind(this.onPermissionChange, this))

      this.render()
    },

    onPermissionChange: function() {
      this.requestingPermission = false
      this.render()
    },

    clearNotifications: function() {
      _.invoke(this.notifications, 'close')
    },

    render: function() {
      this.$el
        .prop('disabled', this.requestingPermission || Notification.permission === 'denied')
        .prop('checked', this.notificationsDesired)
      return this
    },
  })
}(r, Backbone, jQuery, _, store)
