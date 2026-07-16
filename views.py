"""
views.py
디스코드 UI(View/Button) 정의입니다.
모든 View 는 timeout=None 으로 설정된 영구(Persistent) View 이며,
custom_id 가 고정되어 있어 봇이 재시작되어도 버튼이 계속 동작합니다.

주의: ticket.py 와의 순환 참조(circular import)를 피하기 위해
      ticket 모듈은 콜백 함수 내부에서 지역(local) import 합니다.
"""

import asyncio

import discord

import utils


class TicketPanelView(discord.ui.View):
    """티켓 패널에 부착되는 '티켓 생성' 버튼."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Create Ticket",
        style=discord.ButtonStyle.green,
        emoji="🎫",
        custom_id="ticket_create_button",
    )
    async def create_ticket_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        import ticket  # 지역 import (순환 참조 방지)

        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            channel = await ticket.create_ticket_channel(
                interaction.guild, interaction.user, interaction.client
            )
            await interaction.followup.send(
                f"✅ 티켓이 생성되었습니다: {channel.mention}", ephemeral=True
            )
        except RuntimeError as e:
            await interaction.followup.send(f"⚠️ {e}", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send(
                "⚠️ 봇에게 채널을 생성할 권한이 없습니다.", ephemeral=True
            )


class TicketOpenView(discord.ui.View):
    """열려 있는 티켓 채널에 부착되는 '닫기' 버튼."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="닫기",
        style=discord.ButtonStyle.red,
        emoji="🔒",
        custom_id="ticket_close_button",
    )
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        import ticket  # 지역 import (순환 참조 방지)

        if not await utils.is_admin(interaction.user):
            await interaction.response.send_message(
                "⚠️ 관리자만 티켓을 닫을 수 있습니다.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        try:
            await ticket.close_ticket_channel(interaction.channel, interaction.user)
            await interaction.followup.send("✅ 티켓이 닫혔습니다.", ephemeral=True)
        except RuntimeError as e:
            await interaction.followup.send(f"⚠️ {e}", ephemeral=True)


class TicketClosedView(discord.ui.View):
    """닫힌 티켓 채널에 부착되는 '재오픈 / 저장(TXT,HTML) / 삭제' 버튼들."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="재오픈",
        style=discord.ButtonStyle.green,
        emoji="🔓",
        custom_id="ticket_reopen_button",
    )
    async def reopen_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        import ticket  # 지역 import (순환 참조 방지)

        if not await utils.is_admin(interaction.user):
            await interaction.response.send_message(
                "⚠️ 관리자만 티켓을 재오픈할 수 있습니다.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        try:
            await ticket.reopen_ticket_channel(interaction.channel, interaction.user)
            await interaction.followup.send("✅ 티켓이 재오픈되었습니다.", ephemeral=True)
        except RuntimeError as e:
            await interaction.followup.send(f"⚠️ {e}", ephemeral=True)

    @discord.ui.button(
        label="TXT 저장",
        style=discord.ButtonStyle.blurple,
        emoji="📄",
        custom_id="ticket_save_txt_button",
    )
    async def save_txt_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        import ticket  # 지역 import (순환 참조 방지)

        if not await utils.is_admin(interaction.user):
            await interaction.response.send_message(
                "⚠️ 관리자만 티켓을 저장할 수 있습니다.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        file = await ticket.save_ticket_transcript(interaction.channel, interaction.user, "txt")
        await interaction.followup.send("✅ TXT 파일로 저장되었습니다.", file=file, ephemeral=True)

    @discord.ui.button(
        label="HTML 저장",
        style=discord.ButtonStyle.blurple,
        emoji="🌐",
        custom_id="ticket_save_html_button",
    )
    async def save_html_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        import ticket  # 지역 import (순환 참조 방지)

        if not await utils.is_admin(interaction.user):
            await interaction.response.send_message(
                "⚠️ 관리자만 티켓을 저장할 수 있습니다.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        file = await ticket.save_ticket_transcript(interaction.channel, interaction.user, "html")
        await interaction.followup.send(
            "✅ HTML 파일로 저장되었습니다.", file=file, ephemeral=True
        )

    @discord.ui.button(
        label="삭제",
        style=discord.ButtonStyle.gray,
        emoji="🗑️",
        custom_id="ticket_delete_button",
    )
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await utils.is_admin(interaction.user):
            await interaction.response.send_message(
                "⚠️ 관리자만 티켓을 삭제할 수 있습니다.", ephemeral=True
            )
            return

        await interaction.response.send_message(
            "🗑️ 5초 후 이 티켓 채널이 삭제됩니다...", ephemeral=False
        )
        asyncio.create_task(_delayed_delete(interaction.channel, interaction.user))


async def _delayed_delete(channel: discord.TextChannel, deleter: discord.abc.User) -> None:
    import ticket  # 지역 import (순환 참조 방지)

    await asyncio.sleep(5)
    try:
        await ticket.delete_ticket_channel(channel, deleter)
    except RuntimeError:
        pass
