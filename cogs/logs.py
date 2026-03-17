"""
cogs/logs.py — Logs completos do servidor.
Registra: entrou, saiu, ban, unban, mensagem editada, mensagem deletada,
          cargo adicionado/removido, canal criado/deletado, nickname alterado.
Comando: /logs setup, /logs desativar
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
from db.database import get_pool, upsert_guild_config, get_guild_config
from utils.constants import Colors, E, success_embed, error_embed, _now

log = logging.getLogger("multibot.logs")

# Cores por tipo de evento
_CORES = {
    "join":    0x57F287,  # verde
    "leave":   0xED4245,  # vermelho
    "ban":     0xED4245,
    "unban":   0x57F287,
    "msg_edit":   0xFEE75C,  # amarelo
    "msg_delete": 0xED4245,
    "role":    0x5865F2,  # azul
    "channel": 0x9B59B6,  # roxo
    "nick":    0xFEE75C,
}


class Logs(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _log_ch(self, guild: discord.Guild) -> discord.TextChannel | None:
        cfg = await get_guild_config(guild.id)
        ch_id = cfg.get("logs_channel") or cfg.get("log_channel")
        if not ch_id:
            return None
        ch = guild.get_channel(ch_id)
        return ch if isinstance(ch, discord.TextChannel) else None

    async def _send(self, guild: discord.Guild, emb: discord.Embed):
        ch = await self._log_ch(guild)
        if ch:
            try:
                await ch.send(embed=emb)
            except discord.HTTPException:
                pass

    def _base(self, titulo: str, tipo: str) -> discord.Embed:
        emb = discord.Embed(title=titulo, color=_CORES.get(tipo, Colors.MAIN))
        emb.timestamp = _now()
        return emb

    # ── Eventos ───────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        emb = self._base(f"📥 Membro entrou", "join")
        emb.set_thumbnail(url=member.display_avatar.url)
        emb.add_field(name="Membro",      value=f"{member.mention} (`{member}`)", inline=True)
        emb.add_field(name="ID",          value=f"`{member.id}`",                 inline=True)
        emb.add_field(name="Conta criada", value=discord.utils.format_dt(member.created_at, "R"), inline=True)
        emb.add_field(name="Membros",     value=f"`{member.guild.member_count}`", inline=True)
        await self._send(member.guild, emb)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        emb = self._base("📤 Membro saiu", "leave")
        emb.set_thumbnail(url=member.display_avatar.url)
        emb.add_field(name="Membro", value=f"{member} (`{member.id}`)", inline=True)
        roles = [r.mention for r in member.roles if r.name != "@everyone"]
        if roles:
            emb.add_field(name="Cargos", value=" ".join(roles[:10]), inline=False)
        await self._send(member.guild, emb)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        emb = self._base("🔨 Membro banido", "ban")
        emb.set_thumbnail(url=user.display_avatar.url)
        emb.add_field(name="Usuário", value=f"{user} (`{user.id}`)", inline=True)
        await self._send(guild, emb)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        emb = self._base("✅ Membro desbanido", "unban")
        emb.add_field(name="Usuário", value=f"{user} (`{user.id}`)", inline=True)
        await self._send(guild, emb)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild:
            return
        if before.content == after.content:
            return
        emb = self._base("✏️ Mensagem editada", "msg_edit")
        emb.set_author(name=str(before.author), icon_url=before.author.display_avatar.url)
        emb.add_field(name="Canal",  value=before.channel.mention, inline=True)
        emb.add_field(name="Autor",  value=before.author.mention,  inline=True)
        emb.add_field(name="Link",   value=f"[Ir para mensagem]({after.jump_url})", inline=True)
        emb.add_field(name="Antes",  value=(before.content or "*(vazio)*")[:400], inline=False)
        emb.add_field(name="Depois", value=(after.content or "*(vazio)*")[:400],  inline=False)
        await self._send(before.guild, emb)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        emb = self._base("🗑️ Mensagem deletada", "msg_delete")
        emb.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)
        emb.add_field(name="Canal",   value=message.channel.mention, inline=True)
        emb.add_field(name="Autor",   value=message.author.mention,  inline=True)
        if message.content:
            emb.add_field(name="Conteúdo", value=message.content[:800], inline=False)
        if message.attachments:
            emb.add_field(name="Anexos", value="\n".join(a.filename for a in message.attachments), inline=False)
        await self._send(message.guild, emb)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # Nick alterado
        if before.nick != after.nick:
            emb = self._base("📝 Nickname alterado", "nick")
            emb.set_thumbnail(url=after.display_avatar.url)
            emb.add_field(name="Membro", value=after.mention, inline=True)
            emb.add_field(name="Antes",  value=before.nick or before.name, inline=True)
            emb.add_field(name="Depois", value=after.nick or after.name,   inline=True)
            await self._send(after.guild, emb)

        # Cargo adicionado
        added   = set(after.roles) - set(before.roles)
        removed = set(before.roles) - set(after.roles)
        if added:
            emb = self._base(f"{E.TICKET_IC} Cargo adicionado", "role")
            emb.add_field(name="Membro", value=after.mention, inline=True)
            emb.add_field(name="Cargo",  value=" ".join(r.mention for r in added), inline=True)
            await self._send(after.guild, emb)
        if removed:
            emb = self._base(f"{E.MAGIC} Cargo removido", "role")
            emb.add_field(name="Membro", value=after.mention, inline=True)
            emb.add_field(name="Cargo",  value=" ".join(r.mention for r in removed), inline=True)
            await self._send(after.guild, emb)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        emb = self._base("📁 Canal criado", "channel")
        emb.add_field(name="Canal", value=f"{channel.mention} (`{channel.name}`)", inline=True)
        emb.add_field(name="Tipo",  value=str(channel.type).replace("ChannelType.", ""), inline=True)
        await self._send(channel.guild, emb)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        emb = self._base("🗑️ Canal deletado", "channel")
        emb.add_field(name="Canal", value=f"`{channel.name}`", inline=True)
        emb.add_field(name="Tipo",  value=str(channel.type).replace("ChannelType.", ""), inline=True)
        await self._send(channel.guild, emb)

    # ── Slash commands ─────────────────────────────────────────────────────

    logs_group = app_commands.Group(
        name="logs",
        description="Sistema de logs do servidor",
        default_permissions=discord.Permissions(administrator=True),
    )

    @logs_group.command(name="setup", description="Define o canal de logs do servidor")
    @app_commands.describe(canal="Canal onde os logs serão enviados")
    async def logs_setup(self, inter: discord.Interaction, canal: discord.TextChannel):
        await upsert_guild_config(inter.guild.id, logs_channel=canal.id, log_channel=canal.id)
        await inter.response.send_message(
            embed=success_embed("Logs configurados!",
                f"{E.ARROW_BLUE} Todos os eventos serão registrados em {canal.mention}.\n\n"
                f"{E.SYMBOL} **Eventos monitorados:**\n"
                f"{E.ARROW_BLUE} Entrada/saída de membros\n"
                f"{E.ARROW_BLUE} Banimentos e desbanimentos\n"
                f"{E.ARROW_BLUE} Mensagens editadas e deletadas\n"
                f"{E.ARROW_BLUE} Nickname alterado\n"
                f"{E.ARROW_BLUE} Cargos adicionados/removidos\n"
                f"{E.ARROW_BLUE} Canais criados/deletados"
            ),
            ephemeral=True,
        )

    @logs_group.command(name="desativar", description="Desativa o sistema de logs")
    async def logs_off(self, inter: discord.Interaction):
        await upsert_guild_config(inter.guild.id, logs_channel=None, log_channel=None)
        await inter.response.send_message(
            embed=success_embed("Logs desativados", "Os logs do servidor foram desativados."),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Logs(bot))
