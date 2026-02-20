import discord
from discord import app_commands
import os
from datetime import timedelta

TOKEN = os.getenv("BOT_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.moderation = True

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

# ------------------ COMANDOS PÚBLICOS ------------------

@bot.tree.command(
    name="ping",
    description="Verifica se o bot está online"
)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!")

# ------------------ COMANDOS ADMIN ------------------

@bot.tree.command(
    name="setup",
    description="Define o canal de logs",
    default_permissions=discord.Permissions(administrator=True)
)
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction, canal: discord.TextChannel):
    bot.log_channel_id = canal.id
    await interaction.response.send_message(
        f"✅ Canal de logs definido para {canal.mention}"
    )

# ------------------ MODERAÇÃO ------------------

@bot.tree.command(
    name="ban",
    description="Banir um membro",
    default_permissions=discord.Permissions(ban_members=True)
)
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, membro: discord.Member, motivo: str = "Sem motivo"):
    try:
        await membro.ban(reason=motivo)
        await interaction.response.send_message(
            f"🔨 {membro.mention} foi banido.\nMotivo: {motivo}"
        )
    except:
        await interaction.response.send_message(
            "❌ Não foi possível banir esse membro. Verifique permissões e hierarquia.",
            ephemeral=True
        )

@bot.tree.command(
    name="kick",
    description="Expulsar um membro",
    default_permissions=discord.Permissions(kick_members=True)
)
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, membro: discord.Member, motivo: str = "Sem motivo"):
    try:
        await membro.kick(reason=motivo)
        await interaction.response.send_message(
            f"👢 {membro.mention} foi expulso.\nMotivo: {motivo}"
        )
    except:
        await interaction.response.send_message(
            "❌ Não foi possível expulsar esse membro. Verifique permissões e hierarquia.",
            ephemeral=True
        )

@bot.tree.command(
    name="mute",
    description="Aplicar timeout em um membro",
    default_permissions=discord.Permissions(moderate_members=True)
)
@app_commands.checks.has_permissions(moderate_members=True)
async def mute(interaction: discord.Interaction, membro: discord.Member, minutos: int):
    await interaction.response.defer()

    try:
        duração = discord.utils.utcnow() + timedelta(minutes=minutos)
        await membro.timeout(duração)

        await interaction.followup.send(
            f"🔇 {membro.mention} ficou mutado por {minutos} minutos."
        )
    except Exception as e:
        await interaction.followup.send(
            "❌ Não foi possível aplicar o mute. Verifique permissões e hierarquia."
        )
        print(f"Erro no mute: {e}")

@bot.tree.command(
    name="unmute",
    description="Remover timeout de um membro",
    default_permissions=discord.Permissions(moderate_members=True)
)
@app_commands.checks.has_permissions(moderate_members=True)
async def unmute(interaction: discord.Interaction, membro: discord.Member):
    await interaction.response.defer()

    try:
        await membro.timeout(None)
        await interaction.followup.send(
            f"🔊 Timeout removido de {membro.mention}"
        )
    except Exception as e:
        await interaction.followup.send(
            "❌ Não foi possível remover o timeout."
        )
        print(f"Erro no unmute: {e}")

@bot.tree.command(
    name="clear",
    description="Apagar mensagens",
    default_permissions=discord.Permissions(manage_messages=True)
)
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, quantidade: int):
    await interaction.response.defer(ephemeral=True)

    try:
        deleted = await interaction.channel.purge(limit=quantidade)
        await interaction.followup.send(
            f"🧹 {len(deleted)} mensagens apagadas.",
            ephemeral=True
        )
    except:
        await interaction.followup.send(
            "❌ Não foi possível apagar as mensagens.",
            ephemeral=True
        )

# ------------------------------------------------

bot.run(TOKEN)
