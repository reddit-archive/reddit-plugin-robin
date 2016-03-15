from pylons import tmpl_context as c

from r2.lib.pages import Reddit
from r2.lib.wrapped import Templated
from r2.models import Account

from reddit_robin.models import RobinRoom


class RobinPage(Reddit):
    extra_stylesheets = Reddit.extra_stylesheets + ["robin.less"]

    def __init__(self, title, content, **kwargs):
        Reddit.__init__(self,
            title=title,
            show_sidebar=False,
            show_newsletterbar=False,
            content=content,
            **kwargs
        )

    def build_toolbars(self):
        return []


class RobinChatPage(RobinPage):
    pass


class RobinJoin(Templated):
    pass


class RobinAll(Templated):
    def __init__(self):
        all_rooms = list(RobinRoom.generate_alive_rooms())
        self.participants_by_room = {}
        for room in all_rooms:
            participant_ids = room.get_all_participants()
            participants = Account._byID(
                participant_ids, data=True, return_dict=False)
            self.participants_by_room[room.id] = participants
        Templated.__init__(self)


class RobinAdmin(Templated):
    pass


class RobinChat(Templated):
    pass
