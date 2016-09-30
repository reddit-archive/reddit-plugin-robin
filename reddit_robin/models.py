import re

from pylons import app_globals as g

from r2.lib.db import tdb_cassandra


class RoomExistsError(Exception):
    pass


class InvalidNameError(Exception):
    pass


class RobinRoom(tdb_cassandra.Thing):
    _use_db = True
    _connection_pool = 'main'
    _extra_schema_creation_args = {
        "key_validation_class": tdb_cassandra.UTF8_TYPE,
    }
    _read_consistency_level = tdb_cassandra.CL.QUORUM
    _write_consistency_level = tdb_cassandra.CL.QUORUM

    _bool_props = (
        'is_active',
    )
    _defaults = dict(
        is_active=True,
    )

    ALLOWED_ID_REGEX = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9_]{2,20}\Z")

    @classmethod
    def create(cls, room_id):
        valid_name = bool(cls.ALLOWED_ID_REGEX.match(room_id))
        if not valid_name:
            raise InvalidNameError

        with g.make_lock("robin", "create_%s" % room_id):
            try:
                cls._byID(room_id)
            except tdb_cassandra.NotFound:
                pass
            else:
                raise RoomExistsError

            room = cls(_id=room_id)
            room._commit()

            g.stats.simple_event('robin.room.make_new')
            g.stats.flush()

        return room

    @classmethod
    def get(cls, room_id):
        try:
            return cls._byID(room_id)
        except tdb_cassandra.NotFound:
            return

    def get_present_users(self):
        return UserPresenceByRoom.get_present_user_ids(self)


class UserPresenceByRoom(tdb_cassandra.View):
    _use_db = True
    _connection_pool = 'main'
    _fetch_all_columns = True
    _extra_schema_creation_args = dict(
        key_validation_class=tdb_cassandra.UTF8_TYPE,
    )

    _read_consistency_level = tdb_cassandra.CL.QUORUM
    _write_consistency_level = tdb_cassandra.CL.QUORUM

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
