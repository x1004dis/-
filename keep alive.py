"""
keep_alive.py
Replit, Render(Web Service) 등에서 봇 프로세스가 종료되지 않도록
간단한 Flask 웹서버를 별도 스레드에서 실행합니다.

Render는 웹 서비스에 PORT 환경변수를 자동으로 주입하므로
config.PORT 가 이를 그대로 사용합니다.
"""

import logging
from threading import Thread

from flask import Flask

import config

app = Flask("ticket-bot-keep-alive")

# Flask 기본 로그가 너무 많이 출력되지 않도록 조정
_werkzeug_log = logging.getLogger("werkzeug")
_werkzeug_log.setLevel(logging.ERROR)


@app.route("/")
def home():
    return "티켓 관리 봇이 정상적으로 실행 중입니다. ✅"


@app.route("/health")
def health():
    return {"status": "ok"}


def run():
    app.run(host="0.0.0.0", port=config.PORT)


def keep_alive():
    thread = Thread(target=run, daemon=True)
    thread.start()
