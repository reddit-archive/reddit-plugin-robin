!function(r, Backbone, Tinycon, $) {
  'use strict'

  var exports = r.robin.favicon = {}

  var FAVICON = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADwAAAA8CAYAAAA6/NlyAAAEfUlEQVRoQ+2ZXYhUZRzGn+ec3ZkzzqpZiYZlF2UFgn1RO6OIXkRk5e7syhAipZEt3QQhBAUaW2jURvSxUrq7dJGRwYrurIQUSSbqzBaFBV4Y3UR0sfQFm7pzZmfOE7NZ6O66550Z150dz7l9n////f/e5/065xBX2cOrjBcBcK07HjgcOFxjIxBM6RozdBxO4HDgcI2NQDCla8zQYNMKpnS1Tmm1tdVnfxjcCOFxULcTjAL4BcBXltgTGuj71qT2GeGw4slrs8odgnT/RFAEBLArfOeCZ9nVNTIZeNUDS2I23vwlhFX+DvIooe8EDFvEqZAT/YxH9v5+YVzVA7uxpg2e8JE/7MUKkgURb0TSqRdnFHA21vS9hGUmwAQ9EKchfAortNtJ9/40Nq6qHR6Jta7IK3/MBBZg2omEHuSR3jMzdg27seYPPOlJP2ASLursZc6xAz/6av0E09WutW2z3N8GByU1+NVgEdvCmf7tfrpie9VO6eFY82ZI3X4QJPY7mf51frr/2qsOWGs2zHH/+vs1CM8UD1dfEOKbSKZ/wvP5Eme2b8orJnDjiYQnbyeERaadFi8d4Uh4jt9mVVUOa2XrDe5IoVOS8dS8cEDqbHt5/YkDaZNB8p8yJlnK1Jy/RW2m2CHomjLTwLKslnC6r88kftqAs43rlogj3WZXxslRbIsbQ+nUh1UJrNXtdTn35POS95IEx6RIP41lMxk+kdrnp7vix1KuMXGvB/UIusukOFNN1a1hxZMR18u9DGKLJNsUxFTnILqQA3sHTfRTvoZH4i2rCir0SLjVpKBSNQRPOgOpu03jpgx49ALx55kOQG1GFwjTisfqaG2PZPq2mYZPCXA23vKoVNhVygXCtOALdcV3Xtha6hzvP20af1mBtTI5P5tz3wGw3rSASnQke5xM6ulSclw2YDfW/Jgn7QRwfSkFlKslORxmaAnTvb+WkqNiYK1OLnSHc+8LSpTScaVaklucTOqtUvNUBJyLNz/hSW9LmFdqx5XoCe5zBlLJcnKUBazVrTe62cJuSQ+X02klMSQPh+ctfoSHOt1y8pQMPBxPPEVPbwqaW06HlcSQ7A/PX7CeB7vOlZvHGPhfV/PdEh4qt7Ny44pfIwW97qy5Zyvb271y8xTjjICHY4lNLK7VaXAV4NE623rB9H3XbzAmBVbj+gUuz3VLWnt+dIZEdgL8gmI9La+BZIPnoQH0GiQrSmkWgFkCZhO4SdQtEBb7FXLxhQJ5gAct2+4IHd+fKSXWT3tJYLcxsc6Dt6t4ro5+BgXfC0etHTx84A+/pGPb9UBybv5sbmkeuoPibYIWEbhudHcn8gSHBAxZ0CnPxnEnOvdrfr7nbKn9mOjHAWtF0+xcge960qbi1Y3AnpBlt/PE/p9NEla75iLg3PLW+7xC/hOQN0v4mFbolYl+V1Q71GT1/Q+cjSeeg+ftENHLOvtVk6/4MxF8FNiNNW0tbjLhEHfyaKr4k7lmH6NjqZboA+BacnMilsDhwOEaG4FgSteYoeNwAodr3eF/ANj0iEwu4kNUAAAAAElFTkSuQmCC'

  exports.UnreadUpdateCounter = Backbone.View.extend({
    initialize: function() {
      this.unreadItemCount = 0

      Tinycon.setOptions({
        'background': '#ff4500'
      })
      Tinycon.setImage(FAVICON)

      this.listenTo(this.model, 'add', this.onUpdateAdded)
      $(document).on('visibilitychange', $.proxy(this.onVisibilityChange, this))

      this.onVisibilityChange()
    },

    onUpdateAdded: function(update, collection, options) {
      if (document.hidden) {
        this.unreadItemCount += 1
        Tinycon.setBubble(this.unreadItemCount)
      }
    },

    onVisibilityChange: function() {
      if (!document.hidden) {
          Tinycon.setBubble()
        this.unreadItemCount = 0
      }
    },
  })
}(r, Backbone, Tinycon, jQuery)
