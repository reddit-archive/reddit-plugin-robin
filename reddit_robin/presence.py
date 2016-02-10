import json
import posixpath

from pylons import app_globals as g

from r2.lib import amqp, websockets
from r2.models import Account


def run():
    @g.stats.amqp_processor("robin_presence_q")
    def process_presence_update(msg):
        message_type = msg.delivery_info["routing_key"]
        payload = json.loads(msg.body)

        namespace = payload["namespace"]
        if not namespace.startswith("/robin/"):
            return

        presence_type = "join" if message_type == "websocket.connect" else "part"

        user_id36 = posixpath.basename(namespace)
        room_namespace = posixpath.dirname(namespace)

        account = Account._byID36(user_id36, data=True)
        websockets.send_broadcast(
            namespace=room_namespace,
            type=presence_type,
            payload={
                "user": account.name,
            },
        )


    amqp.consume_items(
        "robin_presence_q",
        process_presence_update,
        verbose=True,
    )
