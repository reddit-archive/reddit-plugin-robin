from pylons.controllers.util import abort

from r2.lib.db import tdb_cassandra
from r2.lib.validator import Validator

from .models import RobinRoom


class VRobinRoom(Validator):
    def run(self, id):
        try:
            return RobinRoom._byID(id)
        except tdb_cassandra.NotFound:
            abort(404)
