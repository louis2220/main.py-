"""
main.py — Bot Multifuncional
Banco de dados: PostgreSQL via asyncpg
Comandos: agrupados por /mod, /xp, /musica, /ticket, /config, /embed
"""

import asyncio
import itertools
import logging
import os
import sys

import discord
from discord import app_commands
from discord.ext import tasks

from db.database import init_pool
from utils.constants import Colors, E

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("multibot")

TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    log.critical("Variável BOT_TOKEN não definida!")
    sys.exit(1)

# ── Intents ───────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.members         = True
intents.guilds          = True
intents.message_content = True
intents.moderation      = True

# ── Cogs ──────────────────────────────────────────────────────────────────────
COGS = [
    "cogs.xp",
    "cogs.moderacao",
    "cogs.musica",
    "cogs.config",
    "cogs.tickets",
    "cogs.utilidade",
    "cogs.selfroles",
    "cogs.logs",
    "cogs.economia",
    "cogs.giveaway",
    "cogs.utilidades2",
]

# ── Status rotativos ──────────────────────────────────────────────────────────
_STATUS = itertools.cycle([
    "☕️ | bebendo um cafezinho",
    "📖 | lendo romance",
    "✨ | me adicione!",
    "🎵 | ouvindo música",
    "🌙 | vivendo por aí",
    "🎮 | jogando Mine",
    "🌿 | tomando um ar fresco",
])


class MultiBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # Inicializa banco de dados
        try:
            await init_pool()
            log.info("[DB] Banco de dados conectado.")
        except Exception as exc:
            log.critical(f"[DB] Falha ao conectar: {exc}")
            sys.exit(1)

        # Carrega cogs
        for cog in COGS:
            try:
                await self.load_extension(cog)
                log.info(f"[COG] ✓ {cog}")
            except Exception as exc:
                log.error(f"[COG] ✗ {cog}: {exc}", exc_info=True)

        # Sincroniza slash commands
        try:
            synced = await self.tree.sync()
            log.info(f"[SYNC] {len(synced)} comando(s) sincronizado(s).")
        except Exception as exc:
            log.error(f"[SYNC] Falha: {exc}")

    async def on_ready(self):
        log.info(f"[BOT] Online como {self.user} (ID: {self.user.id})")
        log.info(f"[BOT] Conectado a {len(self.guilds)} servidor(es).")
        if not rotate_status.is_running():
            rotate_status.start()

    async def on_app_command_error(self, inter: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            msg = f"{E.ARROW_RED} Você não tem permissão para usar este comando."
        elif isinstance(error, app_commands.BotMissingPermissions):
            msg = f"{E.ARROW_RED} O bot não tem permissões suficientes."
        elif isinstance(error, app_commands.CommandOnCooldown):
            msg = f"{E.LOADING} Aguarde `{error.retry_after:.1f}s` antes de usar novamente."
        else:
            cmd = inter.command.name if inter.command else "desconhecido"
            log.warning(f"[ERRO] Comando '{cmd}': {error}")
            msg = f"{E.ARROW_RED} Ocorreu um erro ao executar este comando."
        try:
            if inter.response.is_done():
                await inter.followup.send(msg, ephemeral=True)
            else:
                await inter.response.send_message(msg, ephemeral=True)
        except discord.HTTPException:
            pass

    async def on_guild_join(self, guild: discord.Guild):
        log.info(f"[GUILD] Entrou em: {guild.name} ({guild.id})")

    async def on_guild_remove(self, guild: discord.Guild):
        log.info(f"[GUILD] Saiu de: {guild.name} ({guild.id})")


bot = MultiBot()


@tasks.loop(seconds=30)
async def rotate_status():
    await bot.change_presence(
        activity=discord.CustomActivity(name=next(_STATUS)),
        status=discord.Status.online,
    )


@rotate_status.before_loop
async def before_rotate():
    await bot.wait_until_ready()


async def main():
    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("[BOT] Encerrado pelo usuário.")
    except discord.LoginFailure:
        log.critical("[BOT] Token inválido! Verifique BOT_TOKEN.")
        sys.exit(1)
