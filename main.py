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
        await self.tree.sync()

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
    description="Buscar artigos filosóficos por título"
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
        title="<a:51047animatedarrowwhite:1430338988765347850> Resultado filosófico",
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

class LatexView(View):
    def __init__(self, formula):
        super().__init__(timeout=None)
        self.formula = formula
        self.light = False

    @discord.ui.button(label="Copiar fórmula", style=discord.ButtonStyle.gray)
    async def copy_formula(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"`{self.formula}`", ephemeral=True)

    @discord.ui.button(label="Modo claro", style=discord.ButtonStyle.blurple)
    async def toggle_mode(self, interaction: discord.Interaction, button: discord.ui.Button):

        self.light = not self.light

        if self.light:
            latex = f"\\dpi{{300}}\\color{{black}}{{{self.formula}}}"
            embed_color = 0xFFFFFF
            button.label = "Modo escuro"
        else:
            latex = f"\\dpi{{300}}\\color{{white}}{{{self.formula}}}"
            embed_color = 0x2B2D31
            button.label = "Modo claro"

        url = f"https://latex.codecogs.com/png.image?{quote_plus(latex)}"

        embed = discord.Embed(color=embed_color)
        embed.set_image(url=url)

        await interaction.response.edit_message(embed=embed, view=self)


# ===================== COMANDO LATEX =====================

@bot.tree.command(name="latex", description="Renderiza fórmulas em LaTeX")
async def latex(interaction: discord.Interaction, formula: str):
    await interaction.response.defer()

    try:
        formula = formula.strip()

        if formula.startswith("$$") and formula.endswith("$$"):
            formula = formula[2:-2]

        if formula.startswith("$") and formula.endswith("$"):
            formula = formula[1:-1]

        formula = formula.strip()

        latex = f"\\dpi{{300}}\\color{{white}}{{{formula}}}"
        url = f"https://latex.codecogs.com/png.image?{quote_plus(latex)}"

        embed = discord.Embed(color=0x2B2D31)
        embed.set_image(url=url)

        await interaction.followup.send(
            embed=embed,
            view=LatexView(formula)
        )

        # logs
        if getattr(bot, "log_channel_id", None):
            log = bot.get_channel(bot.log_channel_id)
            if log:
                await log.send(f"🧮 {interaction.user.mention} gerou `{formula}`")

    except Exception as e:
        await interaction.followup.send(f"❌ Erro: {e}")


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
