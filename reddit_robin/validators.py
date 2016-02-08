from pylons.controllers.util import abort
from pylons import tmpl_context as c

from r2.lib.db import tdb_cassandra
from r2.lib.validator import Validator

from .models import RobinRoom


class VRobinRoom(Validator):
    def run(self, id):
        try:
            room = RobinRoom._byID(id)
        except tdb_cassandra.NotFound:
            abort(404)

        if not room.is_participant(c.user):
            abort(403)

        if not room.is_alive:
            abort(403)

        return room
