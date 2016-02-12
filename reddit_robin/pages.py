from pylons import tmpl_context as c

from r2.lib.pages import Reddit
from r2.lib.wrapped import Templated

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


class RobinHome(Templated):
    pass


class RobinAll(Templated):
    def __init__(self):
        all_rooms = list(RobinRoom.generate_all_rooms())
        self.all_rooms = [room._id for room in all_rooms]
        self.user_rooms = [
            room._id for room in all_rooms if room.is_participant(c.user)]
        Templated.__init__(self)


class RobinChat(Templated):
    pass
