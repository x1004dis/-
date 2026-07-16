"""
ticket.py
티켓 생성 / 닫기 / 재오픈 / 삭제 / 저장에 대한 핵심 비즈니스 로직입니다.
슬래시 명령어(bot.py)와 버튼(views.py) 양쪽에서 이 모듈의 함수들을 호출합니다.

주의: views.py 와의 순환 참조(circular import)를 피하기 위해
      views 모듈은 함수 내부에서 지역(local) import 합니다.
"""

import io

import discord

import utils
from database import db


async def user_has_open_ticket(guild: discord.Guild, user: discord.abc.User) -> bool:
    """해당 유저가 이미 열려 있는 티켓을 가지고 있는지 확인합니다."""
    row = await db.get_open_ticket_by_owner(guild.id, user.id)
    if not row:
        return False

    channel = guild.get_channel(row["channel_id"])
    if channel is None:
        # 채널이 실제로는 삭제되었지만 DB에 남아있는 경우 -> 정리
        await db.delete_ticket(row["channel_id"])
        return False

    return True


async def create_ticket_channel(
    guild: discord.Guild, member: discord.Member, bot: discord.Client
) -> discord.TextChannel:
    settings = await db.get_settings(guild.id)

    if not settings or not settings["category_id"]:
        raise RuntimeError(
            "티켓 카테고리가 설정되지 않았습니다. `/티켓설정 카테고리` 명령어로 먼저 설정해 주세요."
        )

    category = guild.get_channel(settings["category_id"])
    if category is None or not isinstance(category, discord.CategoryChannel):
        raise RuntimeError("설정된 카테고리를 찾을 수 없습니다. `/티켓설정 카테고리`로 다시 설정해 주세요.")

    if await user_has_open_ticket(guild, member):
        raise RuntimeError("이미 열려 있는 티켓이 있습니다. 기존 티켓을 먼저 닫아주세요.")

    ticket_number = await db.next_ticket_number(guild.id)
    name_format = settings["ticket_name_format"] or "ticket-{count}"
    channel_name = utils.format_ticket_name(name_format, ticket_number, member)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        member: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True,
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_channels=True,
            manage_permissions=True,
            attach_files=True,
            embed_links=True,
        ),
    }

    if settings["admin_role_id"]:
        admin_role = guild.get_role(settings["admin_role_id"])
        if admin_role is not None:
            overwrites[admin_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
                manage_messages=True,
            )

    try:
        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"티켓 소유자: {member.id} | 상태: open",
            reason=f"{member} 님의 티켓 생성",
        )
    except discord.Forbidden:
        raise RuntimeError("봇에게 채널 생성 권한이 없습니다. 서버 관리자에게 문의해 주세요.")

    await db.create_ticket(guild.id, channel.id, member.id, ticket_number)

    import views  # 순환 참조 방지를 위한 지역 import

    embed = utils.welcome_embed(member, ticket_number)
    await channel.send(content=member.mention, embed=embed, view=views.TicketOpenView())

    await utils.send_log(
        guild,
        utils.log_embed(
            "🎫 티켓 생성",
            f"채널: {channel.mention}\n"
            f"생성자: {member.mention} ({member.id})\n"
            f"티켓 번호: #{ticket_number}",
            discord.Color.green().value,
        ),
    )

    return channel


async def close_ticket_channel(channel: discord.TextChannel, closer: discord.abc.User) -> None:
    ticket_row = await db.get_ticket_by_channel(channel.id)
    if not ticket_row:
        raise RuntimeError("이 채널은 티켓 채널이 아닙니다.")
    if ticket_row["status"] == "closed":
        raise RuntimeError("이미 닫힌 티켓입니다.")

    await db.close_ticket(channel.id)

    owner = channel.guild.get_member(ticket_row["owner_id"])
    if owner is not None:
        try:
            await channel.set_permissions(
                owner, view_channel=True, send_messages=False, read_message_history=True
            )
        except discord.HTTPException:
            pass

    import views  # 순환 참조 방지를 위한 지역 import

    await channel.send(embed=utils.closed_embed(closer), view=views.TicketClosedView())

    try:
        await channel.edit(topic=f"티켓 소유자: {ticket_row['owner_id']} | 상태: closed")
    except discord.HTTPException:
        pass

    await utils.send_log(
        channel.guild,
        utils.log_embed(
            "🔒 티켓 닫힘",
            f"채널: {channel.name} ({channel.id})\n"
            f"닫은 사람: {closer.mention} ({closer.id})",
            discord.Color.orange().value,
        ),
    )


