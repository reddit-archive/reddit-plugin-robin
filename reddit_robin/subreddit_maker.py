from pylons import app_globals as g

from r2.lib import amqp, websockets
from r2.models import Account
from r2.models.admintools import send_system_message

from .models import RobinRoom


def send_sr_message(subreddit, recipient):
    subject = 'Continue the conversation in /r/%s' % subreddit.name
    body = 'Continue the conversation in /r/{sr_name}.'.format(
        sr_name=subreddit.name,
    )

    print 'sending system message to %s for %s' % (recipient, subreddit)
    send_system_message(recipient, subject, body, add_to_sent=False)


def run_subreddit_maker():
    @g.stats.amqp_processor('robin_subreddit_maker_q')
    def process_subreddit_maker(msg):
        room_id = msg.body
        room = RobinRoom._byID(room_id)
        print 'creating sr for room %s' % room

        subreddit = room.create_sr()
        print 'got %s from room.create_sr()' % subreddit

        participant_ids = room.get_all_participants()
        participants = [
            Account._byID(participant_id)
            for participant_id in participant_ids
        ]
        moderators = participants[:5]

        if subreddit:
            print 'adding moderators to %s' % subreddit
            for moderator in moderators:
                subreddit.add_moderator(moderator)

            print 'adding contributors to %s' % subreddit
            for participant in participants:
                # To be replaced with UserRel hacking?
                subreddit.add_contributor(participant)
                send_sr_message(subreddit, participant)

            payload = {
                "body": subreddit.name,
            }

            websockets.send_broadcast(
                namespace="/robin/" + room.id,
                type="continue",
                payload=payload,
            )
        else:
            print 'subreddit creation failed for room %s' % room.id

    amqp.consume_items('robin_subreddit_maker_q', process_subreddit_maker)


def queue_subreddit_creation(room):
    amqp.add_item('robin_subreddit_maker_q', room.id)
