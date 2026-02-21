import asyncio
import itertools
import logging
import os
import re
from datetime import timedelta
from urllib.parse import quote_plus

import aiohttp
import discord
from discord import app_commands
from discord.ext import tasks
from discord.ui import View

# ==================================================
# ------------------- LOGGING ----------------------
# ==================================================

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ==================================================
# ------------------- CONFIG ----------------------
# ==================================================

TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "1163654753008484453"))

if not TOKEN:
    raise RuntimeError("Variável de ambiente BOT_TOKEN não definida.")

# ==================================================
# ------------------- INTENTS ----------------------
# ==================================================

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.moderation = True
intents.message_content = True

# ==================================================
# ------------------- BOT -------------------------
# ==================================================

class ModBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.log_channel_id: int | None = None

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        log.info(f"Slash commands sincronizados para guild {GUILD_ID}.")

    async def on_ready(self):
        log.info(f"Bot online como {self.user} (ID: {self.user.id})")
        if not rotate_status.is_running():
            rotate_status.start()

    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ):
        if isinstance(error, app_commands.MissingPermissions):
            msg = "❌ Você não tem permissão para usar este comando."
        elif isinstance(error, app_commands.BotMissingPermissions):
            msg = "❌ Eu não tenho permissões suficientes para executar isso."
        elif isinstance(error, app_commands.CommandOnCooldown):
            msg = f"⏳ Aguarde {error.retry_after:.1f}s antes de usar este comando novamente."
        else:
            msg = "❌ Ocorreu um erro ao executar esse comando."

        log.warning(f"Erro no comando '{interaction.command.name}': {error}")
        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except discord.HTTPException:
            pass

    async def log_action(self, *, title: str, description: str, color: discord.Color = discord.Color.orange()):
        if not self.log_channel_id:
            return
        channel = self.get_channel(self.log_channel_id)
        if not isinstance(channel, discord.TextChannel):
            return
        embed = discord.Embed(title=title, description=description, color=color)
        try:
            await channel.send(embed=embed)
        except discord.HTTPException as e:
            log.error(f"Falha ao enviar log: {e}")

bot = ModBot()

# ==================================================
# ---------------- COMANDOS PÚBLICOS ---------------
# ==================================================

@bot.tree.command(name="ping", description="Verifica se o bot está online e mostra a latência")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! Latência: `{latency}ms`")

# ==================================================
# ------------------ SETUP (ADMIN) -----------------
# ==================================================

@bot.tree.command(name="setup", description="Define o canal de logs do servidor")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction, canal: discord.TextChannel):
    bot.log_channel_id = canal.id
    await interaction.response.send_message(
        f"✅ Canal de logs definido para {canal.mention}", ephemeral=True
    )
    log.info(f"Canal de logs atualizado para #{canal.name} ({canal.id})")

# ==================================================
# ------------------ BAN --------------------------
# ==================================================

@bot.tree.command(name="ban", description="Banir um membro do servidor")
@app_commands.checks.has_permissions(ban_members=True)
@app_commands.describe(membro="Membro a ser banido", motivo="Motivo do banimento")
async def ban(interaction: discord.Interaction, membro: discord.Member, motivo: str = "Sem motivo especificado"):
    if membro == interaction.user:
        return await interaction.response.send_message("❌ Você não pode se banir.", ephemeral=True)
    if membro.top_role >= interaction.guild.me.top_role:
        return await interaction.response.send_message(
            "❌ Não consigo banir esse membro (cargo superior ao meu).", ephemeral=True
        )
    await interaction.response.defer()
    try:
        await membro.send(f"Você foi **banido** do servidor **{interaction.guild.name}**.\nMotivo: {motivo}")
    except (discord.Forbidden, discord.HTTPException):
        pass
    await membro.ban(reason=f"{interaction.user} — {motivo}", delete_message_days=0)
    embed = discord.Embed(
        title="🔨 Membro Banido",
        description=f"**Usuário:** {membro.mention} (`{membro}`)\n**Motivo:** {motivo}\n**Moderador:** {interaction.user.mention}",
        color=discord.Color.red(),
    )
    await interaction.followup.send(embed=embed)
    await bot.log_action(title="🔨 Ban", description=f"{membro} banido por {interaction.user}.\nMotivo: {motivo}", color=discord.Color.red())

# ==================================================
# ------------------ UNBAN ------------------------
# ==================================================

@bot.tree.command(name="unban", description="Desbanir um usuário pelo ID")
@app_commands.checks.has_permissions(ban_members=True)
@app_commands.describe(user_id="ID do usuário banido", motivo="Motivo do desbanimento")
async def unban(interaction: discord.Interaction, user_id: str, motivo: str = "Sem motivo especificado"):
    await interaction.response.defer(ephemeral=True)
    try:
        uid = int(user_id)
    except ValueError:
        return await interaction.followup.send("❌ ID inválido.", ephemeral=True)
    try:
        user = await bot.fetch_user(uid)
        await interaction.guild.unban(user, reason=f"{interaction.user} — {motivo}")
        await interaction.followup.send(f"✅ {user} (`{uid}`) foi desbanido.", ephemeral=True)
        await bot.log_action(title="✅ Unban", description=f"{user} desbanido por {interaction.user}.\nMotivo: {motivo}", color=discord.Color.green())
    except discord.NotFound:
        await interaction.followup.send("❌ Usuário não encontrado ou não está banido.", ephemeral=True)
    except discord.HTTPException as e:
        await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)