async def reopen_ticket_channel(channel: discord.TextChannel, reopener: discord.abc.User) -> None:
    ticket_row = await db.get_ticket_by_channel(channel.id)
    if not ticket_row:
        raise RuntimeError("이 채널은 티켓 채널이 아닙니다.")
    if ticket_row["status"] == "open":
        raise RuntimeError("이미 열려있는 티켓입니다.")

    await db.reopen_ticket(channel.id)

    owner = channel.guild.get_member(ticket_row["owner_id"])
    if owner is not None:
        try:
            await channel.set_permissions(
                owner,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
            )
        except discord.HTTPException:
            pass

    import views  # 순환 참조 방지를 위한 지역 import

    await channel.send(
        embed=utils.make_embed(
            "🔓 티켓이 재오픈되었습니다", f"{reopener.mention}님이 티켓을 다시 열었습니다."
        ),
        view=views.TicketOpenView(),
    )

    try:
        await channel.edit(topic=f"티켓 소유자: {ticket_row['owner_id']} | 상태: open")
    except discord.HTTPException:
        pass

    await utils.send_log(
        channel.guild,
        utils.log_embed(
            "🔓 티켓 재오픈",
            f"채널: {channel.name} ({channel.id})\n"
            f"재오픈한 사람: {reopener.mention} ({reopener.id})",
            discord.Color.blue().value,
        ),
    )


async def delete_ticket_channel(channel: discord.TextChannel, deleter: discord.abc.User) -> None:
    ticket_row = await db.get_ticket_by_channel(channel.id)
    if not ticket_row:
        raise RuntimeError("이 채널은 티켓 채널이 아닙니다.")

    guild = channel.guild
    channel_name = channel.name
    owner_id = ticket_row["owner_id"]

    await db.delete_ticket(channel.id)

    await utils.send_log(
        guild,
        utils.log_embed(
            "🗑️ 티켓 삭제",
            f"채널: {channel_name}\n"
            f"티켓 소유자 ID: {owner_id}\n"
            f"삭제한 사람: {deleter.mention} ({deleter.id})",
            discord.Color.red().value,
        ),
    )

    try:
        await channel.delete(reason=f"티켓 삭제 by {deleter}")
    except discord.HTTPException:
        pass


async def save_ticket_transcript(
    channel: discord.TextChannel, saver: discord.abc.User, fmt: str
) -> discord.File:
    """티켓 대화 내용을 TXT 또는 HTML로 저장하고, 저장채널에 업로드한 뒤
    사용자가 다운로드할 수 있는 discord.File 객체를 반환합니다."""
    settings = await db.get_settings(channel.guild.id)

    if fmt == "txt":
        buffer = await utils.generate_txt_transcript(channel)
        filename = f"{channel.name}-transcript.txt"
    else:
        buffer = await utils.generate_html_transcript(channel)
        filename = f"{channel.name}-transcript.html"

    raw_bytes = buffer.getvalue()
    file_for_save_channel = discord.File(io.BytesIO(raw_bytes), filename=filename)
    file_for_user = discord.File(io.BytesIO(raw_bytes), filename=filename)

    save_channel = None
    if settings and settings["transcript_channel_id"]:
        save_channel = channel.guild.get_channel(settings["transcript_channel_id"])

    if save_channel is not None:
        try:
            await save_channel.send(
                content=f"📁 티켓 저장: **{channel.name}** (저장자: {saver})",
                file=file_for_save_channel,
            )
        except discord.HTTPException:
            pass

    await utils.send_log(
        channel.guild,
        utils.log_embed(
            "💾 티켓 저장",
            f"채널: {channel.name}\n"
            f"형식: {fmt.upper()}\n"
            f"저장한 사람: {saver.mention} ({saver.id})",
            discord.Color.teal().value,
        ),
    )

    return file_for_user
