import random

from pylons import app_globals as g

from r2.lib import amqp
from r2.models import Account

from .models import RobinRoom


def make_room_name_list():
    try:
        with open("/usr/share/dict/words", "r") as f:
            # `apt-get install wamerican` if you don't have this file
            words = f.readlines()
    except IOError:
        # poor man's word list
        import random
        letters = "abcdefghijklmnopqrstuvwxyz"
        words = [
            "".join(random.sample(letters, 8)) for i in xrange(1000)
        ]

    words = map(lambda word: word.strip().lower(), words)
    words = filter(lambda word: len(word) > 6, words)
    words = filter(lambda word: all(c.isalpha() for c in word), words)
    return words


ROOM_NAMES = make_room_name_list()


def make_new_room():
    while True:
        name = random.choice(ROOM_NAMES)
        try:
            room = RobinRoom.create(name, level=0)
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
            current_room_name = g.cache.get("current_robin_room")
            if not current_room_name:
                current_room = make_new_room()
            else:
                current_room = RobinRoom._byID(current_room_name)

            current_room.add_participants([user])
            print "added %s to %s" % (user.name, current_room._id)

            if current_room_name:
                g.cache.delete("current_robin_room")
            else:
                g.cache.set("current_robin_room", current_room._id)

    amqp.consume_items("robin_waitinglist_q", process_waitinglist)


def add_to_waitinglist(user):
    amqp.add_item("robin_waitinglist_q", user._id36)
