import math

from r2.lib.db import tdb_cassandra


class RobinRoom(tdb_cassandra.UuidThing):
    _use_db = True
    _connection_pool = 'main'

    _read_consistency_level = tdb_cassandra.CL.QUORUM
    _write_consistency_level = tdb_cassandra.CL.QUORUM

    _int_props = ('level')
    _bool_props = ('is_alive')

    @classmethod
    def create(cls, level):
        room = cls(is_alive=True, level=level)
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

    def is_participant(self, user):
        vote = ParticipantVoteByRoom.get_vote(self, user)
        return bool(vote)

    def get_all_participants(self):
        return ParticipantVoteByRoom.get_all_participant_ids(self)

    def get_present_participants(self):
        return ParticipantPresenceByRoom.get_present_user_ids(self)

    def get_all_votes(self):
        return ParticipantVoteByRoom.get_all_votes(self)

    def change_vote(self, user, vote_type, confirmed):
        original_vote = ParticipantVoteByRoom.get_vote(self, user)
        if original_vote.confirmed:
            raise ValueError("can't change confirmed vote")

        vote = RoomVote(vote_type, confirmed)
        ParticipantVoteByRoom.set_vote(self, user, vote)

    def destroy(self, reason):
        self.is_alive = False
        self.reason = reason
        self._commit()

    @classmethod
    def merge(cls, room1, room2):
        new_room_level = max([room1.level, room2.level]) + 1
        all_participant_ids = (room1.get_all_participants() +
            room2.get_all_participants())
        all_participants = Account._byID(
            all_participant_ids, data=True, return_dict=False)

        new_room = cls.create(level=new_room_level)
        new_room.add_participants(all_participants)
        room1.destroy(reason="INCREASE")
        room2.destroy(reason="INCREASE")
        return new_room

    @classmethod
    def get_room_for_user(cls, user):
        room_id = RoomsByParticipant.get_room_id(user)
        if room_id is None:
            return

        room = cls._byID(room_id)
        if room.is_alive and room.is_participant(user):
            return room

    @classmethod
    def generate_all_rooms(cls):
        for rowkey, columns in cls._cf.get_range():
            room = cls._byID(rowkey)
            if room.is_alive:
                yield room


class RoomVote(object):
    VALID_VOTES = {
        ("NOVOTE", False),
        ("INCREASE", False),
        ("INCREASE", True),
        ("CONTINUE", False),
        ("CONTINUE", True),
        ("ABANDON", False),
        ("ABANDON", True),
    }

    def __init__(self, name, confirmed):
        assert (name, confirmed) in self.VALID_VOTES

        self.name = name
        self.confirmed = confirmed

    def to_string(self):
        return "{name}{other}".format(
            name=self.name,
            other="_LOCKED" if self.confirmed else "",
        )

    @classmethod
    def from_string(cls, s):
        name, sep, locked = s.partition("_")
        confirmed = locked == "LOCKED"
        vote = cls(name, confirmed)
        return vote

    def __repr__(self):
        cls_name = self.__class__.__name__
        return "<{cls} {name} ({confirmed})>".format(
            cls=cls_name,
            name=self.name,
            confirmed="confirmed" if self.confirmed else "unconfirmed",
        )


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
        vote = RoomVote("NOVOTE", confirmed=False)
        column_value = vote.to_string()
        columns = {user._id36: column_value for user in users}
        cls._cf.insert(rowkey, columns)

    @classmethod
    def get_all_participant_ids(cls, room):
        rowkey = cls._rowkey(room)
        try:
            obj = cls._byID(rowkey)
        except tdb_cassandra.NotFoundException:
            return set()

        return {int(id36, 36) for id36 in obj._t.keys()}

    @classmethod
    def get_vote(cls, room, user):
        rowkey = cls._rowkey(room)
        try:
            d = cls._cf.get(rowkey, columns=[user._id36])
        except tdb_cassandra.NotFoundException:
            return None

        try:
            column_value = d[user._id36]
        except KeyError:
            return None

        return RoomVote.from_string(column_value)

    @classmethod
    def get_all_votes(cls, room):
        rowkey = cls._rowkey(room)
        try:
            obj = cls._byID(rowkey)
        except tdb_cassandra.NotFoundException:
            return {}

        ret = {}
        for user_id36, vote_str in obj._t.iteritems():
            ret[int(user_id36, 36)] = RoomVote.from_string(vote_str)
        return ret

    @classmethod
    def set_vote(cls, room, user, vote):
        rowkey = cls._rowkey(room)
        column_value = vote.to_string()
        columns = {user._id36: column_value}
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

    #_ttl = timedelta(minutes=2) # do we want to expire idle users?

    @classmethod
    def _rowkey(cls, room):
        return room._id

    @classmethod
    def mark_joined(cls, room, user):
        rowkey = cls._rowkey(room)
        columns = {user._id36: ""}
        cls._cf.insert(rowkey, columns)

    @classmethod
    def mark_exited(cls, room, user):
        rowkey = cls._rowkey(room)
        columns = {user._id36: ""}
        cls._cf.remove(rowkey, columns)

    @classmethod
    def get_present_user_ids(cls, room):
        rowkey = cls._rowkey(room)
        try:
            obj = cls._byID(rowkey)
        except tdb_cassandra.NotFoundException:
            return set()
        return {int(id36, 36) for id36 in obj._t.keys()}


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
    def get_room_id(cls, user):
        rowkey = cls._rowkey(user)
        try:
            d = cls._cf.get(rowkey, column_count=1, column_reversed=True)
        except tdb_cassandra.NotFoundException:
            return None
        room_id = d.keys()[0]
        return room_id


def populate():
    from r2.models.account import Account, register, AccountExists
    users = []
    for name in ("test1", "test2", "test3"):
        try:
            a = register(name, "123456", registration_ip="127.0.0.1")
        except AccountExists:
            a = Account._by_name(name)
        users.append(a)

    for _id in ("example_a", "example_b", "example_c"):
        room = RobinRoom.create(_id=_id, level=0)
        if _id == "example_a":
            room.add_participants(users)

def clear_all():
    from pylons import app_globals as g
    g.cache.delete("current_robin_room")
    for cls in (RobinRoom, ParticipantVoteByRoom, ParticipantPresenceByRoom,
                RoomsByParticipant):
        cls._cf.truncate()
