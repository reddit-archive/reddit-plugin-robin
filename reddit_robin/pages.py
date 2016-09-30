from r2.lib.pages import Reddit
from r2.lib.wrapped import Templated


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


class RobinCreate(Templated):
    def __init__(self, room_id):
        self.room_id = room_id
        Templated.__init__(self)


class RobinChat(Templated):
    pass
