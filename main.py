import discord
from discord import app_commands
import os
from datetime import datetime, timedelta
import itertools
from discord.ext import tasks
from discord.ui import View, Button

TOKEN = os.getenv("BOT_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.moderation = True

# ==================================================
# ------------------- BOT -------------------------
# ==================================================
class ModBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.log_channel_id = None

async def setup_hook(self):
    ID_DA_GUILDA = 1163654753008484453

    guild = discord.Object(id=ID_DA_GUILDA)
    self.tree.copy_global_to(guild=guild)
    await self.tree.sync(guild=guild)
    
bot = ModBot()

@bot.event
async def on_ready():
    print(f"✅ Bot online como {bot.user}")

# ==================================================
# ---------------- COMANDOS PÚBLICOS ----------------
# ==================================================

@bot.tree.command(name="ping", description="Verifica se o bot está online")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!")

# ==================================================
# ------------------ SETUP (ADMIN) -----------------
# ==================================================
@bot.tree.command(name="setup", description="Define o canal de logs")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction, canal: discord.TextChannel):
    bot.log_channel_id = canal.id
    await interaction.response.send_message(
        f"✅ Canal de logs definido para {canal.mention}"
    )

# ==================================================
# ------------------ BAN --------------------------
# ==================================================
@bot.tree.command(name="ban", description="Banir um membro")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, membro: discord.Member, motivo: str = "Sem motivo"):
    try:
        await membro.ban(reason=motivo)
        await interaction.response.send_message(
            f"<a:1812purple:1430339025520164974> {membro.mention} foi banido.\nMotivo: {motivo}"
        )
    except:
        await interaction.response.send_message(
            "❌ Não foi possível banir esse membro. Verifique permissões e hierarquia.",
            ephemeral=True
        )

# ==================================================
# ------------------ KICK -------------------------
# ==================================================
@bot.tree.command(name="kick", description="Expulsar um membro")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, membro: discord.Member, motivo: str = "Sem motivo"):
    try:
        await membro.kick(reason=motivo)
        await interaction.response.send_message(
            f"<a:22875nitro:1430339226129404004> {membro.mention} foi expulso.\nMotivo: {motivo}"
        )
    except:
        await interaction.response.send_message(
            "❌ Não foi possível expulsar esse membro.",
            ephemeral=True
        )

# ==================================================
# ------------------ MUTE (TIMEOUT) ----------------
# ==================================================
@bot.tree.command(name="mute", description="Aplicar timeout em um membro")
@app_commands.checks.has_permissions(moderate_members=True)
async def mute(interaction: discord.Interaction, membro: discord.Member, minutos: int):
    await interaction.response.defer()
    try:
        duração = discord.utils.utcnow() + timedelta(minutes=minutos)
        await membro.timeout(duração)
        await interaction.followup.send(
            f"<a:8865gloading:1430269021374119936> {membro.mention} ficou mutado por {minutos} minutos."
        )
    except Exception as e:
        await interaction.followup.send(
            "❌ Não foi possível aplicar o mute."
        )
        print(f"Erro no mute: {e}")

# ==================================================
# ------------------ UNMUTE -----------------------
# ==================================================
@bot.tree.command(name="unmute", description="Remover timeout de um membro")
@app_commands.checks.has_permissions(moderate_members=True)
async def unmute(interaction: discord.Interaction, membro: discord.Member):
    await interaction.response.defer()
    try:
        await membro.timeout(None)
        await interaction.followup.send(
            f"<a:4455lightbluefire:1430338771236294767> Timeout removido de {membro.mention}"
        )
    except Exception as e:
        await interaction.followup.send(
            "❌ Não foi possível remover o timeout."
        )
        print(f"Erro no unmute: {e}")

# ==================================================
# ------------------ CLEAR ------------------------
# ==================================================
@bot.tree.command(name="clear", description="Apagar mensagens")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, quantidade: int):
    await interaction.response.defer(ephemeral=True)
    try:
        deleted = await interaction.channel.purge(limit=quantidade)
        await interaction.followup.send(
            f"<a:32877animatedarrowbluelite:1430339008537428009> {len(deleted)} mensagens apagadas.",
            ephemeral=True
        )
    except:
        await interaction.followup.send(
            "❌ Não foi possível apagar as mensagens.",
            ephemeral=True
        )

# ==================================================
# ---------------- PESQUISA FILOSOFIA ----------------
# ==================================================

from urllib.parse import quote_plus

