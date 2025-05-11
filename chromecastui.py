#!/usr/bin/python3

from tkinter import filedialog
from views import toggle_button

from threading import Thread

from lxml import html

import tkinter.ttk as ttk
import tkinter as tk
import pychromecast
import requests
import pathlib
import pygubu
import yt_dlp

import http.server
import socketserver
import socket


PROJECT_PATH = pathlib.Path(__file__).parent
PROJECT_UI = PROJECT_PATH / "gui.ui"
RESOURCE_PATHS = [PROJECT_PATH]

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


class HttpServer(Thread):
    def __init__(self, bind_host, bind_port, directory, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bind_host = bind_host
        self.bind_port = bind_port
        self.directory = directory

    def run(self):
        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self1, *args, **kwargs):
                super().__init__(*args, directory=self.directory, **kwargs)

        with socketserver.TCPServer((self.bind_host, self.bind_port),
                                    Handler) as httpd:
            self.httpd = httpd
            httpd.serve_forever()

    def stop(self):
        self.httpd.shutdown()


class UI:
    """Class for containing all relevant UI elements in one place"""

    def __init__(self, builder, *ui_elements):
        for ui_element in ui_elements:
            setattr(self, ui_element, builder.get_object(ui_element))

class ChromecastUI:
    def __init__(self, master, cast):
        self.master = master
        self.builder = pygubu.Builder()
        self.builder.add_resource_paths(RESOURCE_PATHS)
        self.builder.add_from_file(PROJECT_UI)
        # Main widget
        self.mainwindow: ttk.Notebook = self.builder.get_object(
            "notebook4", master)
        self.builder.connect_callbacks(self)

        self.ui = UI(self.builder,
                     "btnCreateHttpServer", "txtHttpDir", "txtHttpHost",
                     "txtHttpPort", "txtYtUrl", "btnToggleMute",
                     "sliderVolume", "lblCurrentlyPlaying", "btnPlayPause",
                     "sliderSeekTime", "listLocalFiles")

        # business logic
        self.deferred_jobs: list[Thread] = []
        self._http_server = None
        self.directory = None
        self._yt = yt_dlp.YoutubeDL()
        self._yt.params["quiet"] = True
        self._cast: pychromecast.Chromecast = cast
        self._mc: pychromecast.controllers.media.MediaController =\
                cast.media_controller

        self._get_current_cast_status()
        self._status_listener = MyListener(self)
        self._cast.register_status_listener(self._status_listener)
        self._mc.register_status_listener(self._status_listener)

    def run(self):
        self.mainwindow.mainloop()

    def _exec_deferred_jobs(self):
        for job in self.deferred_jobs:
            job.start()
        self.deferred_jobs.clear()

    def _get_current_cast_status(self):
        toggle_button(self._cast.status.volume_muted, self.ui.btnToggleMute)
        toggle_button(self._mc.status.player_state == "PAUSED",
                      self.ui.btnPlayPause)

        self.ui.sliderVolume.set(int(self._cast.status.volume_level*100))
        self.ui.sliderSeekTime.set(self._mc.status.current_time)

    def disconnect(self):
        self._cast.disconnect()

    def stop_http_server(self):
        if self._http_server is not None:
            self._http_server.stop()

    def browse_fileserver_dir(self, event=None):
        directory = filedialog.askdirectory()
        txt = self.ui.txtHttpDir
        txt.config(state="normal")
        txt.delete(0, tk.END)
        txt.insert(0, directory)
        txt.config(state="readonly")

    def create_stop_http_server(self, event=None):
        directory = self.ui.txtHttpDir.get()
        host = self.ui.txtHttpHost.get()
        port = self.ui.txtHttpPort.get()

        if not directory:
            tk.messagebox.showerror("Error", "No directory selected")
            return

        if not port:
            tk.messagebox.showerror("Error", "Port cannot be empty")
            return

        call_stop = self._http_server is not None and\
                self._http_server.is_alive()

        if not call_stop:
            try:
                port = int(port)
            except ValueError:
                tk.messagebox.showerror("Error", "Port must be an integer")
                return

            try:
                if is_port_in_use(port):
                    tk.messagebox.showerror("Error",
                                            f'Port "{port}" is already in use')
                    return
            except Exception as e:
                tk.messagebox.showerror("Error", e.args[0])
                return

        if call_stop:
            text = "Create HTTP server"
            self._http_server.stop()
        else:
            text = "Stop HTTP server"
            self._http_server = HttpServer(host, port, directory)
            self._http_server.start()

        self.ui.btnCreateHttpServer.config(text=text)

    def connect_http_server(self, event=None):
        host = self.ui.txtHttpHost.get()
        port = self.ui.txtHttpPort.get()

        if not host:
            tk.messagebox.showerror("Error", "Host cannot be empty")
            return

        if not port:
            tk.messagebox.showerror("Error", "Port cannot be empty")
            return

        self.http_base_url = f"http://{host}:{port}/"

        try:
            tree = html.fromstring(requests.get(self.http_base_url).text)
        except ConnectionError:
            tk.messagebox.showerror("Error",
                                    f"Cannot connect to {self.http_base_url}")
            return

        list_local_files: tk.Listbox = self.ui.listLocalFiles
        list_local_files.delete(0, "end")
        list_local_files.insert(0, *tree.xpath("//ul/li/a/@href"))

    def _get_list_local_selection(self):
        index = self.ui.listLocalFiles.curselection()
        try:
            index = index[0]
        except IndexError:
            return None

        return self.ui.listLocalFiles.get(index)

    def play_local_song(self, event=None):
        selection = self._get_list_local_selection()
        if selection is None:
            return

        url = self.http_base_url + selection

        self._mc.play_media(url, "audio/mp3", title=selection)
        self._exec_deferred_jobs()

    def enqueue_local_song(self, event=None):
        selection = self._get_list_local_selection()
        if selection is None:
            return

        url = self.http_base_url + selection

        self._mc.play_media(url, "audio/mp3", title=selection, enqueue=True,
                            autoplay=False)
        self._exec_deferred_jobs()

    @staticmethod
    def get_audio_url(info_obj) -> (bool, str):
        best_audio_quality = float("-inf")
        best_audio_url = None
        protocol = None
        for _format in info_obj["formats"]:
            if yt_dlp.YoutubeDL.format_resolution(_format) != "audio only":
                continue

            format_id = int(_format["format_id"])
            if format_id > best_audio_quality:
                best_audio_quality = format_id
                best_audio_url = _format["url"]
                protocol = _format["protocol"]

        return (protocol.startswith("m3u8"), best_audio_url)

    @staticmethod
    def handle_m3u8_url(url: str) -> list[str]:
        urls = []
        lines = requests.get(url).text.split("\n")
        for line in lines:
            if line.startswith("#"):
                continue
            if line.startswith("https://") or line.startswith("http://"):
                urls.append(line)
        return urls

    def _get_yt_url(self):
        url = self.ui.txtYtUrl.get()
        return url, self._yt.extract_info(url, download=False, process=False)

    def play_yt_url(self, event=None):
        url, info_obj = self._get_yt_url()
        title = info_obj["title"]
        m3u8_url, audio_url = ChromecastUI.get_audio_url(info_obj)
        if m3u8_url:
            audio_urls = ChromecastUI.handle_m3u8_url(audio_url)
            first_url = True
            for audio_url in audio_urls:
                if first_url:
                    first_url = False
                    self._mc.play_media(audio_url, "audio/mp3", title=title)
                else:
                    self._mc.play_media(audio_url, "audio/mp3",
                                    title=info_obj["title"], enqueue=True,
                                    autoplay=True)
        else:
            self._mc.play_media(audio_url, "audio/mp3", title=title)

        self._exec_deferred_jobs()

    def enqueue_yt_url(self, event=None):
        url, info_obj = self._get_yt_url()
        self._mc.play_media(ChromecastUI.get_audio_url(info_obj), "audio/mp3",
                            title=info_obj["title"], enqueue=True,
                            autoplay=True)
        self._exec_deferred_jobs()

    def player_toggle_mute(self, event=None):
        mute = not self._cast.status.volume_muted
        toggle_button(mute, self.ui.btnToggleMute)
        self._cast.set_volume_muted(mute)
        self._exec_deferred_jobs()

    def volume_change(self, event=None):
        volume = self.ui.sliderVolume.get()
        self._cast.set_volume(volume/100)
        self._exec_deferred_jobs()

    def seek_time_change(self, event=None):
        seek_time = self.ui.sliderSeekTime.get()
        self._mc.seek(seek_time)
        self._exec_deferred_jobs()

    def player_play_pause(self, event=None):
        if self._mc.status.player_state == "PLAYING":
            self._mc.pause()
            toggle_button(True, self.ui.btnPlayPause)
        elif self._mc.status.player_state == "PAUSED":
            self._mc.play()
            toggle_button(False, self.ui.btnPlayPause)
        else:
            # TODO che faccio qua?
            pass
        self._exec_deferred_jobs()

    def player_stop(self, event=None):
        self._mc.stop()
        self._exec_deferred_jobs()

    def player_prev(self, event=None):
        self._mc.queue_prev()
        self._exec_deferred_jobs()

    def player_next(self, event=None):
        self._mc.queue_next()
        self._exec_deferred_jobs()


class MyListener:
    def __init__(self, chromecastUI: ChromecastUI):
        self.ui = chromecastUI.ui
        self.deferred_jobs: list[Thread] = chromecastUI.deferred_jobs

    def new_cast_status(self, status):
        self.deferred_jobs.extend((
            Thread(target=self.ui.sliderVolume.set,
                   args=(int(status.volume_level*100),)),
            Thread(target=toggle_button,
                   args=(status.volume_muted, self.ui.btnToggleMute))
            ))

    def new_media_status(self, status):
        self.deferred_jobs.extend((
            Thread(target=self.ui.sliderSeekTime.config,
                   kwargs={"to": status.duration}),
            Thread(target=self.ui.sliderSeekTime.set,
                   args=(status.current_time,)),
            Thread(target=self.ui.lblCurrentlyPlaying.config,
                   kwargs={"text": status.title})
            ))


if __name__ == "__main__":
    root = tk.Tk()
    app = ChromecastUI(root)
    app.run()
