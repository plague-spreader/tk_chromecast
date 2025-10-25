from views import SelectChromecastView

import pychromecast
import pathlib
import pygubu

PROJECT_PATH = pathlib.Path(__file__).parent
PROJECT_UI = PROJECT_PATH / "gui.ui"
RESOURCE_PATHS = [PROJECT_PATH]


class SelectChromecast:
    def __init__(self, master=None):
        self.master = master
        self.builder = pygubu.Builder()
        self.builder.add_resource_paths(RESOURCE_PATHS)
        self.builder.add_from_file(PROJECT_UI)
        # Main widget
        self.mainwindow = self.builder.get_object("toplevel1", master)
        self.builder.connect_callbacks(self)

        self.listChromecasts = self.builder.get_object("listChromecasts")
        self.cast_view = SelectChromecastView(
                self.listChromecasts,
        )

        self._casts, browser = pychromecast.get_chromecasts()

        for cast in self._casts:
            self.cast_view.add_cast(
                    self.listChromecasts,
                    cast.cast_info.model_name,
                    cast.cast_info.friendly_name,
                    cast.cast_info.host
            )

        self.selected_cast = None

    def run(self):
        self.mainwindow.mainloop()

    def select_chromecast(self, event=None):
        cast_index = self.listChromecasts.selection()
        if cast_index != ():
            cast_index = int(cast_index[0][1:]) - 1
            self.selected_cast = self._casts[cast_index]
            print("Selected chromecast:", self.selected_cast)

    def select_chromecast_and_quit(self, event=None):
         self.select_chromecast(event)
         self.mainwindow.destroy()
