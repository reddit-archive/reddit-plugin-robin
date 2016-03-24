from pylons.i18n import N_

from r2.config.routing import not_in_sr
from r2.lib.configparse import ConfigValue
from r2.lib.js import (
    Module,
    LocalizedModule,
    TemplateFileSource,
)
from r2.lib.plugin import Plugin


class Robin(Plugin):
    needs_static_build = True

    js = {
        "robin": LocalizedModule("robin.js",
            "lib/page-visibility.js",
            "lib/tinycon.js",
            "websocket.js",
            TemplateFileSource("robin/robinmessage.html"),
            TemplateFileSource("robin/robinroomparticipant.html"),
            "errors.js",
            "models/validators.js",
            "robin/models.js",
            "robin/views.js",
            "robin/notifications.js",
            "robin/favicon.js",
            "robin/init.js",
        ),

        "robin-join": Module("robin-join.js",
            "robin/join.js",
        ),
    }

    config = {
        # TODO: your static configuratation options go here, e.g.:
        # ConfigValue.int: [
        #     "robin_blargs",
        # ],
    }

    live_config = {
        # TODO: your live configuratation options go here, e.g.:
        # ConfigValue.int: [
        #     "robin_realtime_blargs",
        # ],
    }

    def declare_queues(self, queues):
        from r2.config.queues import MessageQueue

        queues.declare({
            "robin_presence_q": MessageQueue(),
            "robin_waitinglist_q": MessageQueue(bind_to_self=True),
        })

        queues.robin_presence_q << (
            "websocket.connect",
            "websocket.disconnect",
        )

    def add_routes(self, mc):
        mc("/robin", controller="robin", action="chat",
            conditions={"function": not_in_sr})
        mc("/robin/all", controller="robin", action="all",
            conditions={"function": not_in_sr})
        mc("/robin/admin", controller="robin", action="admin",
            conditions={"function": not_in_sr})
        mc("/robin/join", controller="robin", action="join",
            conditions={"function": not_in_sr})
        mc("/robin/:room_id", controller="robin", action="force_room",
            conditions={"function": not_in_sr})
        mc("/robin/user/:user", controller="robin", action="user_room",
            conditions={"function": not_in_sr})
        mc("/api/robin/:room_id/:action", controller="robin",
            conditions={"function": not_in_sr})
        mc("/api/join_room", controller="robin", action="join_room",
            conditions={"function": not_in_sr})
        mc("/api/room_assignment", controller="robin", action="room_assignment",
            conditions={"function": not_in_sr})
        mc("/api/admin_prompt", controller="robin", action="admin_prompt",
            conditions={"function": not_in_sr})
        mc("/api/admin_reap", controller="robin", action="admin_reap",
            conditions={"function": not_in_sr})
        mc("/api/admin_broadcast", controller="robin", action="admin_broadcast",
            conditions={"function": not_in_sr})

    def load_controllers(self):
        from reddit_robin.controllers import (
            RobinController,
        )
