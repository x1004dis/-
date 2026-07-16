"""
bot.py
디스코드 티켓 관리 봇의 메인 실행 파일입니다.
모든 슬래시(Slash) 명령어가 이 파일에 정의되어 있으며,
실제 로직은 ticket.py / views.py / database.py / utils.py 를 통해 처리됩니다.

실행:
    python bot.py
"""

import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

import config
import ticket
import utils
import views
from database import db

# ------------------------------------------------------------------ #
# 로깅 설정
# ------------------------------------------------------------------ #
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ticket-bot")

# ------------------------------------------------------------------ #
# Intents
# ------------------------------------------------------------------ #
intents = discord.Intents.default()
intents.members = True
intents.message_content = True


class TicketBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self) -> None:
        # 데이터베이스 연결
        await db.connect()
        logger.info("데이터베이스 연결 완료 (%s)", config.DB_PATH)

        # 영구(Persistent) View 등록 - 재시작 후에도 버튼이 동작하도록 함
        self.add_view(views.TicketPanelView())
        self.add_view(views.TicketOpenView())
        self.add_view(views.TicketClosedView())
        logger.info("Persistent View 등록 완료")

        # /티켓설정 그룹 명령어 등록
        self.tree.add_command(ticket_settings_group)

        # 슬래시 명령어 동기화
        if config.GUILD_ID:
            guild_obj = discord.Object(id=int(config.GUILD_ID))
            self.tree.copy_global_to(guild=guild_obj)
            synced = await self.tree.sync(guild=guild_obj)
            logger.info("길드(%s)에 %d개의 명령어를 동기화했습니다.", config.GUILD_ID, len(synced))
        else:
            synced = await self.tree.sync()
            logger.info("글로벌로 %d개의 명령어를 동기화했습니다. (전파까지 최대 1시간 소요될 수 있습니다)", len(synced))


bot = TicketBot()


# ------------------------------------------------------------------ #
# 공용 체크 함수
# ------------------------------------------------------------------ #
async def require_admin(interaction: discord.Interaction) -> bool:
    """관리자 권한이 없으면 안내 메시지를 보내고 False 를 반환합니다."""
    if not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message(
            "⚠️ 이 명령어는 서버 내에서만 사용할 수 있습니다.", ephemeral=True
        )
        return False

    if await utils.is_admin(interaction.user):
        return True

    await interaction.response.send_message(
        "⚠️ 이 명령어는 관리자만 사용할 수 있습니다.", ephemeral=True
    )
    return False


def is_text_channel(channel: discord.abc.GuildChannel) -> bool:
    return isinstance(channel, discord.TextChannel)


# ------------------------------------------------------------------ #
# /티켓설정 (Group)
# ------------------------------------------------------------------ #
ticket_settings_group = app_commands.Group(
    name="티켓설정",
    description="티켓 시스템을 설정합니다 (관리자 전용)",
)


@ticket_settings_group.command(name="카테고리", description="티켓 채널이 생성될 카테고리를 설정합니다")
@app_commands.describe(category="티켓 채널이 생성될 카테고리")
async def settings_category(interaction: discord.Interaction, category: discord.CategoryChannel):
    if not await require_admin(interaction):
        return
    await db.set_category(interaction.guild.id, category.id)
    await interaction.response.send_message(
        f"✅ 티켓 카테고리가 **{category.name}** (으)로 설정되었습니다.", ephemeral=True
    )
    await utils.send_log(
        interaction.guild,
        utils.log_embed("⚙️ 설정 변경", f"티켓 카테고리 → **{category.name}**\n변경자: {interaction.user.mention}"),
    )


@ticket_settings_group.command(name="로그채널", description="티켓 로그가 전송될 채널을 설정합니다")
@app_commands.describe(channel="로그를 전송할 채널")
async def settings_log_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    if not await require_admin(interaction):
        return
    await db.set_log_channel(interaction.guild.id, channel.id)
    await interaction.response.send_message(
        f"✅ 로그 채널이 {channel.mention}(으)로 설정되었습니다.", ephemeral=True
    )
    await utils.send_log(
        interaction.guild,
        utils.log_embed("⚙️ 설정 변경", f"로그 채널 → {channel.mention}\n변경자: {interaction.user.mention}"),
    )


@ticket_settings_group.command(name="저장채널", description="티켓 저장 파일(TXT/HTML)이 업로드될 채널을 설정합니다")
@app_commands.describe(channel="저장 파일을 업로드할 채널")
async def settings_save_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    if not await require_admin(interaction):
        return
    await db.set_transcript_channel(interaction.guild.id, channel.id)
    await interaction.response.send_message(
        f"✅ 저장 채널이 {channel.mention}(으)로 설정되었습니다.", ephemeral=True
    )
    await utils.send_log(
        interaction.guild,
        utils.log_embed("⚙️ 설정 변경", f"저장 채널 → {channel.mention}\n변경자: {interaction.user.mention}"),
    )


