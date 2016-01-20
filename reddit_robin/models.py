from r2.lib.db import tdb_cassandra


# TODO: an actual model
class RobinRoom(object):
    def __init__(self, id):
        self._id = id

    @classmethod
    def _byID(cls, id):
        if id not in ("example_a", "example_b", "example_c"):
            raise tdb_cassandra.NotFound
        return RobinRoom(id)
