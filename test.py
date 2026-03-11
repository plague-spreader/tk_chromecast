import pychromecast, yt_dlp
casts, browser = pychromecast.get_chromecasts()
cast = casts[0]
cast.start()
yt = yt_dlp.YoutubeDL()
info_obj = yt.extract_info("https://www.youtube.com/watch?v=8Zs7VWqNGHg", download=False, process=False)
