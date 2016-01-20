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


class RobinHome(Templated):
    pass


class RobinChat(Templated):
    pass
