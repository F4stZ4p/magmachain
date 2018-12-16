import asyncio
import gc
import os
import traceback

import psutil
import humanize
import aiohttp
from arsenic import get_session
from arsenic.browsers import Chrome
from arsenic.services import Chromedriver
from quart import Quart, jsonify, request

app = Quart(__name__)
maincache = str()
screen_count = 0
process = psutil.Process()
with open("main.html", "r") as f:
    maincache = f.read()

service = Chromedriver(log_file=os.devnull)
browser = Chrome(
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

async def make_snapshot(website: str):
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

                gc.collect()
                
                del image
                del sess
                
                return link


@app.route("/")
async def main():
    return maincache

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

    link = await make_snapshot(website)
    global screen_count
    screen_count += 1
    try:
        
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
            {screen_count} screenshots!</h1>
            <hr><h1>Memory usage:
            {humanize.naturalsize(process.memory_full_info().uss)}</h1>
        </body>
        </head>
    </html>
    """
# <h1 style="color:green; display:inline;">•</h1><h1 style="display:inline;"> Online</h1>

app.run(host="0.0.0.0", port=os.getenv("PORT"), debug=True)
