from datetime import datetime, timedelta

from pylons import app_globals as g

from r2.lib import websockets
from .models import RobinRoom, move_dead_rooms


"""
reaping happens every 15 minutes
5 minutes before the reaping we will prompt each room to vote

doing it on a fixed schedule like this will put all rooms in sync rather than
having them age in reference from their creation date. this simplifies the merging.

Update your cron (for local installs):
/etc/cron.d/reddit
*/15 * * * * root /sbin/start --quiet reddit-job-robin_reap_ripe_rooms
10-59/15 * * * * root /sbin/start --quiet reddit-job-robin_prompt_for_voting


"""


def prompt_for_voting(room_age_minutes=6):
    now = datetime.now(g.tz)
    alert_older_than = now - timedelta(minutes=room_age_minutes)
    print "%s: prompting rooms older than %s" % (now, alert_older_than)

    count = 0
    for room in RobinRoom.generate_rooms_for_prompting(cutoff=alert_older_than):
        count += 1
        websockets.send_broadcast(
            namespace="/robin/" + room.id,
            type="please_vote",
            payload={},
        )
        room.mark_prompted()
        print "prompted %s" % room
    print "%s: done prompting (%s rooms took %s)" % (datetime.now(g.tz), count, datetime.now(g.tz) - now)


def reap_ripe_rooms(room_age_minutes=10):
    # reap rooms older than 10 minutes, and the reaper job runs every 15 minutes
    # this offset accounts for the time it takes to run reaping
    now = datetime.now(g.tz)
    reap_older_than = now - timedelta(minutes=room_age_minutes)
    print "%s: reaping rooms older than %s" % (now, reap_older_than)

    to_merge_by_level = {}
    count = 0
    for room in RobinRoom.generate_rooms_for_reaping(cutoff=reap_older_than):
        count += 1
        votes_by_user = room.get_all_votes()
        votes = votes_by_user.values()

        num_total_votes = len(votes)
        num_increase = sum(1 for vote in votes if vote == "INCREASE")
        num_continue = sum(1 for vote in votes if vote == "CONTINUE")
        # abandon votes are novotes plus explicit abandon
        num_abandon = num_total_votes - num_increase - num_continue

        if num_increase >= num_continue and num_increase >= num_abandon:
            if room.level in to_merge_by_level:
                other_room = to_merge_by_level.pop(room.level)
                merge_rooms(room, other_room)
            else:
                to_merge_by_level[room.level] = room
        elif num_continue >= num_abandon:
            continue_room(room)
        else:
            abandon_room(room)

    for level, orphaned_room in to_merge_by_level.iteritems():
        alert_no_match(orphaned_room)
    print "%s: done reaping (%s rooms took %s)" % (datetime.now(g.tz), count, datetime.now(g.tz) - now)

    move_dead_rooms()


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
    room.continu()

    websockets.send_broadcast(
        namespace="/robin/" + room.id,
        type="no_match",
        payload={},
    )
