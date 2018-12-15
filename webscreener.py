from quart import Quart
from quart import request, jsonify, render_template
import os

import aiohttp
from arsenic import get_session
from arsenic.browsers import Chrome
from arsenic.services import Chromedriver

app = Quart(__name__)


async def make_snapshot(website: str):

    service = Chromedriver(log_file=os.devnull)
    browser = Chrome(
        chromeOptions={
            "args": [
                "--headless",
                "--disable-gpu",
                "--hide-scrollbars",
                "--window-size=1920,1080",
                "--no-gpu",
                "--ipc-connection-timeout=10",
                "--disable-mojo-local-storage",
            ]
        }
    )

    async with get_session(service, browser) as session:
        await session.get(website)
        image = await session.get_screenshot()
        image.seek(0)

        async with aiohttp.ClientSession() as sess:

            headers = {"Authorization": "Client-ID 6656d64547a5031"}
            data = {"image": image}

            async with sess.post(
                "https://api.imgur.com/3/image", data=data, headers=headers
            ) as r:
                link = (await r.json())["data"]["link"]

                return link


@app.route("/")
async def main():
    return render_template("info.html")

@app.route("/api/v1", methods=["POST"])
@app.route("/v1", methods=["POST"])
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

    snapshot = await make_snapshot(website)

    return jsonify({"snapshot": snapshot, "website": website, "status": 200})


app.run(host="0.0.0.0", port=os.getenv("PORT"), debug=True)
