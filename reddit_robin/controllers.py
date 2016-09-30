import datetime
import posixpath

import pytz
from pylons import request
from pylons import app_globals as g
from pylons import tmpl_context as c
from pylons.controllers.util import abort

from r2.controllers import add_controller
from r2.controllers.reddit_base import RedditController
from r2.lib import websockets, ratelimit, utils
from r2.lib.errors import errors
from r2.lib.validator import (
    nop,
    validate,
    validatedForm,
    VAdmin,
    VLength,
    VModhash,
    VNotInTimeout,
    VUser,
)
from r2.models import Account

from . import events
from .validators import VRobinRoom
from .pages import (
    RobinChat,
    RobinCreate,
    RobinChatPage,
    RobinPage,
)
from .models import RobinRoom, InvalidNameError, RoomExistsError


@add_controller
class RobinController(RedditController):
    @validate(
        VUser(),
        VNotInTimeout(),
        room=VRobinRoom("room_id"),
    )
    def GET_chat(self, room):
        if not room.is_active and not c.user_is_admin:
            abort(404)

        return self._get_chat_page(room)

    @validate(
        VUser(),
        VAdmin(),
        room_id=nop("room_id"),
    )
    def GET_create(self, room_id):
        room = RobinRoom.get(room_id)
        if room:
            self.redirect("/robin/%s" % room_id)

        return RobinPage(
            title="create room",
            content=RobinCreate(room_id),
        ).render()

    @validatedForm(
        VAdmin(),
        VModhash(),
        room_id=nop("room_id"),
    )
    def POST_create(self, form, jquery, room_id):
        try:
            room = RobinRoom.create(room_id)
        except InvalidNameError:
            abort(400, "bad name")
        except RoomExistsError:
            room = RobinRoom.get(room_id)

        self.redirect("/robin/%s" % room_id)    # TODO: not working

    def _get_chat_page(self, room):
        path = posixpath.join("/robin", room._id, c.user._id36)
        websocket_url = websockets.make_url(path, max_age=3600)

        present_user_ids = room.get_present_users()

        users = Account._byID(present_user_ids, stale=True)
        user_list = []

        for user in users.itervalues():
            user_list.append({
                "name": user.name,
                "present": True,
            });

        return RobinChatPage(
            title="chat in %s" % room._id,
            content=RobinChat(room=room),
            extra_js_config={
                "robin_room_id": room._id,
                "robin_websocket_url": websocket_url,
                "robin_user_list": user_list,
            },
        ).render()

    def _has_exceeded_ratelimit(self, form, room):
        # TODO: scale ratelimit by number of users in room
        desired_avg_per_sec = 1

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
        if not room.is_active and not c.user_is_admin:
            return

        if self._has_exceeded_ratelimit(form, room):
            return

        if form.has_errors("message", errors.NO_TEXT, errors.TOO_LONG):
            return

        websockets.send_broadcast(
            namespace="/robin/" + room._id,
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
