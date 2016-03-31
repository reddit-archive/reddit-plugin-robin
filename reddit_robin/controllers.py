import datetime
import posixpath

import pytz
from pylons import request
from pylons import app_globals as g
from pylons import tmpl_context as c
from pylons.controllers.util import abort

from r2.config import feature
from r2.controllers import add_controller
from r2.controllers.reddit_base import RedditController
from r2.lib import websockets, ratelimit, utils
from r2.lib.errors import errors
from r2.lib.template_helpers import js_timestamp
from r2.lib.validator import (
    json_validate,
    validate,
    validatedForm,
    VAccountByName,
    VAdmin,
    VBoolean,
    VLength,
    VModhash,
    VNotInTimeout,
    VOneOf,
    VUser,
)
from r2.models import Account

from . import events
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
from .reaper import prompt_for_voting, reap_ripe_rooms, get_reap_time


@add_controller
class RobinController(RedditController):
    def pre(self):
        RedditController.pre(self)
        if not feature.is_enabled("robin"):
            self.abort404()

    @validate(
        VUser(),
        VNotInTimeout(),
    )
    def GET_join(self):
        room = RobinRoom.get_room_for_user(c.user)
        if room:
            return self.redirect("/robin")

        return RobinPage(
            title="robin",
            content=RobinJoin(robin_heavy_load=g.live_config.get(
                'robin_heavy_load')),
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
        VNotInTimeout(),
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
                "robin_room_is_continued": room.is_continued,
                "robin_room_name": room.name,
                "robin_room_id": room.id,
                "robin_websocket_url": websocket_url,
                "robin_user_list": user_list,
                "robin_room_date": js_timestamp(room.date),
                "robin_room_reap_time": js_timestamp(get_reap_time(room)),
            },
        ).render()

    def _has_exceeded_ratelimit(self, form, room):
        # grab the ratelimit (as average events per second) for the room's
        # current level, using the highest level configured that's not bigger
        # than the room.  e.g. if ratelimits are defined for levels 1, 2, and 4
        # and the room is level 3, this will give us the ratelimit specified
        # for 2.
        desired_avg_per_sec = 1
        by_level = g.live_config.get("robin_ratelimit_avg_per_sec", {})
        for level, avg_per_sec in sorted(by_level.items(), key=lambda (x,y): x):
            if level > room.level:
                break
            desired_avg_per_sec = avg_per_sec

        # now figure out how many events per window that means
        window_size = g.live_config.get("robin_ratelimit_window", 10)
        allowed_events_per_window = int(desired_avg_per_sec * window_size)

        try:
            # now figure out how much they've actually used
            ratelimit_key = "robin/{}".format(c.user._id36)
            time_slice = ratelimit.get_timeslice(window_size)
            usage = ratelimit.get_usage(ratelimit_key, time_slice)

            # ratelimit them if too much
            if usage >= allowed_events_per_window:
                g.stats.simple_event("robin.ratelimit.exceeded")

                period_end = datetime.datetime.utcfromtimestamp(time_slice.end)
                period_end_utc = period_end.replace(tzinfo=pytz.UTC)
                until_reset = utils.timeuntil(period_end_utc)
                c.errors.add(errors.RATELIMIT, {"time": until_reset},
                             field="ratelimit", code=429)
                form.has_errors("ratelimit", errors.RATELIMIT)

                return True

            # or record the usage and move on
            ratelimit.record_usage(ratelimit_key, time_slice)
        except ratelimit.RatelimitError as exc:
            g.log.warning("ratelimit error: %s", exc)
        return False

    @validatedForm(
        VUser(),
        VNotInTimeout(),
        VModhash(),
        room=VRobinRoom("room_id"),
        message=VLength("message", max_length=140),  # TODO: do we want md?
    )
    def POST_message(self, form, jquery, room, message):
        if self._has_exceeded_ratelimit(form, room):
            return

        if form.has_errors("message", errors.NO_TEXT, errors.TOO_LONG):
            return

        websockets.send_broadcast(
            namespace="/robin/" + room.id,
            type="chat",
            payload={
                "from": c.user.name,
                "body": message,
            },
        )

        events.message(
            room=room,
            message=message,
            sent_dt=datetime.datetime.utcnow(),
            context=c,
            request=request,
        )


    @validatedForm(
        VUser(),
        VNotInTimeout(),
        VModhash(),
        room=VRobinRoom("room_id"),
        vote=VOneOf("vote", VALID_VOTES),
    )
    def POST_vote(self, form, jquery, room, vote):
        if self._has_exceeded_ratelimit(form, room):
            return

        if not vote:
            # TODO: error return?
            return

        g.stats.simple_event('robin.vote.%s' % vote)

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
        VNotInTimeout(),
        VModhash(),
    )
    def POST_join_room(self, form, jquery):
        if g.live_config.get('robin_heavy_load'):
            request.environ["usable_error_content"] = (
                "Robin is currently experience high load.")
            abort(503)

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
        websockets.send_broadcast(
            namespace="/robin/" + room.id,
            type="users_abandoned",
            payload={
                "users": [c.user.name],
            },
        )

    @json_validate(
        VUser(),
        VNotInTimeout(),
    )
    def GET_room_assignment(self, responder):
        room = RobinRoom.get_room_for_user(c.user)
        if room:
            return {"roomId": room.id}

    @validatedForm(
        VAdmin(),
        VModhash(),
    )
    def POST_admin_prompt(self, form, jquery):
        prompt_for_voting()

    @validatedForm(
        VAdmin(),
        VModhash(),
    )
    def POST_admin_reap(self, form, jquery):
        reap_ripe_rooms()

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
