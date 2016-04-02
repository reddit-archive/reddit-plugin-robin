import random

from pylons import app_globals as g

from r2.lib import amqp
from r2.lib import websockets
from r2.lib.db import tdb_cassandra
from r2.models import Account

from .models import RobinRoom


def make_new_room():
    while True:
        try:
            room = RobinRoom.create(level=0)
        except ValueError:
            continue
        else:
            break
    return room


def run_waitinglist():
    @g.stats.amqp_processor("robin_waitinglist_q")
    def process_waitinglist(msg):
        user_id36 = msg.body
        user = Account._byID36(user_id36, data=True)
        if RobinRoom.get_room_for_user(user):
            print "%s already in room" % user.name
            return

        with g.make_lock("robin_room", "global"):
            current_room_id = g.cache.get("current_robin_room")
            if not current_room_id:
                current_room = make_new_room()
            else:
                try:
                    current_room = RobinRoom._byID(current_room_id)
                except tdb_cassandra.NotFoundException:
                    current_room_id = None
                    current_room = make_new_room()

                if not current_room.is_alive or current_room.is_continued:
                    current_room_id = None
                    current_room = make_new_room()

            current_room.add_participants([user])
            print "added %s to %s" % (user.name, current_room.id)

            if current_room_id:
                g.cache.delete("current_robin_room")
                current_room.persist_computed_name()
                websockets.send_broadcast(
                    namespace="/robin/" + current_room.id,
                    type="updated_name",
                    payload={
                        "room_name": current_room.name,
                    },
                )
            else:
                g.cache.set("current_robin_room", current_room.id)

    amqp.consume_items("robin_waitinglist_q", process_waitinglist)


def add_to_waitinglist(user):
    amqp.add_item("robin_waitinglist_q", user._id36)
