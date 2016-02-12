import posixpath

from pylons import tmpl_context as c

from r2.controllers import add_controller
from r2.controllers.reddit_base import RedditController
from r2.lib import websockets
from r2.lib.errors import errors
from r2.lib.validator import (
    validate,
    validatedForm,
    VLength,
    VModhash,
    VUser,
)

from .validators import VRobinRoom
from .pages import (
    RobinPage,
    RobinChatPage,
    RobinHome,
    RobinChat,
)
from .models import RobinRoom


@add_controller
class RobinController(RedditController):
    def GET_home(self):
        if c.user_is_loggedin:
            room = RobinRoom.get_room_for_user(c.user)
            if room:
                self.redirect("/robin/{room_id}".format(room_id=room._id))

        return RobinPage(
            title="robin",
            content=RobinHome(),
        ).render()

    @validate(
        VUser(),
        room=VRobinRoom("room_id"),
    )
    def GET_chat(self, room):
        path = posixpath.join("/robin", str(room._id), c.user._id36)
        websocket_url = websockets.make_url(path, max_age=3600)

        return RobinChatPage(
            title="chat in %s" % room._id,
            content=RobinChat(room=room),
            extra_js_config={
                "robin_room_id": room._id,
                "robin_websocket_url": websocket_url,
            },
        ).render()

    @validatedForm(
        VUser(),
        VModhash(),
        room=VRobinRoom("room_id"),
        message=VLength("message", max_length=140),  # TODO: do we want md?
        # TODO: do we want a throttle/ratelimit?
    )
    def POST_message(self, form, jquery, room, message):
        if form.has_errors("message", errors.NO_TEXT, errors.TOO_LONG):
            return

        # if we decide we want logging, perhaps we can make a logger that
        # watches the amqp bus instead of complicating this request logic?
        websockets.send_broadcast(
            namespace="/robin/" + room._id,
            type="chat",
            payload={
                "from": c.user.name,
                "body": message,
            },
        )
