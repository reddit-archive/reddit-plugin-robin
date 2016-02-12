import posixpath

from pylons import tmpl_context as c

from r2.controllers import add_controller
from r2.controllers.reddit_base import RedditController
from r2.lib import websockets
from r2.lib.errors import errors
from r2.lib.validator import (
    json_validate,
    validate,
    validatedForm,
    VBoolean,
    VLength,
    VModhash,
    VOneOf,
    VUser,
)

from .validators import VRobinRoom
from .pages import (
    RobinAll,
    RobinPage,
    RobinChatPage,
    RobinHome,
    RobinChat,
)
from .models import RobinRoom
from .matchmaker import add_to_waitinglist


@add_controller
class RobinController(RedditController):
    @validate(
        VUser(),
    )
    def GET_home(self):
        room = RobinRoom.get_room_for_user(c.user)
        if room:
            self.redirect("/robin/{room_id}".format(room_id=room._id))
            return

        return RobinPage(
            title="robin",
            content=RobinHome(),
        ).render()

    @validate(
        VUser(),
    )
    def GET_all(self):
        #if not c.user_is_admin:
        #    return self.abort403()

        return RobinPage(
            title="robin",
            content=RobinAll(),
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

    @validatedForm(
        VUser(),
        VModhash(),
        room=VRobinRoom("room_id"),
        vote=VOneOf("vote", ("INCREASE", "CONTINUE", "ABANDON")),
        confirmed=VBoolean("confirmed"),
    )
    def POST_vote(self, form, jquery, room, vote, confirmed):
        if not vote:
            # TODO: error return?
            return

        try:
            room.change_vote(c.user, vote, confirmed)
        except ValueError:
            # TODO: error return?
            return

        websockets.send_broadcast(
            namespace="/robin/" + room._id,
            type="vote",
            payload={
                "from": c.user.name,
                "vote": vote,
                "confirmed": confirmed,
            },
        )

    @validatedForm(
        VUser(),
        VModhash(),
    )
    def POST_join_room(self, form, jquery):
        room = RobinRoom.get_room_for_user(c.user)
        if room:
            # user is already in a room, they should get redirected by the
            # frontend after polling /api/room_assignment.json
            return

        add_to_waitinglist(c.user)

    @json_validate(VUser())
    def GET_room_assignment(self, responder):
        room = RobinRoom.get_room_for_user(c.user)
        if room:
            return {"roomId": room._id}
