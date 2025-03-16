#!/usr/bin/python3
import tkinter as tk
from chromecastui import ChromecastUI
from chromecast_select import SelectChromecast

import sys


if __name__ == "__main__":
    #root = tk.Tk()
    root = None
    app_select = SelectChromecast(root)
    app_select.run()
    if app_select.selected_cast is None:
        tk.messagebox.showinfo(
                "Chromecast",
                "No chromecast selected. Closing."
        )
    else:
        cast = app_select.selected_cast
        cast.wait()
        app = ChromecastUI(root, cast)
        app.run()
        app.disconnect()
        app.stop_http_server()
        print("Bye")