# ==================================================
# ------------------ KICK -------------------------
# ==================================================

@bot.tree.command(name="kick", description="Expulsar um membro do servidor")
@app_commands.checks.has_permissions(kick_members=True)
@app_commands.describe(membro="Membro a ser expulso", motivo="Motivo da expulsão")
async def kick(interaction: discord.Interaction, membro: discord.Member, motivo: str = "Sem motivo especificado"):
    if membro == interaction.user:
        return await interaction.response.send_message("❌ Você não pode se expulsar.", ephemeral=True)
    if membro.top_role >= interaction.guild.me.top_role:
        return await interaction.response.send_message(
            "❌ Não consigo expulsar esse membro (cargo superior ao meu).", ephemeral=True
        )
    await interaction.response.defer()
    try:
        await membro.send(f"Você foi **expulso** do servidor **{interaction.guild.name}**.\nMotivo: {motivo}")
    except (discord.Forbidden, discord.HTTPException):
        pass
    await membro.kick(reason=f"{interaction.user} — {motivo}")
    embed = discord.Embed(
        title="👢 Membro Expulso",
        description=f"**Usuário:** {membro.mention} (`{membro}`)\n**Motivo:** {motivo}\n**Moderador:** {interaction.user.mention}",
        color=discord.Color.orange(),
    )
    await interaction.followup.send(embed=embed)
    await bot.log_action(title="👢 Kick", description=f"{membro} expulso por {interaction.user}.\nMotivo: {motivo}", color=discord.Color.orange())

# ==================================================
# ------------------ MUTE --------------------------
# ==================================================

@bot.tree.command(name="mute", description="Aplicar timeout em um membro")
@app_commands.checks.has_permissions(moderate_members=True)
@app_commands.describe(membro="Membro a silenciar", minutos="Duração em minutos (máx. 40320)")
async def mute(interaction: discord.Interaction, membro: discord.Member, minutos: app_commands.Range[int, 1, 40320]):
    if membro.top_role >= interaction.guild.me.top_role:
        return await interaction.response.send_message("❌ Não consigo silenciar esse membro.", ephemeral=True)
    await interaction.response.defer()
    until = discord.utils.utcnow() + timedelta(minutes=minutos)
    await membro.timeout(until, reason=f"Mute por {interaction.user} — {minutos} min")
    embed = discord.Embed(
        title="🔇 Membro Silenciado",
        description=f"**Usuário:** {membro.mention}\n**Duração:** {minutos} minuto(s)\n**Moderador:** {interaction.user.mention}",
        color=discord.Color.yellow(),
    )
    await interaction.followup.send(embed=embed)
    await bot.log_action(title="🔇 Mute", description=f"{membro} silenciado por {interaction.user} por {minutos} minuto(s).", color=discord.Color.yellow())

# ==================================================
# ------------------ UNMUTE -----------------------
# ==================================================

@bot.tree.command(name="unmute", description="Remover timeout de um membro")
@app_commands.checks.has_permissions(moderate_members=True)
@app_commands.describe(membro="Membro para remover o timeout")
async def unmute(interaction: discord.Interaction, membro: discord.Member):
    await interaction.response.defer()
    if not membro.timed_out_until:
        return await interaction.followup.send(f"❌ {membro.mention} não está em timeout.", ephemeral=True)
    await membro.timeout(None, reason=f"Unmute por {interaction.user}")
    embed = discord.Embed(
        title="🔊 Timeout Removido",
        description=f"**Usuário:** {membro.mention}\n**Moderador:** {interaction.user.mention}",
        color=discord.Color.green(),
    )
    await interaction.followup.send(embed=embed)
    await bot.log_action(title="🔊 Unmute", description=f"Timeout de {membro} removido por {interaction.user}.", color=discord.Color.green())

# ==================================================
# ------------------ CLEAR ------------------------
# ==================================================

@bot.tree.command(name="clear", description="Apagar mensagens do canal")
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.describe(quantidade="Número de mensagens a apagar (1–100)")
async def clear(interaction: discord.Interaction, quantidade: app_commands.Range[int, 1, 100]):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=quantidade)
    await interaction.followup.send(f"✅ {len(deleted)} mensagem(ns) apagada(s).", ephemeral=True)
    await bot.log_action(
        title="🗑️ Clear",
        description=f"{interaction.user} apagou {len(deleted)} mensagem(ns) em {interaction.channel.mention}.",
        color=discord.Color.blurple(),
    )

# ==================================================
# ---------------- FILOSOFIA / PESQUISA -----------
# ==================================================

