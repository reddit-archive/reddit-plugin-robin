from datetime import datetime, timedelta
import math

from pylons import app_globals as g

from r2.lib.db import tdb_cassandra
from r2.models import Account


class RobinRoom(tdb_cassandra.UuidThing):
    _use_db = True
    _connection_pool = 'main'

    _read_consistency_level = tdb_cassandra.CL.QUORUM
    _write_consistency_level = tdb_cassandra.CL.QUORUM

    _int_props = ('level')
    _bool_props = (
        'is_alive',
        'is_abandoned',
        'is_merged',
        'is_continued',
    )
    _date_props = (
        'last_prompt_time',
        'last_reap_time',
    )
    _defaults = dict(
        is_alive=True,
        is_abandoned=False,
        is_merged=False,
        is_continued=False,
    )

    @classmethod
    def create(cls, level):
        room = cls(level=level)
        room._commit()
        return room

    @classmethod
    def make_room_name(cls, pieces):
        room_name = ""
        num_pieces = len(pieces)
        for i, piece in enumerate(pieces):
            len_piece = len(piece)
            chunk_size = max(2, int(math.ceil(len_piece / float(num_pieces))))
            chunk_position = i / float(num_pieces)
            chunk_head = int(chunk_position * len_piece)
            chunk_tail = chunk_head + chunk_size
            if chunk_tail > len_piece:
                chunk_tail = len_piece
                chunk_head = chunk_tail - chunk_size
            chunk = piece[chunk_head:chunk_tail]
            room_name += chunk
        return room_name

    @property
    def id(self):
        """Convert UUID to string"""
        return str(self._id)

    @property
    def name(self):
        if hasattr(self, "_name"):
            return self._name

        user_ids = self.get_all_participants()
        users = Account._byID(user_ids, data=True, return_dict=False)
        user_names = [user.name for user in users]
        self._name = self.make_room_name(user_names)
        return self._name

    def add_participants(self, users):
        ParticipantVoteByRoom.add_participants(self, users)
        RoomsByParticipant.add_users_to_room(users, self)

    def remove_participants(self, users):
        ParticipantVoteByRoom.remove_participants(self, users)
        RoomsByParticipant.remove_users_from_room(users, self)

    def is_participant(self, user):
        vote = ParticipantVoteByRoom.get_vote(self, user)
        return bool(vote)

    def get_all_participants(self):
        return ParticipantVoteByRoom.get_all_participant_ids(self)

    def get_present_participants(self):
        return ParticipantPresenceByRoom.get_present_user_ids(self)

    def get_all_votes(self):
        return ParticipantVoteByRoom.get_all_votes(self)

    def set_vote(self, user, vote):
        ParticipantVoteByRoom.set_vote(self, user, vote)

    def abandon(self):
        self.last_reap_time = datetime.now(g.tz)
        self.is_alive = False
        self.is_abandoned = True
        self._commit()

    def continu(self):
        self.is_continued = True
        self._commit()

    @classmethod
    def merge(cls, room1, room2):
        new_room_level = max([room1.level, room2.level]) + 1
        all_participant_ids = (room1.get_all_participants() |
            room2.get_all_participants())
        all_participants = Account._byID(
            all_participant_ids, data=True, return_dict=False)

        new_room = cls.create(level=new_room_level)
        new_room.add_participants(all_participants)

        for room in (room1, room2):
            room.last_reap_time = datetime.now(g.tz)
            room.is_alive = False
            room.is_merged = True
            room.next_room = new_room.id
            room._commit()

        return new_room

    @classmethod
    def get_room_for_user(cls, user):
        room_id = RoomsByParticipant.get_room_id(user)
        if room_id is None:
            return

        try:
            room = cls._byID(room_id)
        except tdb_cassandra.NotFoundException:
            return

        if room.is_alive and room.is_participant(user):
            return room

    @classmethod
    def generate_all_rooms(cls):
        for _id, columns in cls._cf.get_range():
            room = cls._from_serialized_columns(_id, columns)
            yield room

    @classmethod
    def generate_voting_rooms(cls):
        for room in cls.generate_all_rooms():
            if room.is_alive and not room.is_continued:
                yield room

    def has_prompted(self):
        return True if getattr(self, 'last_prompt_time', False) else False

    def mark_prompted(self):
        self.last_prompt_time = datetime.now(g.tz)
        self._commit()

    def mark_reaped(self):
        self.last_reap_time = datetime.now(g.tz)
        self._commit()


class RobinRoomDead(RobinRoom):
    """An exact copy of RobinRoom for storing dead rooms."""
    _use_db = True
    _type_prefix = "RobinRoomDead"


def move_dead_rooms():
    """Move dead rooms so that only live ones exist in RobinRoom.

    This will ensure that get_range() style queries on the RobinRoom CF stay
    as fast as possible.

    """

    count = 0
    start = datetime.now(g.tz)
    for _id, columns in RobinRoom._cf.get_range():
        room = RobinRoom._from_serialized_columns(_id, columns)
        if not room.is_alive:
            RobinRoomDead._cf.insert(_id, columns)
            RobinRoom._cf.remove(_id)
            count += 1
    print "moved %s rooms in %s" % (count, datetime.now(g.tz) - start)


