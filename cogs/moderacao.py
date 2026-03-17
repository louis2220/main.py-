"""cogs/moderacao.py — Moderação completa com warns persistentes."""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import timedelta
import logging
from db import database as db
from utils.constants import Colors, E, success_embed, error_embed, mod_embed, _now

log = logging.getLogger("multibot.mod")


class Moderacao(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _log(self, guild: discord.Guild, **kwargs):
        cfg = await db.get_guild_config(guild.id)
        ch_id = cfg.get("log_channel")
        if not ch_id:
            return
        ch = guild.get_channel(ch_id)
        if not isinstance(ch, discord.TextChannel):
            return
        emb = discord.Embed(
            title=kwargs.get("title", "Log"),
            description=kwargs.get("description", ""),
            color=Colors.MAIN,
        )
        emb.timestamp = _now()
        for name, value, inline in kwargs.get("fields", []):
            emb.add_field(name=name, value=value, inline=inline)
        try:
            await ch.send(embed=emb)
        except discord.HTTPException:
            pass

    def _hier_ok(self, inter: discord.Interaction, membro: discord.Member) -> str | None:
        if membro == inter.guild.me:
            return "Não posso agir sobre mim mesmo."
        if membro == inter.guild.owner:
            return "Não posso agir sobre o dono do servidor."
        if membro.top_role >= inter.guild.me.top_role:
            return "O cargo do membro é igual ou superior ao meu."
        if membro.top_role >= inter.user.top_role and inter.user != inter.guild.owner:
            return "O cargo do membro é igual ou superior ao seu."
        return None

    # ── Grupo /mod ─────────────────────────────────────────────────────────
    mod_group = app_commands.Group(
        name="mod",
        description="Ferramentas de moderação",
        default_permissions=discord.Permissions(moderate_members=True),
    )

    @mod_group.command(name="ban", description="Bane um membro do servidor")
    @app_commands.describe(membro="Membro", motivo="Motivo", delete_days="Dias de msgs a apagar (0–7)")
    @app_commands.default_permissions(ban_members=True)
    async def ban(self, inter: discord.Interaction, membro: discord.Member,
                  motivo: str = "Sem motivo", delete_days: app_commands.Range[int, 0, 7] = 0):
        await inter.response.defer(ephemeral=True)
        if err := self._hier_ok(inter, membro):
            return await inter.followup.send(embed=error_embed("Hierarquia", err), ephemeral=True)
        try:
            await membro.send(f"Você foi **banido** de **{inter.guild.name}**.\nMotivo: {motivo}")
        except Exception:
            pass
        await membro.ban(reason=f"{inter.user} — {motivo}", delete_message_days=delete_days)
        await inter.followup.send(embed=success_embed("Banido!",
            f"{E.STAFF} {membro.mention} (`{membro}`)\n{E.PIN} Motivo: {motivo}"
        ), ephemeral=True)
        await self._log(inter.guild, title=f"{E.ARROW_RED} Ban",
            description=f"{membro} banido por {inter.user}.",
            fields=[("Motivo", motivo, False)])

    @mod_group.command(name="unban", description="Desbane um usuário pelo ID")
    @app_commands.describe(user_id="ID do usuário banido", motivo="Motivo")
    @app_commands.default_permissions(ban_members=True)
    async def unban(self, inter: discord.Interaction, user_id: str, motivo: str = "Sem motivo"):
        await inter.response.defer(ephemeral=True)
        try:
            uid  = int(user_id)
            user = await self.bot.fetch_user(uid)
            await inter.guild.unban(user, reason=f"{inter.user} — {motivo}")
            await inter.followup.send(embed=success_embed("Desbanido!",
                f"{E.ARROW_GREEN} {user} foi desbanido.\n{E.PIN} Motivo: {motivo}"
            ), ephemeral=True)
            await self._log(inter.guild, title=f"{E.ARROW_GREEN} Unban",
                description=f"{user} desbanido por {inter.user}.", fields=[("Motivo", motivo, False)])
        except ValueError:
            await inter.followup.send(embed=error_embed("ID inválido", "Digite um número."), ephemeral=True)
        except discord.NotFound:
            await inter.followup.send(embed=error_embed("Não encontrado", "Usuário não está banido."), ephemeral=True)

    @mod_group.command(name="kick", description="Expulsa um membro do servidor")
    @app_commands.describe(membro="Membro", motivo="Motivo")
    @app_commands.default_permissions(kick_members=True)
    async def kick(self, inter: discord.Interaction, membro: discord.Member, motivo: str = "Sem motivo"):
        await inter.response.defer(ephemeral=True)
        if err := self._hier_ok(inter, membro):
            return await inter.followup.send(embed=error_embed("Hierarquia", err), ephemeral=True)
        try:
            await membro.send(f"Você foi **expulso** de **{inter.guild.name}**.\nMotivo: {motivo}")
        except Exception:
            pass
        await membro.kick(reason=f"{inter.user} — {motivo}")
        await inter.followup.send(embed=success_embed("Expulso!",
            f"{E.STAFF} {membro.mention}\n{E.PIN} Motivo: {motivo}"
        ), ephemeral=True)
        await self._log(inter.guild, title=f"{E.ARROW_ORANGE} Kick",
            description=f"{membro} expulso por {inter.user}.", fields=[("Motivo", motivo, False)])

    @mod_group.command(name="mute", description="Aplica timeout em um membro")
    @app_commands.describe(membro="Membro", minutos="Duração em minutos (1–40320)")
    @app_commands.default_permissions(moderate_members=True)
    async def mute(self, inter: discord.Interaction, membro: discord.Member,
                   minutos: app_commands.Range[int, 1, 40320], motivo: str = "Sem motivo"):
        await inter.response.defer(ephemeral=True)
        if err := self._hier_ok(inter, membro):
            return await inter.followup.send(embed=error_embed("Hierarquia", err), ephemeral=True)
        until = discord.utils.utcnow() + timedelta(minutes=minutos)
        await membro.timeout(until, reason=f"{inter.user} — {motivo}")
        await inter.followup.send(embed=success_embed("Silenciado!",
            f"{E.STAFF} {membro.mention}\n{E.ARROW_BLUE} Duração: {minutos} min\n"
            f"{E.LOADING} Expira: {discord.utils.format_dt(until, 'R')}"
        ), ephemeral=True)
        await self._log(inter.guild, title=f"{E.ARROW_YELLOW} Mute",
            description=f"{membro} silenciado por {inter.user} por {minutos} min.",
            fields=[("Motivo", motivo, False)])

    @mod_group.command(name="unmute", description="Remove o timeout de um membro")
    @app_commands.describe(membro="Membro")
    @app_commands.default_permissions(moderate_members=True)
    async def unmute(self, inter: discord.Interaction, membro: discord.Member):
        await inter.response.defer(ephemeral=True)
        if not membro.timed_out_until:
            return await inter.followup.send(
                embed=error_embed("Erro", f"{membro.mention} não está em timeout."), ephemeral=True
            )
        await membro.timeout(None, reason=f"Unmute por {inter.user}")
        await inter.followup.send(embed=success_embed("Timeout removido!",
            f"{E.ARROW_GREEN} {membro.mention} pode falar novamente."
        ), ephemeral=True)
        await self._log(inter.guild, title=f"{E.ARROW_GREEN} Unmute",
            description=f"Timeout de {membro} removido por {inter.user}.")

    @mod_group.command(name="limpar", description="Apaga mensagens do canal (1–100)")
    @app_commands.describe(quantidade="Número de mensagens")
    @app_commands.default_permissions(manage_messages=True)
    async def limpar(self, inter: discord.Interaction, quantidade: app_commands.Range[int, 1, 100]):
        await inter.response.defer(ephemeral=True)
        deleted = await inter.channel.purge(limit=quantidade)
        await inter.followup.send(embed=success_embed("Mensagens apagadas",
            f"{E.ARROW_BLUE} `{len(deleted)}` mensagem(ns) apagada(s)."
        ), ephemeral=True)
        await self._log(inter.guild, title=f"{E.WARN_IC} Limpar",
            description=f"{inter.user} apagou `{len(deleted)}` mensagem(ns) em {inter.channel.mention}.")

    # ── Warns ──────────────────────────────────────────────────────────────
    @mod_group.command(name="warn", description="Aplica um aviso formal a um membro")
    @app_commands.describe(membro="Membro", motivo="Motivo do aviso")
    @app_commands.default_permissions(moderate_members=True)
    async def warn(self, inter: discord.Interaction, membro: discord.Member, motivo: str):
        await inter.response.defer(ephemeral=True)
        total = await db.add_warn(inter.guild.id, membro.id, motivo, inter.user.id)
        try:
            await membro.send(
                f"{E.WARN_IC} Você recebeu um aviso em **{inter.guild.name}**.\n"
                f"**Motivo:** {motivo}\n**Total de avisos:** {total}"
            )
        except Exception:
            pass
        await inter.followup.send(embed=mod_embed(f"{E.WARN_IC} Aviso #{total} aplicado",
            f"{E.STAFF} {membro.mention}\n{E.PIN} Motivo: {motivo}\n{E.STAR} Total: `{total}`"
        ), ephemeral=True)
        await self._log(inter.guild, title=f"{E.WARN_IC} Warn",
            description=f"{membro} avisado por {inter.user}.",
            fields=[("Motivo", motivo, False), ("Total", str(total), True)])

    @mod_group.command(name="warns", description="Lista os avisos de um membro")
    @app_commands.describe(membro="Membro")
    @app_commands.default_permissions(moderate_members=True)
    async def warns(self, inter: discord.Interaction, membro: discord.Member):
        lista = await db.get_warns(inter.guild.id, membro.id)
        if not lista:
            return await inter.response.send_message(
                embed=success_embed("Sem avisos", f"{membro.mention} não tem avisos."), ephemeral=True
            )
        desc = "\n".join(
            f"{E.ARROW_BLUE} `{i+1}.` {w['motivo']} — "
            f"<t:{int(w['created_at'].timestamp())}:d>"
            for i, w in enumerate(lista)
        )
        emb = discord.Embed(
            title=f"{E.WARN_IC} Avisos de {membro.display_name}",
            description=desc, color=Colors.MAIN,
        )
        emb.set_thumbnail(url=membro.display_avatar.url)
        emb.set_footer(text=f"Total: {len(lista)} aviso(s)")
        emb.timestamp = _now()
        await inter.response.send_message(embed=emb, ephemeral=True)

    @mod_group.command(name="clearwarns", description="Remove todos os avisos de um membro")
    @app_commands.describe(membro="Membro")
    @app_commands.default_permissions(administrator=True)
    async def clearwarns(self, inter: discord.Interaction, membro: discord.Member):
        await db.clear_warns(inter.guild.id, membro.id)
        await inter.response.send_message(
            embed=success_embed("Avisos removidos", f"{E.ARROW_GREEN} Todos os avisos de {membro.mention} foram removidos."),
            ephemeral=True,
        )

    @mod_group.command(name="userinfo", description="Informações detalhadas sobre um membro")
    @app_commands.describe(membro="Membro (padrão: você mesmo)")
    async def userinfo(self, inter: discord.Interaction, membro: discord.Member = None):
        m     = membro or inter.user
        dados = await db.get_xp(inter.guild.id, m.id)
        warns = await db.get_warns(inter.guild.id, m.id)
        roles = [r.mention for r in reversed(m.roles) if r.name != "@everyone"]
        emb   = discord.Embed(title=f"{E.STAFF} {m.display_name}", color=Colors.MAIN)
        emb.set_thumbnail(url=m.display_avatar.url)
        emb.add_field(name=f"{E.SPARKLE} Tag",       value=str(m),                               inline=True)
        emb.add_field(name=f"{E.SYMBOL} ID",         value=f"`{m.id}`",                          inline=True)
        emb.add_field(name=f"{E.VERIFY} Bot?",       value="Sim" if m.bot else "Não",            inline=True)
        emb.add_field(name="Entrou",                 value=discord.utils.format_dt(m.joined_at, "R") if m.joined_at else "?", inline=True)
        emb.add_field(name="Conta criada",           value=discord.utils.format_dt(m.created_at, "R"), inline=True)
        emb.add_field(name=f"{E.TROPHY} Nível XP",  value=f"`{dados['level']}` · `{dados['xp']:,}` XP", inline=True)
        emb.add_field(name=f"{E.WARN_IC} Avisos",   value=str(len(warns)),                      inline=True)
        emb.add_field(name=f"Cargos ({len(roles)})",
                      value=" ".join(roles[:10]) + ("..." if len(roles) > 10 else "") if roles else "Nenhum",
                      inline=False)
        emb.set_footer(text=f"Solicitado por {inter.user.display_name}")
        emb.timestamp = _now()
        await inter.response.send_message(embed=emb, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderacao(bot))