@bot.tree.command(name="filosofia", description="Buscar artigos e recursos acadêmicos por tema")
@app_commands.describe(termo="Tema ou título para buscar")
async def filosofia(interaction: discord.Interaction, termo: str):
    await interaction.response.defer()
    encoded = quote_plus(f'"{termo}"')
    normal = quote_plus(termo)
    titulo = termo.title()
    links = {
        "<a:51047animatedarrowwhite:1430338988765347850> Stanford Encyclopedia": (f"https://plato.stanford.edu/search/searcher.py?query={normal}", "SEP"),
        "<a:51047animatedarrowwhite:1430338988765347850> Google Scholar": (f"https://scholar.google.com/scholar?q={encoded}", "Academic paper"),
        "<a:51047animatedarrowwhite:1430338988765347850> PhilPapers": (f"https://philpapers.org/s/{normal}", "PhilPapers"),
        "<a:51047animatedarrowwhite:1430338988765347850> Springer": (f"https://link.springer.com/search?query={normal}", "Journal article"),
        "<a:51047animatedarrowwhite:1430338988765347850> Anna's Archive": (f"https://annas-archive.org/search?q={normal}", "Book sources"),
        "<a:51047animatedarrowwhite:1430338988765347850> Internet Archive": (f"https://archive.org/search?query={normal}", "Digital archive"),
    }
    embed = discord.Embed(
        title="<a:9582dsicordveriyblack:1430269158024810598> Recursos Acadêmicos",
        description=f"**Busca:** {termo}",
        color=0x2B2D31,
    )
    for field_name, (url, label) in links.items():
        embed.add_field(name=field_name, value=f"[{titulo} — {label}]({url})", inline=False)
    await interaction.followup.send(embed=embed)

# ==================================================
# ------------------ LATEX ------------------------
# ==================================================

LATEX_PATTERN_BLOCK  = re.compile(r'\$\$([ \s\S]+?)\$\$')
LATEX_PATTERN_INLINE = re.compile(r'\$(.+?)\$')


def message_to_latex(text: str) -> str | None:
    """
    Converte a mensagem inteira num único bloco LaTeX (estilo TeXiT).
    - $$ ... $$ → renderiza só a fórmula em modo display
    - $...$ inline → monta parágrafo com \text{} ao redor do texto normal
    - Sem LaTeX → retorna None
    """
    # Bloco display tem prioridade
    block = LATEX_PATTERN_BLOCK.search(text)
    if block:
        return block.group(1).strip()

    # Precisa ter pelo menos um inline
    if not LATEX_PATTERN_INLINE.search(text):
        return None

    parts = []
    last = 0
    for m in LATEX_PATTERN_INLINE.finditer(text):
        before = text[last:m.start()]
        if before:
            safe = before.replace('%', r'\%')
            parts.append(r'\text{' + safe + '}')
        parts.append(m.group(1))
        last = m.end()
    after = text[last:]
    if after:
        safe = after.replace('%', r'\%')
        parts.append(r'\text{' + safe + '}')

    return ' '.join(parts)


def codecogs_url(formula: str) -> str:
    """
    Gera URL do CodeCogs: GET puro, fundo branco, texto preto.
    DPI 110 = tamanho proporcional ao texto do Discord, sem cortar.
    """
    from urllib.parse import quote
    prefix = "\\dpi{110}\\bg{white}\\fg{black} "
    return "https://latex.codecogs.com/png.latex?" + quote(prefix + formula)



class LatexView(View):
    def __init__(self, formula: str):
        super().__init__(timeout=120)
        self.formula = formula

    @discord.ui.button(label="📋 Copiar fórmula", style=discord.ButtonStyle.secondary)
    async def copy_formula(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"```latex\n{self.formula}\n```", ephemeral=True
        )


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    latex = message_to_latex(message.content)
    log.info(f"[on_message] {message.author}: latex_gerado={bool(latex)}")

    if not latex:
        return

    url = codecogs_url(latex)
    log.info(f"[LaTeX] URL gerada com sucesso")

    embed = discord.Embed(color=0xFFFFFF)
    embed.set_image(url=url)
    embed.set_footer(text="Renderizado via CodeCogs")

    try:
        await message.reply(embed=embed, view=LatexView(message.content), mention_author=False)
    except discord.HTTPException as e:
        log.warning(f"[LaTeX] Erro ao enviar embed: {e}")


# ==================================================
# ---------------- STATUS ROTATIVO ----------------
# ==================================================

_STATUS_LIST = [
    ("Aprendendo matemática 🩵", discord.ActivityType.watching),
    ("Olimpíadas ⚡", discord.ActivityType.watching),
    ("OBMEP 🏆", discord.ActivityType.watching),
    ("Filosofia 🏮", discord.ActivityType.watching),
]

_cycle_status = itertools.cycle(_STATUS_LIST)


@tasks.loop(seconds=30)
async def rotate_status():
    name, activity_type = next(_cycle_status)
    await bot.change_presence(activity=discord.Activity(type=activity_type, name=name))


@rotate_status.before_loop
async def before_rotate():
    await bot.wait_until_ready()

# ==================================================
# -------------------- RUN ------------------------
# ==================================================

bot.run(TOKEN)
