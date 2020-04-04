import asyncio
import os
import traceback

import psutil
import humanize
import aiohttp
from arsenic import get_session
from arsenic.browsers import Chrome
from arsenic.services import Chromedriver
from quart import Quart, jsonify, request, render_template, send_from_directory


class MagmaChain(Quart):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.screen_count = 0
        self.process = psutil.Process()
        self.session = None
        self.pending = dict()
        
        self.busy = False

        self.service = Chromedriver(log_file=os.devnull)
        self.browser = Chrome(
            chromeOptions={
                "args": [
                    "--headless",
                    "--hide-scrollbars",
                    "--window-size=1366,768",
                    "--ipc-connection-timeout=5",
                    "--max_old_space_size=10",
                    "--disable-mojo-local-storage",
                    "--enable-async-event-targeting",
                    "--enable-gpu-async-worker-context",
                ]
            }
        )

    async def init_session(self):
        self.session = aiohttp.ClientSession()

    async def make_snapshot(self, website: str):

        if self.session is None:
            await self.init_session()
            
        while self.busy:
            await asyncio.sleep(1)

        async with get_session(self.service, self.browser) as session:
            
            self.busy = True

            await session.get(website)
            image = await session.get_screenshot()
            image.seek(0)
            
            session.close()

            headers = {"Authorization": "Client-ID 6656d64547a5031"}
            data = {"image": image}

            async with self.session.post(
                "https://api.imgur.com/3/image", data=data, headers=headers
            ) as r:

                link = (await r.json())["data"]["link"]
                r.close()

                del image
                
                self.busy = False
                return link


# <h1 style="color:green; display:inline;">•</h1><h1 style="display:inline;"> Online</h1>

if __name__ == "__main__":
    app = MagmaChain(__name__)

    @app.route("/")
    async def main():
        return await render_template("new_main.html")

    @app.route("/old_main")
    async def old_main():
        return await render_template("old_main.html")

    @app.route("/api/v1", methods=["POST", "GET"])
    async def web_screenshot():

        website = request.headers.get("website")
        if website is None:
            return jsonify(
                {
                    "snapshot": "https://cdn1.iconfinder.com/data/icons/web-interface-part-2/32/circle-question-mark-512.png",
                    "website": "A website was not provided.",
                    "status": 400,
                }
            )

        if not (website.startswith("http://") or website.startswith("https://")):
            website = f"http://{website}"

        try:
            link = await app.make_snapshot(website)
            app.screen_count += 1
            return jsonify({"snapshot": link, "website": website, "status": 200})
        except Exception:
            return traceback.format_exc()

    @app.route("/favicon.ico")
    async def favicon():
        return await send_from_directory(".", "favicon.ico")

    @app.route("/status")
    async def status():
        return await render_template(
            "status.html",
            msg=os.environ.get("MESSAGE"),
            count=app.screen_count,
            mem=humanize.naturalsize(app.process.memory_full_info().uss),
        )

    app.run(host="0.0.0.0", port=os.getenv("PORT"), debug=True)
