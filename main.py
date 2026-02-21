import discord
from discord import app_commands
import os
from datetime import timedelta

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
@bot.tree.command(
    name="filosofia",
    description="Pesquisar termo na Stanford Encyclopedia + Google Scholar/Google"
)
async def filosofia(interaction: discord.Interaction, termo: str):
    await interaction.response.defer()

    sep_url = f"https://plato.stanford.edu/search/searcher.py?query={termo.replace(' ', '+')}"
    scholar_url = f"https://scholar.google.com/scholar?q={termo.replace(' ', '+')}"
    google_url = f"https://www.google.com/search?q={termo.replace(' ', '+')}"

    embed = discord.Embed(
        title="<:5508discordstagechannel:1430269231982973069> Pesquisa Filosofia & Teologia",
        description=f"**Termo pesquisado:** {termo}",
        color=0x2b2d31
    )

    embed.add_field(
        name="<a:1812purple:1430339025520164974> Stanford Encyclopedia",
        value=f"[Pesquisar artigo na SEP]({sep_url})",
        inline=False
    )

    embed.add_field(
        name="<a:1503hearts:1430339028720549908> Google Scholar",
        value=f"[Pesquisar artigos acadêmicos]({scholar_url})",
        inline=False
    )

    embed.add_field(
        name="<a:8865gloading:1430269021374119936> Google",
        value=f"[Pesquisar no Google]({google_url})",
        inline=False
    )

    embed.set_footer(text="Fonte acadêmica + pesquisa online")
    await interaction.followup.send(embed=embed)

# ==================================================
# ------------------- RUN ------------------------
# ==================================================

# ==================================================
# 📝 LOGS + RENDERIZADOR DE FÓRMULAS (LaTeX)
# ==================================================

import io
import matplotlib.pyplot as plt
import discord
from datetime import datetime, timedelta

# ==================== COMANDO LATEX ====================

@bot.tree.command(name="latex", description="Renderiza fórmulas em LaTeX")
async def latex(interaction: discord.Interaction, formula: str):
    await interaction.response.defer()

    try:
        # Configura a imagem do matplotlib
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, f"${formula}$", fontsize=20, ha='center', va='center')
        ax.axis('off')

        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', transparent=True)
        buf.seek(0)
        plt.close(fig)

        file = discord.File(fp=buf, filename="formula.png")
        await interaction.followup.send(file=file)

        # ---------- LOGS ----------
        if bot.log_channel_id:
            log_channel = bot.get_channel(bot.log_channel_id)
            await log_channel.send(
                f"<a:8111discordverifypurple:1430269168908894369> {interaction.user.mention} gerou a fórmula: `{formula}`"
            )

    except Exception as e:
        await interaction.followup.send(f"❌ Erro ao renderizar a fórmula: {e}")
        if bot.log_channel_id:
            log_channel = bot.get_channel(bot.log_channel_id)
            await log_channel.send(
                f"❌ Erro ao gerar fórmula do usuário {interaction.user.mention}: {e}"
            )

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

# ---------------------------------------------------

bot.run(TOKEN)
