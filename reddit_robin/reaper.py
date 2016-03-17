from collections import defaultdict
from datetime import datetime, timedelta

from pylons import app_globals as g

from r2.lib import websockets
from r2.models import Account
from .models import (
    NOVOTE,
    INCREASE,
    CONTINUE,
    ABANDON,
    move_dead_rooms,
    RobinRoom,
)


# We do this on a 2 minute interval, since reaping and vote alerting is done
# every minute.  This should guarantee a warning at least 1 minute before
# each room is reaped.  This could still be a problem if the overall loop time
# is bigger than a minute.
VOTING_PROMPT_TIME = timedelta(minutes=2)

# How long each room will last at each level before merging happens.
DEFAULT_LEVEL_TIME = timedelta(minutes=15)
LEVEL_TIMINGS = defaultdict(lambda: DEFAULT_LEVEL_TIME)
LEVEL_TIMINGS.update({
    0: timedelta(minutes=5),
})


"""
reaping happens every 15 minutes
5 minutes before the reaping we will prompt each room to vote

doing it on a fixed schedule like this will put all rooms in sync rather than
having them age in reference from their creation date. this simplifies the merging.

"""


def prompt_for_voting():
    now = datetime.now(g.tz)
    print "%s: prompting voting in rooms with less than %s remaining" % (
        now, VOTING_PROMPT_TIME)

    count = 0
    for room in RobinRoom.generate_voting_rooms():

        # Skip if we've already prompted
        if room.has_prompted():
            continue

        # Skip this room if too much time still remains
        alert_after = room.date + (LEVEL_TIMINGS[room.level] -
                                   VOTING_PROMPT_TIME)
        if now < alert_after:
            continue

        count += 1
        websockets.send_broadcast(
            namespace="/robin/" + room.id,
            type="please_vote",
            payload={},
        )
        room.mark_prompted()
        print "prompted %s" % room
    print "%s: done prompting (%s rooms took %s)" % (
        datetime.now(g.tz), count, datetime.now(g.tz) - now)


def reap_ripe_rooms():
    """Apply voting decision to each room.

    Users can vote to:
    1) increase (merge with another room)
    2) continue (stop votingand leave the room its current size forever)
    3) abandon (terminate the room). no vote counts as a vote to abandon

    A simple majority decides which action to take.
    Any users that vote to abandon are removed from the room permanently.
    In case of ties precedence is abandon > continue > increase

    """
    now = datetime.now(g.tz)

    to_merge_by_level = {}
    count = 0
    for room in RobinRoom.generate_voting_rooms():

        # The room isn't old enough to be merged yet
        age = now - room.date
        if age < LEVEL_TIMINGS[room.level]:
            continue

        print "%s: attempting to merge room %s with age %s" % (
            datetime.now(g.tz), room, age)

        count += 1

        # Calculate votes
        votes_by_user = room.get_all_votes()
        votes = votes_by_user.values()
        abandoning_user_ids = {
            _id for _id, vote in votes_by_user.iteritems()
            if vote == ABANDON or vote == NOVOTE
        }
        num_increase = sum(1 for vote in votes if vote == INCREASE)
        num_continue = sum(1 for vote in votes if vote == CONTINUE)
        num_abandon = len(abandoning_user_ids)

        if num_abandon >= num_continue and num_abandon >= num_increase:
            abandon_room(room)
        else:
            # no matter the vote outcome, abandoning users are removed
            if abandoning_user_ids:
                abandoning_users = Account._byID(
                    abandoning_user_ids, data=True, return_dict=False)
                remove_abandoners(room, abandoning_users)

            if num_continue >= num_increase:
                continue_room(room)
            else:
                if room.level in to_merge_by_level:
                    other_room = to_merge_by_level.pop(room.level)
                    merge_rooms(room, other_room)
                else:
                    to_merge_by_level[room.level] = room

    for level, orphaned_room in to_merge_by_level.iteritems():
        alert_no_match(orphaned_room)
    print "%s: done reaping (%s rooms took %s)" % (datetime.now(g.tz), count, datetime.now(g.tz) - now)

    move_dead_rooms()


def remove_abandoners(room, users):
    print "removing %s from %s" % (users, room)
    room.remove_participants(users)

    websockets.send_broadcast(
        namespace="/robin/" + room.id,
        type="users_abandoned",
        payload={
            "users": [user._id36 for user in users],
        },
    )


def continue_room(room):
    print "continuing %s" % room
    room.continu()

    websockets.send_broadcast(
        namespace="/robin/" + room.id,
        type="continue",
        payload={},
    )


def abandon_room(room):
    print "abandoning %s" % room
    room.abandon()

    websockets.send_broadcast(
        namespace="/robin/" + room.id,
        type="abandon",
        payload={},
    )


def merge_rooms(room1, room2):
    print "merging %s + %s" % (room1, room2)
    new_room = RobinRoom.merge(room1, room2)

    for room in (room1, room2):
        websockets.send_broadcast(
            namespace="/robin/" + room.id,
            type="merge",
            payload={
                "destination": new_room.id,
            },
        )


def alert_no_match(room):
    print "no match for %s" % room

    websockets.send_broadcast(
        namespace="/robin/" + room.id,
        type="no_match",
        payload={},
    )