NOVOTE = "NOVOTE"
INCREASE = "INCREASE"
CONTINUE = "CONTINUE"
ABANDON = "ABANDON"
VALID_VOTES = (INCREASE, CONTINUE, ABANDON)


class ParticipantVoteByRoom(tdb_cassandra.View):
    """Store the list of users and their votes. This is the authoritative list
    of users that belong to a room."""
    _use_db = True
    _connection_pool = 'main'
    _fetch_all_columns = True
    _extra_schema_creation_args = dict(
        key_validation_class=tdb_cassandra.TIME_UUID_TYPE,
    )

    _read_consistency_level = tdb_cassandra.CL.QUORUM
    _write_consistency_level = tdb_cassandra.CL.QUORUM

    @classmethod
    def _rowkey(cls, room):
        return room._id

    @classmethod
    def add_participants(cls, room, users):
        rowkey = cls._rowkey(room)
        vote = NOVOTE
        columns = {user._id36: vote for user in users}
        cls._cf.insert(rowkey, columns)

    @classmethod
    def remove_participants(cls, room, users):
        rowkey = cls._rowkey(room)
        columns = {user._id36: "" for user in users}
        cls._cf.remove(rowkey, columns)

    @classmethod
    def get_all_participant_ids(cls, room):
        rowkey = cls._rowkey(room)
        try:
            columns = cls._cf.get(rowkey)
        except tdb_cassandra.NotFoundException:
            return set()

        return {int(id36, 36) for id36 in columns.keys()}

    @classmethod
    def get_vote(cls, room, user):
        rowkey = cls._rowkey(room)
        try:
            d = cls._cf.get(rowkey, columns=[user._id36])
        except tdb_cassandra.NotFoundException:
            # the user doesn't belong to the room
            return None

        try:
            vote = d[user._id36]
            return vote
        except KeyError:
            # the user doesn't belong to the room
            return None

    @classmethod
    def get_all_votes(cls, room):
        rowkey = cls._rowkey(room)
        try:
            columns = cls._cf.get(rowkey)
        except tdb_cassandra.NotFoundException:
            return {}

        ret = {}
        for user_id36, vote in columns.iteritems():
            ret[int(user_id36, 36)] = vote
        return ret

    @classmethod
    def set_vote(cls, room, user, vote):
        rowkey = cls._rowkey(room)
        columns = {user._id36: vote}
        cls._cf.insert(rowkey, columns)


class ParticipantPresenceByRoom(tdb_cassandra.View):
    _use_db = True
    _connection_pool = 'main'
    _fetch_all_columns = True
    _extra_schema_creation_args = dict(
        key_validation_class=tdb_cassandra.TIME_UUID_TYPE,
    )

    _read_consistency_level = tdb_cassandra.CL.QUORUM
    _write_consistency_level = tdb_cassandra.CL.QUORUM

    _ttl = timedelta(minutes=2)

    @classmethod
    def _rowkey(cls, room):
        return room._id

    @classmethod
    def mark_joined(cls, room, user):
        rowkey = cls._rowkey(room)
        columns = {user._id36: ""}
        cls._cf.insert(rowkey, columns, ttl=cls._ttl)

    @classmethod
    def mark_exited(cls, room, user):
        rowkey = cls._rowkey(room)
        columns = {user._id36: ""}
        cls._cf.remove(rowkey, columns)

    @classmethod
    def get_present_user_ids(cls, room):
        rowkey = cls._rowkey(room)
        try:
            columns = cls._cf.get(rowkey)
        except tdb_cassandra.NotFoundException:
            return set()
        return {int(id36, 36) for id36 in columns.keys()}


class RoomsByParticipant(tdb_cassandra.View):
    _use_db = True
    _connection_pool = 'main'

    _compare_with = tdb_cassandra.TIME_UUID_TYPE
    _read_consistency_level = tdb_cassandra.CL.QUORUM
    _write_consistency_level = tdb_cassandra.CL.QUORUM

    @classmethod
    def _rowkey(cls, user):
        return user._id36

    @classmethod
    def add_users_to_room(cls, users, room):
        column = {room._id: ""}
        with cls._cf.batch() as b:
            for user in users:
                rowkey = cls._rowkey(user)
                b.insert(rowkey, column)

    @classmethod
    def remove_users_from_room(cls, users, room):
        column = {room._id: "EXITED"}
        with cls._cf.batch() as b:
            for user in users:
                rowkey = cls._rowkey(user)
                b.insert(rowkey, column)

    @classmethod
    def get_room_id(cls, user):
        rowkey = cls._rowkey(user)
        try:
            d = cls._cf.get(rowkey, column_count=1, column_reversed=True)
        except tdb_cassandra.NotFoundException:
            return None

        room_id, status = d.items()[0]
        if status != "EXITED":
            return room_id


def populate(start=0, num_users=16384):
    from r2.models.account import Account, register, AccountExists
    from reddit_robin.matchmaker import add_to_waitinglist

    for i in xrange(start, num_users):
        name = "test%s" % i
        try:
            a = register(name, "123456", registration_ip="127.0.0.1")
        except AccountExists:
            a = Account._by_name(name)
        print "added %s" % a
        add_to_waitinglist(a)


def clear_all():
    g.cache.delete("current_robin_room")
    for cls in (RobinRoom, ParticipantVoteByRoom, ParticipantPresenceByRoom,
                RoomsByParticipant):
        cls._cf.truncate()
