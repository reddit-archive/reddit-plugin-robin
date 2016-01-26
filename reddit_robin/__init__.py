from pylons.i18n import N_

from r2.config.routing import not_in_sr
from r2.lib.configparse import ConfigValue
from r2.lib.js import LocalizedModule
from r2.lib.plugin import Plugin


class Robin(Plugin):
    needs_static_build = True

    js = {
        "robin": LocalizedModule("robin.js",
            "websocket.js",
            "robin/init.js",
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
        })

        queues.robin_presence_q << (
            "websocket.connect",
            "websocket.disconnect",
        )

    def add_routes(self, mc):
        mc("/robin", controller="robin", action="home",
           conditions={"function": not_in_sr})
        mc("/robin/:room_id", controller="robin", action="chat",
           conditions={"function": not_in_sr})
        mc("/api/robin/:room_id/:action", controller="robin",
           conditions={"function": not_in_sr})

    def load_controllers(self):
        from reddit_robin.controllers import (
            RobinController,
        )
