"""
utils.py
Embed 생성, 권한 체크, 로그 전송, TXT/HTML 트랜스크립트 생성 등
여러 모듈에서 공용으로 사용하는 유틸리티 함수 모음입니다.
"""

import html as html_lib
import io
from datetime import datetime, timezone

import discord

import config
from database import db


# ------------------------------------------------------------------ #
# Embed 빌더
# ------------------------------------------------------------------ #
def make_embed(title: str, description: str = "", color: int = None) -> discord.Embed:
    embed = discord.Embed(
        title=title,
        description=description,
        color=color if color is not None else config.EMBED_COLOR,
        timestamp=datetime.now(timezone.utc),
    )
    return embed


def panel_embed() -> discord.Embed:
    embed = make_embed(
        "🎫 티켓 지원 시스템",
        "도움이 필요하신가요?\n"
        "아래 **Create Ticket** 버튼을 눌러 문의 티켓을 생성해 주세요.\n\n"
        "⚠️ 사용자당 하나의 티켓만 생성할 수 있습니다.",
    )
    embed.set_footer(text="티켓 관리 시스템")
    return embed


def welcome_embed(owner: discord.abc.User, ticket_number: int) -> discord.Embed:
    embed = make_embed(
        f"🎫 티켓 #{ticket_number}",
        f"{owner.mention}님, 문의해주셔서 감사합니다.\n"
        "담당자가 곧 응답할 예정입니다. 문의 내용을 자세히 작성해 주세요.\n\n"
        "🔒 티켓을 닫으려면 아래 **닫기** 버튼을 눌러주세요.",
    )
    embed.set_footer(text=f"티켓 소유자: {owner}")
    return embed


def closed_embed(closer: discord.abc.User) -> discord.Embed:
    return make_embed(
        "🔒 티켓이 닫혔습니다",
        f"{closer.mention}님이 이 티켓을 닫았습니다.\n"
        "관리자는 재오픈, 저장, 삭제를 진행할 수 있습니다.",
        color=discord.Color.red().value,
    )


def log_embed(title: str, description: str, color: int = None) -> discord.Embed:
    return make_embed(
        title, description, color if color is not None else discord.Color.blurple().value
    )


# ------------------------------------------------------------------ #
# 권한 체크
# ------------------------------------------------------------------ #
async def is_admin(member: discord.Member) -> bool:
    """서버 관리자 권한, 지정된 관리자 역할, 혹은 /관리자추가 로 등록된 유저인지 확인합니다."""
    if not isinstance(member, discord.Member):
        return False

    if member.guild_permissions.administrator:
        return True

    settings = await db.get_settings(member.guild.id)
    if settings and settings["admin_role_id"]:
        role = member.guild.get_role(settings["admin_role_id"])
        if role is not None and role in member.roles:
            return True

    if await db.is_extra_admin(member.guild.id, member.id):
        return True

    return False


# ------------------------------------------------------------------ #
# 로그 전송
# ------------------------------------------------------------------ #
async def get_log_channel(guild: discord.Guild):
    settings = await db.get_settings(guild.id)
    if settings and settings["log_channel_id"]:
        return guild.get_channel(settings["log_channel_id"])
    return None


async def send_log(guild: discord.Guild, embed: discord.Embed) -> None:
    channel = await get_log_channel(guild)
    if channel is None:
        return
    try:
        await channel.send(embed=embed)
    except discord.HTTPException:
        pass


# ------------------------------------------------------------------ #
# 티켓 채널 이름 포맷
# ------------------------------------------------------------------ #
def format_ticket_name(fmt: str, count: int, user: discord.abc.User) -> str:
    if not fmt:
        fmt = "ticket-{count}"

    name = fmt.replace("{count}", str(count)).replace("{번호}", str(count))
    name = name.replace("{username}", user.name).replace("{유저}", user.name)
    name = name.replace(" ", "-").lower()

    if not name:
        name = f"ticket-{count}"

    return name[:90]


# ------------------------------------------------------------------ #
# 트랜스크립트 생성 (TXT / HTML)
# ------------------------------------------------------------------ #
async def generate_txt_transcript(channel: discord.TextChannel) -> io.BytesIO:
    lines = [
        f"티켓 채널: {channel.name}",
        f"저장 시각(UTC): {datetime.now(timezone.utc).isoformat()}",
        "-" * 60,
        "",
    ]

    async for message in channel.history(limit=None, oldest_first=True):
        ts = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
        author = f"{message.author} ({message.author.id})"
        content = message.content or ""
        lines.append(f"[{ts}] {author}: {content}")

        for att in message.attachments:
            lines.append(f"    [첨부파일] {att.filename} - {att.url}")

        for embed in message.embeds:
            if embed.title or embed.description:
                lines.append(
                    f"    [Embed] {embed.title or ''} {embed.description or ''}".strip()
                )

    data = "\n".join(lines).encode("utf-8")
    buffer = io.BytesIO(data)
    buffer.seek(0)
    return buffer


async def generate_html_transcript(channel: discord.TextChannel) -> io.BytesIO:
    rows = []

    async for message in channel.history(limit=None, oldest_first=True):
        ts = message.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        author = html_lib.escape(str(message.author))
        try:
            avatar = message.author.display_avatar.url
        except AttributeError:
            avatar = ""
        content = html_lib.escape(message.content or "").replace("\n", "<br>")

        attachments_html = ""
        for att in message.attachments:
            safe_url = html_lib.escape(att.url)
            safe_name = html_lib.escape(att.filename)
            attachments_html += (
                f'<div class="attachment">📎 '
                f'<a href="{safe_url}" target="_blank">{safe_name}</a></div>'
            )

        rows.append(
            f"""
            <div class="message">
                <img class="avatar" src="{avatar}" onerror="this.style.display='none'">
                <div class="content">
                    <div class="meta">
                        <span class="author">{author}</span>
                        <span class="time">{ts}</span>
                    </div>
                    <div class="text">{content}</div>
                    {attachments_html}
                </div>
            </div>
            """
        )

    html_doc = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>{html_lib.escape(channel.name)} - 티켓 기록</title>
<style>
    body {{ background:#313338; color:#dbdee1; font-family:'Segoe UI', 'Malgun Gothic', sans-serif; margin:0; padding:24px; }}
    h1 {{ color:#ffffff; border-bottom:2px solid #3f4147; padding-bottom:12px; }}
    .info {{ color:#949ba4; margin-bottom:16px; }}
    .message {{ display:flex; padding:10px 6px; border-bottom:1px solid #3f4147; }}
    .avatar {{ width:40px; height:40px; border-radius:50%; margin-right:14px; background:#5865f2; }}
    .meta {{ font-size:13px; color:#949ba4; margin-bottom:4px; }}
    .author {{ color:#ffffff; font-weight:600; margin-right:10px; }}
    .text {{ white-space:pre-wrap; word-wrap:break-word; line-height:1.5; }}
    .attachment {{ margin-top:6px; font-size:13px; }}
    .attachment a {{ color:#00a8fc; text-decoration:none; }}
    .attachment a:hover {{ text-decoration:underline; }}
</style>
</head>
<body>
<h1># {html_lib.escape(channel.name)} - 티켓 기록</h1>
<p class="info">저장 시각(UTC): {datetime.now(timezone.utc).isoformat()}</p>
<hr>
{''.join(rows)}
</body>
</html>"""

    buffer = io.BytesIO(html_doc.encode("utf-8"))
    buffer.seek(0)
    return buffer
