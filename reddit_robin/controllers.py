import posixpath

from pylons import app_globals as g
from pylons import tmpl_context as c

from r2.controllers import add_controller
from r2.controllers.reddit_base import RedditController
from r2.lib import websockets
from r2.lib.errors import errors
from r2.lib.validator import (
    json_validate,
    validate,
    validatedForm,
    VAccountByName,
    VAdmin,
    VBoolean,
    VLength,
    VModhash,
    VOneOf,
    VUser,
)
from r2.models import Account

from .validators import VRobinRoom
from .pages import (
    RobinAdmin,
    RobinAll,
    RobinPage,
    RobinChatPage,
    RobinJoin,
    RobinChat,
)
from .models import RobinRoom, VALID_VOTES
from .matchmaker import add_to_waitinglist
from .reaper import prompt_for_voting, reap_ripe_rooms


@add_controller
class RobinController(RedditController):
    @validate(
        VUser(),
    )
    def GET_join(self):
        room = RobinRoom.get_room_for_user(c.user)
        if room:
            return self.redirect("/robin")

        return RobinPage(
            title="robin",
            content=RobinJoin(),
        ).render()

    @validate(
        VAdmin(),
    )
    def GET_all(self):
        return RobinPage(
            title="robin",
            content=RobinAll(),
        ).render()

    @validate(
        VAdmin(),
    )
    def GET_admin(self):
        return RobinPage(
            title="robin",
            content=RobinAdmin(),
        ).render()

    @validate(
        VUser(),
    )
    def GET_chat(self):
        room = RobinRoom.get_room_for_user(c.user)
        if not room:
            return self.redirect("/robin/join")

        return self._get_chat_page(room)

    @validate(
        VAdmin(),
        room=VRobinRoom("room_id", allow_admin=True),
    )
    def GET_force_room(self, room):
        """Allow admins to view a specific room"""
        return self._get_chat_page(room)

    @validate(
        VAdmin(),
        user=VAccountByName("user"),
    )
    def GET_user_room(self, user):
        """Redirect admins to a user's room"""
        room = RobinRoom.get_room_for_user(user)
        if not room:
            self.abort404()

        self.redirect("/robin/" + room.id)

    def _get_chat_page(self, room):
        path = posixpath.join("/robin", room.id, c.user._id36)
        websocket_url = websockets.make_url(path, max_age=3600)

        all_user_ids = room.get_all_participants()
        all_present_ids = room.get_present_participants()
        all_votes = room.get_all_votes()

        users = Account._byID(all_user_ids, data=True)
        user_list = []

        for user in users.itervalues():
            if user._id in all_votes:
                vote = all_votes.get(user._id)
            else:
                vote = None

            user_list.append({
                "name": user.name,
                "present": user._id in all_present_ids,
                "vote": vote,
            });

        return RobinChatPage(
            title="chat in %s" % room.name,
            content=RobinChat(room=room),
            extra_js_config={
                "robin_room_name": room.name,
                "robin_room_id": room.id,
                "robin_websocket_url": websocket_url,
                "robin_user_list": user_list,
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
            namespace="/robin/" + room.id,
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
        vote=VOneOf("vote", VALID_VOTES),
    )
    def POST_vote(self, form, jquery, room, vote):
        if not vote:
            # TODO: error return?
            return

        room.set_vote(c.user, vote)
        websockets.send_broadcast(
            namespace="/robin/" + room.id,
            type="vote",
            payload={
                "from": c.user.name,
                "vote": vote,
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

    @validatedForm(
        VUser(),
        VModhash(),
    )
    def POST_leave_room(self, form, jquery):
        room = RobinRoom.get_room_for_user(c.user)
        if not room:
            return
        room.remove_participants([c.user])

    @json_validate(VUser())
    def GET_room_assignment(self, responder):
        room = RobinRoom.get_room_for_user(c.user)
        if room:
            return {"roomId": room.id}

    @validatedForm(
        VAdmin(),
        VModhash(),
    )
    def POST_admin_prompt(self, form, jquery):
        prompt_for_voting(room_age_minutes=0)

    @validatedForm(
        VAdmin(),
        VModhash(),
    )
    def POST_admin_reap(self, form, jquery):
        reap_ripe_rooms(room_age_minutes=0)

    @validatedForm(
        VAdmin(),
        VModhash(),
        message=VLength("message", max_length=140),
    )
    def POST_admin_broadcast(self, form, jquery, message):
        if form.has_errors("message", errors.NO_TEXT, errors.TOO_LONG):
            return

        websockets.send_broadcast(
            namespace="/robin",
            type="system_broadcast",
            payload={
                "body": message,
            },
        )
