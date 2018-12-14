from sanic import Sanic
from sanic import response
from signal import signal, SIGINT
import asyncio
import os
import random

import aiohttp
from arsenic import get_session
from arsenic.browsers import Chrome
from arsenic.services import Chromedriver
from io import BytesIO

app = Sanic(__name__)

async def make_snapshot(website: str):
    
    service = Chromedriver(log_file=os.devnull)
    browser = Chrome(chromeOptions={ 'args': ['--headless', '--disable-gpu', '--hide-scrollbars', '--window-size=1920,1080', '--no-gpu' ] })

    async with get_session(service, browser) as session:
        await session.get(website)
        image = await session.get_screenshot()
        image.seek(0)

        async with aiohttp.ClientSession() as sess:

            headers = {
                "Authorization": "Client-ID 6656d64547a5031"
            }
            data = {
                "image": image,
            }

            async with sess.post("https://api.imgur.com/3/image", data=data, headers=headers) as r:
                link = (await r.json())["data"]["link"]

                return link

@app.route("/")
async def main(request):
    return response.text(
        "OwO, what's this? Made by F4stZ4p#3507 with ❤"
        )

@app.route("/v1/<website>")
async def web_screenshot(request, website):

    snap = await make_snapshot(f"https://{website}")

    return response.json({
        "status": response.status,
        "snap": snap,
        "website": website
        })

server = app.create_server(host="0.0.0.0", port=os.getenv("PORT"))

loop = asyncio.get_event_loop()
task = asyncio.ensure_future(server)
asyncio.set_event_loop(asyncio.SelectorEventLoop())
signal(SIGINT, lambda s, f: loop.stop())

try:
    loop.run_forever()
except:
    loop.stop()