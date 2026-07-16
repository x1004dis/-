"""
config.py
환경변수(.env)를 읽어와 봇 전역에서 사용할 설정값을 제공합니다.
"""

import os
from dotenv import load_dotenv

# .env 파일 로드 (없어도 에러 없이 통과되며, 호스팅 환경변수를 그대로 사용합니다)
load_dotenv()

# 디스코드 봇 토큰 (필수)
TOKEN = os.getenv("DISCORD_TOKEN", "").strip()

# SQLite 데이터베이스 파일 경로
DB_PATH = os.getenv("DB_PATH", "ticket_bot.db").strip()

# 특정 길드(서버)에만 슬래시 명령어를 즉시 동기화하고 싶을 때 사용 (선택)
# 비워두면 글로벌로 동기화됩니다 (전파까지 최대 1시간 소요될 수 있음).
GUILD_ID = os.getenv("GUILD_ID", "").strip()

# Replit / Render 등에서 웹 서버를 띄워 봇을 계속 살아있게 할지 여부
KEEP_ALIVE = os.getenv("KEEP_ALIVE", "false").strip().lower() in ("1", "true", "yes", "on")

# keep_alive 웹서버가 사용할 포트 (Render는 PORT 환경변수를 자동 주입합니다)
try:
    PORT = int(os.getenv("PORT", "8080"))
except ValueError:
    PORT = 8080

# Embed 기본 색상 (16진수 문자열, 예: 2F3136)
_color_env = os.getenv("EMBED_COLOR", "").strip()
try:
    EMBED_COLOR = int(_color_env, 16) if _color_env else 0x2F3136
except ValueError:
    EMBED_COLOR = 0x2F3136
