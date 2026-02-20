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

# ------------------ COMANDO PÚBLICO ------------------

@bot.tree.command(name="ping", description="Verifica se o bot está online")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!")

# ------------------ SETUP (ADMIN) ------------------

@bot.tree.command(name="setup", description="Define o canal de logs")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction, canal: discord.TextChannel):
    bot.log_channel_id = canal.id
    await interaction.response.send_message(
        f"✅ Canal de logs definido para {canal.mention}"
    )

# ------------------ BAN ------------------

@bot.tree.command(name="ban", description="Banir um membro")
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

# ------------------ KICK ------------------

@bot.tree.command(name="kick", description="Expulsar um membro")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, membro: discord.Member, motivo: str = "Sem motivo"):
    try:
        await membro.kick(reason=motivo)
        await interaction.response.send_message(
            f"👢 {membro.mention} foi expulso.\nMotivo: {motivo}"
        )
    except:
        await interaction.response.send_message(
            "❌ Não foi possível expulsar esse membro.",
            ephemeral=True
        )

# ------------------ MUTE (TIMEOUT) ------------------

@bot.tree.command(name="mute", description="Aplicar timeout em um membro")
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
            "❌ Não foi possível aplicar o mute."
        )
        print(f"Erro no mute: {e}")

# ------------------ UNMUTE ------------------

@bot.tree.command(name="unmute", description="Remover timeout de um membro")
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

# ------------------ CLEAR ------------------

@bot.tree.command(name="clear", description="Apagar mensagens")
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

# ==================================================
# 🧠 FILOSOFIA + IA
# ==================================================

from openai import OpenAI

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
client_ai = OpenAI(api_key=OPENAI_KEY)

@bot.tree.command(name="filosofia", description="Pesquisar termo na Stanford Encyclopedia + resumo IA")
async def filosofia(interaction: discord.Interaction, termo: str):

    await interaction.response.defer()

    search_url = f"https://plato.stanford.edu/search/searcher.py?query={termo.replace(' ', '+')}"

    try:
        resposta = client_ai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Você é um assistente especializado em filosofia e teologia. Explique de forma clara e acadêmica."
                },
                {
                    "role": "user",
                    "content": f"Explique o conceito filosófico de: {termo}"
                }
            ],
            max_tokens=500
        )

        resumo = resposta.choices[0].message.content

    except Exception as e:
        resumo = "❌ Erro ao gerar resposta da IA."

    embed = discord.Embed(
        title="📚 Filosofia & Teologia",
        description=f"**Tema:** {termo}",
        color=0x2b2d31
    )

    embed.add_field(name="🧠 Explicação IA", value=resumo[:1024], inline=False)
    embed.add_field(name="🔎 Stanford Encyclopedia", value=f"[Pesquisar artigo]({search_url})", inline=False)
    embed.set_footer(text="Fonte acadêmica + IA")

    await interaction.followup.send(embed=embed)


# ------------------ PERGUNTAS LIVRES ------------------

@bot.tree.command(name="pergunta", description="Fazer pergunta filosófica ou teológica")
async def pergunta(interaction: discord.Interaction, pergunta: str):

    await interaction.response.defer()

    try:
        resposta = client_ai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Você é um especialista em filosofia e teologia. Responda de forma clara, acadêmica e respeitosa."
                },
                {
                    "role": "user",
                    "content": pergunta
                }
            ],
            max_tokens=600
        )

        texto = resposta.choices[0].message.content

    except Exception as e:
        texto = "❌ Erro ao consultar IA."

    embed = discord.Embed(
        title="🧠 Resposta Filosófica",
        description=texto[:4096],
        color=0x5865F2
    )

    await interaction.followup.send(embed=embed)
# -------------------------------------------------------

bot.run(TOKEN)
