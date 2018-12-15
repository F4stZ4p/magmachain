from quart import Quart
from quart import request, jsonify
import os
import traceback
import copy
import aiohttp
from arsenic import get_session
from arsenic.browsers import Chrome
from arsenic.services import Chromedriver

app = Quart(__name__)

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

async def make_snapshot(website: str):
    async with get_session(service, browser) as session:
        await session.get(website)
        image = await session.get_screenshot()
        image.seek(0)
        newimg = copy.copy(image)

        async with aiohttp.ClientSession() as sess:

            headers = {"Authorization": "Client-ID 6656d64547a5031"}
            data = {"image": image}

            async with sess.post(
                "https://api.imgur.com/3/image", data=data, headers=headers
            ) as r:
                link = (await r.json())["data"]["link"]

                return (link, newimg)


@app.route("/")
async def main():
    return """
    <html>
    <head>
    <style>
    hr {
        background-color:#FFFFFF
    }
    h1 {
        color:#FFFFFF
    }
    </style>
    <title>Screenshot API</title>
    <body style="background-color: #7289DA;text-align:center;font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;">
    <h1>
    OwO, what's this? Made by F4stZ4p#3507 and chr1s#7185 with ❤
    <hr>
    Endpoints:<br>
    POST /api/v1<br>
    Takes a screenshot of a website and returns an Imgur URL.
    <hr>
    Headers:<br><code>{"website": "URL"}</code>
    <hr>
    Returns:<br>
    <code>
    {"snapshot": "URL", "website": "URL", "status": 200}
    </code>
    </h1>
    </body>
    </head>
    </html>
    """

@app.route("/api/v1", methods=["POST", "GET"])
@app.route("/v1", methods=["POST", "GET"])
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

    link, image = await make_snapshot(website)
    try:
        return jsonify({"snapshot": link, "website": website, "status": 200, "raw": image.getvalue()})
    except Exception:
        return traceback.format_exc()

app.run(host="0.0.0.0", port=os.getenv("PORT"), debug=True)
