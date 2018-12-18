import asyncio
import os
import traceback

import psutil
import humanize
import aiohttp
from arsenic import get_session
from arsenic.browsers import Chrome
from arsenic.services import Chromedriver
from quart import Quart, jsonify, request, render_template_string

class MagmaChain(Quart):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.maincache = str()
        self.screen_count = 0
        self.process = psutil.Process()
        self.loop = asyncio.get_event_loop()
        self.session = None
        self.pending = dict()

        with open("main.html", "r") as f:
            self.maincache = f.read()

        self.service = Chromedriver(log_file=os.devnull)
        self.browser = Chrome(
            chromeOptions={
                "args": [
                    "--headless",
                    "--hide-scrollbars",
                    #"--no-gpu"
                    #"--disable-gpu"
                    "--window-size=1366,768",
                    "--ipc-connection-timeout=10",
                    "--max_old_space_size=20",
                    "--disable-mojo-local-storage",
                    ]
                }
            )

    async def init_session(self):
        self.session = aiohttp.ClientSession()

    async def make_snapshot(self, website: str):

        if self.session is None:
            await self.init_session()
    
        async with get_session(self.service, self.browser) as session:
            await session.get(website)
            image = await session.get_screenshot()
            image.seek(0)

            headers = {"Authorization": "Client-ID 6656d64547a5031"}
            data = {"image": image}

            async with self.session.post(
                "https://api.imgur.com/3/image", data=data, headers=headers
            ) as r:
            
                link = (await r.json())["data"]["link"]
                
                del image
                
                return link

# <h1 style="color:green; display:inline;">•</h1><h1 style="display:inline;"> Online</h1>

if __name__ == "__main__":
    app = MagmaChain(__name__)
    
    async def handle_screens():
        while True:
            if app.pending:
                for pending in list(app.pending.keys()):
                    link = await app.pending[pending]
                    app.pending.update({pending: link})
                    await asyncio.sleep(3)
            await asyncio.sleep(0.5)

    app.loop.create_task(handle_screens())

    @app.route("/")
    async def main():
        return app.maincache

    @app.route("/wakemydyno.txt")
    async def wmd():
        return "."

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
            snap = asyncio.Task(app.make_snapshot(website))
            app.pending.update({website: snap})
            while not isinstance(app.pending.get(website), str):
                await asyncio.sleep(0.5)
            link = app.pending[website]
            del app.pending[website]
            app.screen_count += 1
            return jsonify({"snapshot": link, 
                            "website": website, 
                            "status": 200, 
                           })
        except Exception:
            return traceback.format_exc()

    @app.route("/status")
    async def status():
        return f"""
        <html>
            <head>
            <link rel="icon" type="image/ico" href="favicon.ico">
            <meta property="og:title" content="MagmaChain" />
            <meta property="og:type" content="website" />
            <meta property="og:url" content="http://magmachain.herokuapp.com" />
            <meta property="og:description" content="A fast screenshot API made by F4stZ4p#3507 and chr1s#7185." />
            <meta name="theme-color" content="#D42A42" />
            <meta property="og:image" content="https://camo.githubusercontent.com/ada81cc539f272f5fb8e1931eb1fc157458cf06b/68747470733a2f2f692e696d6775722e636f6d2f5a706b4e7339322e706e67" />

                <style>
                    hr {{
                    background-color:#FFFFFF
                    }}
                    h1 {{
                    color:#FFFFFF
                    }}
                </style>
                <title>Screenshot API</title>
            <body style="background-color: #7289DA;font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;">
                <h1>
                    Status<hr>
                </h1>
                {os.environ.get("STATUS")}
                <hr><h1>Screenshots taken:
                {app.screen_count} screenshots!</h1>
                <hr><h1>Memory usage:
                {humanize.naturalsize(app.process.memory_full_info().uss)}</h1>
            </body>
            </head>
        </html>
        """

    app.run(host="0.0.0.0", port=os.getenv("PORT"), debug=True)
