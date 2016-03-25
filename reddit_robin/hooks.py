from r2.config import feature
from r2.lib.hooks import HookRegistrar
from r2.lib.pages import SideBox

hooks = HookRegistrar()


@hooks.on('home.add_sidebox')
def add_home_sidebox():
    if not feature.is_enabled('robin_on_homepage'):
        return None

    return SideBox(
        title="robin",
        css_class="robin_sidebox",
        link="/robin",
        target="_blank",
    )