@ticket_settings_group.command(name="관리자역할", description="티켓을 관리할 수 있는 역할을 설정합니다")
@app_commands.describe(role="티켓 관리 권한을 가질 역할")
async def settings_admin_role(interaction: discord.Interaction, role: discord.Role):
    if not await require_admin(interaction):
        return
    await db.set_admin_role(interaction.guild.id, role.id)
    await interaction.response.send_message(
        f"✅ 관리자 역할이 {role.mention}(으)로 설정되었습니다.", ephemeral=True
    )
    await utils.send_log(
        interaction.guild,
        utils.log_embed("⚙️ 설정 변경", f"관리자 역할 → {role.mention}\n변경자: {interaction.user.mention}"),
    )


@ticket_settings_group.command(name="이름형식", description="생성되는 티켓 채널의 이름 형식을 설정합니다")
@app_commands.describe(형식="예: ticket-{count}, 문의-{username}  ({count}, {username} 사용 가능)")
async def settings_name_format(interaction: discord.Interaction, 형식: str):
    if not await require_admin(interaction):
        return
    await db.set_name_format(interaction.guild.id, 형식)
    await interaction.response.send_message(
        f"✅ 티켓 이름 형식이 `{형식}`(으)로 설정되었습니다.", ephemeral=True
    )
    await utils.send_log(
        interaction.guild,
        utils.log_embed("⚙️ 설정 변경", f"이름 형식 → `{형식}`\n변경자: {interaction.user.mention}"),
    )


@ticket_settings_group.command(name="확인", description="현재 티켓 시스템 설정을 확인합니다")
async def settings_view(interaction: discord.Interaction):
    if not await require_admin(interaction):
        return

    settings = await db.get_settings(interaction.guild.id)
    if not settings:
        await interaction.response.send_message("⚠️ 아직 설정된 내용이 없습니다.", ephemeral=True)
        return

    category = interaction.guild.get_channel(settings["category_id"]) if settings["category_id"] else None
    log_channel = interaction.guild.get_channel(settings["log_channel_id"]) if settings["log_channel_id"] else None
    save_channel = (
        interaction.guild.get_channel(settings["transcript_channel_id"])
        if settings["transcript_channel_id"]
        else None
    )
    admin_role = interaction.guild.get_role(settings["admin_role_id"]) if settings["admin_role_id"] else None

    embed = utils.make_embed("⚙️ 현재 티켓 설정")
    embed.add_field(name="카테고리", value=(category.mention if category else "설정되지 않음"), inline=False)
    embed.add_field(name="로그 채널", value=(log_channel.mention if log_channel else "설정되지 않음"), inline=False)
    embed.add_field(name="저장 채널", value=(save_channel.mention if save_channel else "설정되지 않음"), inline=False)
    embed.add_field(name="관리자 역할", value=(admin_role.mention if admin_role else "설정되지 않음"), inline=False)
    embed.add_field(name="이름 형식", value=f"`{settings['ticket_name_format']}`", inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)


# ------------------------------------------------------------------ #
# /티켓패널
# ------------------------------------------------------------------ #
@bot.tree.command(name="티켓패널", description="티켓 생성 패널을 이 채널에 전송합니다 (관리자 전용)")
async def ticket_panel(interaction: discord.Interaction):
    if not await require_admin(interaction):
        return

    settings = await db.get_settings(interaction.guild.id)
    if not settings or not settings["category_id"]:
        await interaction.response.send_message(
            "⚠️ 먼저 `/티켓설정 카테고리` 명령어로 티켓 카테고리를 설정해 주세요.", ephemeral=True
        )
        return

    embed = utils.panel_embed()
    await interaction.channel.send(embed=embed, view=views.TicketPanelView())
    await interaction.response.send_message("✅ 티켓 패널이 전송되었습니다.", ephemeral=True)


# ------------------------------------------------------------------ #
# /관리자추가, /관리자제거
# ------------------------------------------------------------------ #
@bot.tree.command(name="관리자추가", description="티켓 관리자를 추가합니다 (관리자 전용)")
@app_commands.describe(user="관리자로 추가할 사용자")
async def add_admin(interaction: discord.Interaction, user: discord.Member):
    if not await require_admin(interaction):
        return
    await db.add_admin(interaction.guild.id, user.id)
    await interaction.response.send_message(
        f"✅ {user.mention}님이 티켓 관리자로 추가되었습니다.", ephemeral=True
    )
    await utils.send_log(
        interaction.guild,
        utils.log_embed(
            "👮 관리자 추가",
            f"{user.mention}님이 관리자로 추가됨\n실행자: {interaction.user.mention}",
        ),
    )


@bot.tree.command(name="관리자제거", description="티켓 관리자를 제거합니다 (관리자 전용)")
@app_commands.describe(user="관리자에서 제거할 사용자")
async def remove_admin(interaction: discord.Interaction, user: discord.Member):
    if not await require_admin(interaction):
        return
    await db.remove_admin(interaction.guild.id, user.id)
    await interaction.response.send_message(
        f"✅ {user.mention}님이 티켓 관리자에서 제거되었습니다.", ephemeral=True
    )
    await utils.send_log(
        interaction.guild,
        utils.log_embed(
            "👮 관리자 제거",
            f"{user.mention}님이 관리자에서 제거됨\n실행자: {interaction.user.mention}",
        ),
    )


