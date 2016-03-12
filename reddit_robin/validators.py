from pylons.controllers.util import abort
from pylons import tmpl_context as c

from r2.lib.db import tdb_cassandra
from r2.lib.validator import Validator

from .models import RobinRoom


class VRobinRoom(Validator):
    def __init__(self, param, allow_admin=False):
        self.allow_admin = allow_admin
        Validator.__init__(self, param)

    def run(self, id):
        try:
            room = RobinRoom._byID(id)
        except tdb_cassandra.NotFound:
            abort(404)

        admin_override = self.allow_admin and c.user_is_admin
        if not (room.is_participant(c.user) or admin_override):
            abort(403)

        if not room.is_alive:
            abort(403)

        return room
