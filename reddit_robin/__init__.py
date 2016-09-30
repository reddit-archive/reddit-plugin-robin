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

    live_config = {
        ConfigValue.int: [
            "robin_ratelimit_window",
        ],

        ConfigValue.dict(ConfigValue.int, ConfigValue.float): [
            "robin_ratelimit_avg_per_sec",
        ],
    }

    def declare_queues(self, queues):
        from r2.config.queues import MessageQueue

        queues.declare({
            "robin_presence_q": MessageQueue(),
        })

        # TODO: appears to not be getting messages
        queues.robin_presence_q << (
            "websocket.connect",
            "websocket.disconnect",
        )

    def add_routes(self, mc):
        mc("/robin/:room_id", controller="robin", action="chat",
            conditions={"function": not_in_sr})
        mc("/robin/:room_id/create", controller="robin", action="create",
            conditions={"function": not_in_sr})
        mc("/api/robin/:room_id/:action", controller="robin",
            conditions={"function": not_in_sr})

    def load_controllers(self):
        from r2.lib.pages import Reddit
        from reddit_robin.controllers import (
            RobinController,
        )

        Reddit.extra_stylesheets.append('robin_global.less')

        from reddit_robin.hooks import hooks
        hooks.register_all()