# ------------------------------------------------------------------ #
# /티켓닫기, /티켓재오픈, /티켓삭제, /티켓저장
# ------------------------------------------------------------------ #
@bot.tree.command(name="티켓닫기", description="현재 채널의 티켓을 닫습니다 (관리자 전용)")
async def ticket_close(interaction: discord.Interaction):
    if not await require_admin(interaction):
        return
    if not is_text_channel(interaction.channel):
        await interaction.response.send_message(
            "⚠️ 이 명령어는 티켓 채널에서만 사용할 수 있습니다.", ephemeral=True
        )
        return

    try:
        await ticket.close_ticket_channel(interaction.channel, interaction.user)
        await interaction.response.send_message("✅ 티켓이 닫혔습니다.", ephemeral=True)
    except RuntimeError as e:
        await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)


@bot.tree.command(name="티켓재오픈", description="닫힌 티켓을 다시 엽니다 (관리자 전용)")
async def ticket_reopen(interaction: discord.Interaction):
    if not await require_admin(interaction):
        return
    if not is_text_channel(interaction.channel):
        await interaction.response.send_message(
            "⚠️ 이 명령어는 티켓 채널에서만 사용할 수 있습니다.", ephemeral=True
        )
        return

    try:
        await ticket.reopen_ticket_channel(interaction.channel, interaction.user)
        await interaction.response.send_message("✅ 티켓이 재오픈되었습니다.", ephemeral=True)
    except RuntimeError as e:
        await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)


@bot.tree.command(name="티켓삭제", description="티켓 채널을 완전히 삭제합니다 (관리자 전용)")
async def ticket_delete(interaction: discord.Interaction):
    if not await require_admin(interaction):
        return
    if not is_text_channel(interaction.channel):
        await interaction.response.send_message(
            "⚠️ 이 명령어는 티켓 채널에서만 사용할 수 있습니다.", ephemeral=True
        )
        return

    await interaction.response.send_message("🗑️ 5초 후 이 티켓 채널이 삭제됩니다...")
    channel = interaction.channel
    user = interaction.user
    await asyncio.sleep(5)
    try:
        await ticket.delete_ticket_channel(channel, user)
    except RuntimeError:
        pass


@bot.tree.command(name="티켓저장", description="티켓 대화 내용을 파일로 저장합니다 (관리자 전용)")
@app_commands.describe(형식="저장할 파일 형식을 선택하세요")
@app_commands.choices(
    형식=[
        app_commands.Choice(name="TXT", value="txt"),
        app_commands.Choice(name="HTML", value="html"),
    ]
)
async def ticket_save(interaction: discord.Interaction, 형식: app_commands.Choice[str]):
    if not await require_admin(interaction):
        return
    if not is_text_channel(interaction.channel):
        await interaction.response.send_message(
            "⚠️ 이 명령어는 티켓 채널에서만 사용할 수 있습니다.", ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True, thinking=True)
    file = await ticket.save_ticket_transcript(interaction.channel, interaction.user, 형식.value)
    await interaction.followup.send(f"✅ {형식.name} 파일로 저장되었습니다.", file=file, ephemeral=True)


# ------------------------------------------------------------------ #
# 오류 처리
# ------------------------------------------------------------------ #
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    logger.error("명령어 오류 발생: %s", error, exc_info=error)

    message = "⚠️ 명령어 실행 중 오류가 발생했습니다."
    if isinstance(error, app_commands.MissingPermissions):
        message = "⚠️ 이 명령어를 사용할 권한이 없습니다."
    elif isinstance(error, app_commands.CommandOnCooldown):
        message = f"⚠️ 명령어 쿨다운 중입니다. {error.retry_after:.1f}초 후 다시 시도해 주세요."

    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
    except discord.HTTPException:
        pass


# ------------------------------------------------------------------ #
# 이벤트
# ------------------------------------------------------------------ #
@bot.event
async def on_ready():
    logger.info("%s (ID: %s) 로그인 완료", bot.user, bot.user.id)
    try:
        await bot.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name="/티켓패널")
        )
    except discord.HTTPException:
        pass


# ------------------------------------------------------------------ #
# 실행부
# ------------------------------------------------------------------ #
def main():
    if not config.TOKEN:
        raise SystemExit(
            "DISCORD_TOKEN이 설정되지 않았습니다. .env 파일(또는 호스팅 환경변수)을 확인해 주세요."
        )

    if config.KEEP_ALIVE:
        from keep_alive import keep_alive

        keep_alive()
        logger.info("Keep-alive 웹서버가 포트 %d 에서 실행됩니다.", config.PORT)

    bot.run(config.TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