@bot.tree.command(
    name="filosofia",
    description="Buscar artigos acadêmicos por título"
)
async def filosofia(interaction: discord.Interaction, termo: str):
    await interaction.response.defer()

    exact = f"\"{termo}\""
    encoded = quote_plus(exact)
    normal = quote_plus(termo)

    # links
    sep_url = f"https://plato.stanford.edu/search/searcher.py?query={normal}"
    scholar_url = f"https://scholar.google.com/scholar?q={encoded}"
    springer_url = f"https://link.springer.com/search?query={normal}"
    annas_url = f"https://annas-archive.org/search?q={normal}"
    philpapers_url = f"https://philpapers.org/s/{normal}"
    archive_url = f"https://archive.org/search?query={normal}"

    titulo = termo.title()

    embed = discord.Embed(
        title="<a:9582dsicordveriyblack:1430269158024810598> Resultado de artigos encontrados",
        description=f"**Busca:** {termo}",
        color=0x2b2d31
    )

    embed.add_field(
        name="<a:51047animatedarrowwhite:1430338988765347850> Stanford Encyclopedia",
        value=f"[{titulo} — SEP]({sep_url})",
        inline=False
    )

    embed.add_field(
        name="<a:51047animatedarrowwhite:1430338988765347850> Scholar",
        value=f"[{titulo} — Academic paper]({scholar_url})",
        inline=False
    )

    embed.add_field(
        name="<a:51047animatedarrowwhite:1430338988765347850> PhilPapers",
        value=f"[{titulo} — PhilPapers entry]({philpapers_url})",
        inline=False
    )

    embed.add_field(
        name="<a:51047animatedarrowwhite:1430338988765347850> Springer",
        value=f"[{titulo} — Journal article]({springer_url})",
        inline=False
    )

    embed.add_field(
        name="<a:51047animatedarrowwhite:1430338988765347850> Library",
        value=f"[{titulo} — Book sources]({annas_url})",
        inline=False
    )

    embed.add_field(
        name="<a:51047animatedarrowwhite:1430338988765347850> Archive",
        value=f"[{titulo} — Digital archive]({archive_url})",
        inline=False
    )

    await interaction.followup.send(embed=embed)

# ===================== LATEX VIEW =====================

import re
import aiohttp
from discord.ui import View
from urllib.parse import quote

LATEX_PATTERN = re.compile(r"\$\$(.*?)\$\$|\$(.*?)\$", re.DOTALL)

# ===================== RENDER FUNÇÃO =====================

async def render_latex(formula: str, dark=True):
    color = "\\color{white}" if dark else "\\color{black}"
    background = "\\bg_black" if dark else "\\bg_white"

    payload = f"""
    \\dpi{{300}}
    {background}
    {color}
    {formula}
    """

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://quicklatex.com/latex3.f",
            data={
                "formula": payload,
                "fsize": "14px",
                "out": "1",
                "preamble": "\\usepackage{amsmath}\\usepackage{amssymb}\\usepackage{amsfonts}"
            }
        ) as resp:
            text = await resp.text()

    if "error" in text.lower():
        return None

    image_url = text.split()[0]
    return image_url


# ===================== VIEW =====================

class LatexView(View):
    def __init__(self, formula):
        super().__init__(timeout=None)
        self.formula = formula
        self.dark = True

    @discord.ui.button(label="Copiar fórmula", style=discord.ButtonStyle.gray)
    async def copy_formula(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"```latex\n{self.formula}\n```", ephemeral=True)

    @discord.ui.button(label="Modo claro", style=discord.ButtonStyle.blurple)
    async def toggle_mode(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.dark = not self.dark

        url = await render_latex(self.formula, dark=self.dark)

        embed = discord.Embed(color=0x2B2D31 if self.dark else 0xFFFFFF)
        embed.set_image(url=url)

        button.label = "Modo escuro" if not self.dark else "Modo claro"

        await interaction.response.edit_message(embed=embed, view=self)


# ===================== AUTO DETECT =====================

@bot.event
async def on_message(message: discord.Message):

    if message.author.bot:
        return

    matches = LATEX_PATTERN.findall(message.content)

    if not matches:
        return

    for match in matches:
        formula = match[0] if match[0] else match[1]
        formula = formula.strip()

        url = await render_latex(formula, dark=True)

        if not url:
            continue

        embed = discord.Embed(color=0x2B2D31)
        embed.set_image(url=url)

        await message.reply(embed=embed, view=LatexView(formula))

        if getattr(bot, "log_channel_id", None):
            log = bot.get_channel(bot.log_channel_id)
            if log:
                await log.send(
                    f"🧮 {message.author.mention} renderizou automaticamente:\n```latex\n{formula}\n```"
        )

# ===================== STATUS ROTATIVO =====================

status_list = [
    "🩵 Aprendendo matemática",
    "⚡ Olimpíadas",
    "🏆 OBMEP",
    "🏮 Assistindo filosofia"
]

cycle_status = itertools.cycle(status_list)


@tasks.loop(seconds=30)
async def rotate_status():
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=next(cycle_status)
        )
    )


# ===================== ON READY =====================

@bot.event
async def on_ready():
    rotate_status.start()

    # sincroniza slash commands (pra aparecer no perfil)
    await bot.tree.sync()

    print(f"Logado como {bot.user}")

# ==================== LOGS DE MODERAÇÃO ====================

# Função auxiliar para enviar logs
async def enviar_log(acao: str, membro: discord.Member, autor: discord.Member, motivo: str = None):
    if bot.log_channel_id:
        log_channel = bot.get_channel(bot.log_channel_id)
        msg = f"<a:1812purple:1430339025520164974> **Ação:** {acao}\n" \
              f"**Membro:** {membro.mention}\n" \
              f"**Por:** {autor.mention}"
        if motivo:
            msg += f"\n**Motivo:** {motivo}"
        await log_channel.send(msg)

# Exemplo de uso nos comandos de moderação:
# await enviar_log("Ban", membro, interaction.user, motivo)
# await enviar_log("Kick", membro, interaction.user, motivo)
# await enviar_log("Mute", membro, interaction.user, f"{minutos} min")
# await enviar_log("Unmute", membro, interaction.user)
# await enviar_log("Clear", interaction.user, f"{quantidade} mensagens")

# ------------------------------------------------------------

bot.run(TOKEN)
