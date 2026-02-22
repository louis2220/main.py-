import itertools
import logging
import os
from datetime import timedelta
from urllib.parse import quote_plus

import discord
from discord import app_commands
from discord.ext import tasks
from discord.ui import View, Modal, TextInput

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
# ------------------- CORES -----------------------
# ==================================================

class Colors:
    MAIN = 0x590CEA  # Roxo meia-noite — cor padrão de todas as embeds

# ==================================================
# ------------------- EMOJIS ----------------------
# ==================================================

class E:
    # Setas animadas coloridas
    ARROW_BLUE   = "<a:32877animatedarrowbluelite:1430339008537428009>"
    ARROW_ORANGE = "<a:28079animatedarroworange:1430339004452044972>"
    ARROW_YELLOW = "<a:15770animatedarrowyellow:1430338999716806777>"
    ARROW_GREEN  = "<a:68523animatedarrowgreen:1430338981958123660>"
    ARROW_RED    = "<a:73288animatedarrowred:1430339017848787167>"

    # Ícones de interface Discord
    SEARCH   = "<:5864blurplesearch:1430269243374440478>"
    DISCORD  = "<:3970discord:1430269042161221834>"
    VERIFY   = "<a:8111discordverifypurple:1430269168908894369>"
    ANNOUNCE = "<:9098blurpleannouncements:1430269155063365734>"
    STAGE    = "<:5508discordstagechannel:1430269231982973069>"
    RULES    = "<:3149blurplerules:1430269036708761690>"
    SETTINGS = "<:1520blurplesettings:1430269149384413256>"
    STAFF    = "<:8968pastelstaff:1430339243854663710>"
    NITRO    = "<a:22875nitro:1430339226129404004>"
    LOADING  = "<a:8865gloading:1430269021374119936>"
    FIRE     = "<a:4455lightbluefire:1430338771236294767>"
    STAR     = "<a:94798starpur:1430339020646252604>"
    STAR_P   = "<a:1812purple:1430339025520164974>"
    FLYNITRO = "<a:44459flyingnitro:1430338788462428210>"

    # Ícones de ação/status
    INFO_IC  = "<:TCA_info:1446590981821436139>"
    WARN_IC  = "<a:i_exclamation:1446591025622679644>"
    PIN      = "<:w_p:1446590947902099556>"
    ARROW_W  = "<:w_seta:1446590852573958164>"
    WHITE_IC = "<:AZ_8white:1446590820894507130>"
    BRANCORE = "<:brancore:1446590909297987761>"

# ==================================================
# ------------------- BOT -------------------------
# ==================================================

class ModBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.log_channel_id: int | None = None

    async def setup_hook(self):
        # Sync global — aparece em TODOS os servidores onde o bot estiver
        await self.tree.sync()
        log.info("Slash commands sincronizados globalmente.")

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
            msg = f"{E.ARROW_RED} Você não tem permissão para usar este comando."
        elif isinstance(error, app_commands.BotMissingPermissions):
            msg = f"{E.ARROW_RED} Eu não tenho permissões suficientes para executar isso."
        elif isinstance(error, app_commands.CommandOnCooldown):
            msg = f"{E.LOADING} Aguarde `{error.retry_after:.1f}s` antes de usar este comando novamente."
        else:
            msg = f"{E.ARROW_RED} Ocorreu um erro ao executar esse comando."
            log.warning(f"Erro no comando '{interaction.command.name if interaction.command else 'unknown'}': {error}")

        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except discord.HTTPException:
            pass

    async def log_action(
        self,
        *,
        title: str,
        description: str,
        color: int = Colors.MAIN,
        fields: list[tuple[str, str, bool]] | None = None,
    ):
        if not self.log_channel_id:
            return
        channel = self.get_channel(self.log_channel_id)
        if not isinstance(channel, discord.TextChannel):
            return
        embed = discord.Embed(title=title, description=description, color=color)
        embed.timestamp = discord.utils.utcnow()
        if fields:
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)
        try:
            await channel.send(embed=embed)
        except discord.HTTPException as e:
            log.error(f"Falha ao enviar log: {e}")

bot = ModBot()

# ==================================================
# -------------- HELPERS DE EMBED -----------------
# ==================================================

def success_embed(title: str, description: str) -> discord.Embed:
    e = discord.Embed(
        title=f"{E.VERIFY} {title}",
        description=description,
        color=Colors.MAIN,
    )
    e.timestamp = discord.utils.utcnow()
    return e

def error_embed(title: str, description: str) -> discord.Embed:
    e = discord.Embed(
        title=f"{E.ARROW_RED} {title}",
        description=description,
        color=Colors.MAIN,
    )
    e.timestamp = discord.utils.utcnow()
    return e

def mod_embed(title: str, description: str) -> discord.Embed:
    e = discord.Embed(title=title, description=description, color=Colors.MAIN)
    e.timestamp = discord.utils.utcnow()
    return e

# ==================================================
# -------------- MODAL DE EMBED -------------------
# ==================================================

class EmbedModal(Modal, title="Criar Embed"):
    titulo = TextInput(
        label="Título",
        placeholder="Título do embed...",
        required=True,
        max_length=256,
    )
    descricao = TextInput(
        label="Descrição",
        placeholder="Conteúdo principal do embed...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=4000,
    )
    cor = TextInput(
        label="Cor (hex, ex: #590CEA)",
        placeholder="#590CEA",
        required=False,
        max_length=7,
    )
    rodape = TextInput(
        label="Rodapé",
        placeholder="Texto do rodapé (opcional)...",
        required=False,
        max_length=2048,
    )
    imagem_url = TextInput(
        label="URL da imagem (opcional)",
        placeholder="https://...",
        required=False,
        max_length=512,
    )

    def __init__(self, canal: discord.TextChannel):
        super().__init__()
        self.canal = canal

    async def on_submit(self, interaction: discord.Interaction):
        color = Colors.MAIN
        raw_color = self.cor.value.strip()
        if raw_color:
            try:
                color = int(raw_color.lstrip("#"), 16)
            except ValueError:
                await interaction.response.send_message(
                    embed=error_embed("Cor inválida", "Use o formato `#RRGGBB`, ex: `#590CEA`."),
                    ephemeral=True,
                )
                return

        embed = discord.Embed(
            title=self.titulo.value,
            description=self.descricao.value,
            color=color,
        )
        embed.timestamp = discord.utils.utcnow()

        if self.rodape.value.strip():
            embed.set_footer(text=self.rodape.value.strip())
        if self.imagem_url.value.strip():
            embed.set_image(url=self.imagem_url.value.strip())

        try:
            await self.canal.send(embed=embed)
            await interaction.response.send_message(
                embed=success_embed("Embed enviada!", f"Sua embed foi publicada em {self.canal.mention}."),
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("Sem permissão", f"Não tenho permissão para enviar mensagens em {self.canal.mention}."),
                ephemeral=True,
            )
        except discord.HTTPException as e:
            await interaction.response.send_message(
                embed=error_embed("Erro", f"Falha ao enviar embed: {e}"),
                ephemeral=True,
            )

# ==================================================
# ----------- VIEW DE PREVIEW DE EMBED ------------
# ==================================================

class EmbedBuilderView(View):
    """View interativa para construir embeds passo a passo."""

    def __init__(self, autor: discord.Member, canal: discord.TextChannel):
        super().__init__(timeout=300)
        self.autor = autor
        self.canal = canal

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.autor.id:
            await interaction.response.send_message(
                f"{E.ARROW_RED} Apenas quem iniciou pode usar esses botões.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Criar Embed", style=discord.ButtonStyle.primary, emoji="✏️")
    async def criar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EmbedModal(self.canal))

    @discord.ui.button(label="Anunciar", style=discord.ButtonStyle.success, emoji="📣")
    async def anunciar(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title=f"{E.ANNOUNCE} Anúncio",
            description="*(edite o conteúdo usando o botão Criar Embed)*",
            color=Colors.MAIN,
        )
        embed.timestamp = discord.utils.utcnow()
        await self.canal.send(embed=embed)
        await interaction.response.send_message(
            embed=success_embed("Anúncio enviado!", f"Publicado em {self.canal.mention}."),
            ephemeral=True,
        )

    @discord.ui.button(label="Regras", style=discord.ButtonStyle.secondary, emoji="📋")
    async def regras(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title=f"{E.RULES} Regras do Servidor",
            description=(
                f"Bem-vindo! Leia e respeite as regras abaixo.\n\n"
                f"{E.ARROW_BLUE} **1.** Respeite todos os membros.\n"
                f"{E.ARROW_BLUE} **2.** Sem spam ou flood.\n"
                f"{E.ARROW_BLUE} **3.** Sem conteúdo NSFW fora dos canais permitidos.\n"
                f"{E.ARROW_BLUE} **4.** Siga os Termos de Serviço do Discord.\n"
                f"{E.ARROW_BLUE} **5.** Decisões da staff são finais."
            ),
            color=Colors.MAIN,
        )
        embed.set_footer(text="Ao participar, você concorda com essas regras.")
        embed.timestamp = discord.utils.utcnow()
        await self.canal.send(embed=embed)
        await interaction.response.send_message(
            embed=success_embed("Regras enviadas!", f"Publicado em {self.canal.mention}."),
            ephemeral=True,
        )

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.danger, emoji="✖️")
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        await interaction.response.send_message(
            f"{E.ARROW_RED} Criação de embed cancelada.", ephemeral=True
        )

# ==================================================
# ------------ COMMAND: /embed --------------------
# ==================================================

@bot.tree.command(name="embed", description="Criar e enviar uma embed personalizada em um canal")
@app_commands.default_permissions(manage_messages=True)
@app_commands.describe(canal="Canal onde a embed será enviada")
async def embed_cmd(interaction: discord.Interaction, canal: discord.TextChannel):
    view = EmbedBuilderView(autor=interaction.user, canal=canal)
    preview = discord.Embed(
        title=f"{E.STAR} Construtor de Embeds",
        description=(
            f"Escolha uma opção abaixo para enviar uma embed em {canal.mention}.\n\n"
            f"{E.ARROW_BLUE} **Criar Embed** — totalmente customizado via formulário\n"
            f"{E.ARROW_BLUE} **Anunciar** — template de anúncio pronto\n"
            f"{E.ARROW_BLUE} **Regras** — template de regras formatado"
        ),
        color=Colors.MAIN,
    )
    preview.set_footer(text=f"Solicitado por {interaction.user.display_name}")
    preview.timestamp = discord.utils.utcnow()
    await interaction.response.send_message(embed=preview, view=view, ephemeral=True)

# ==================================================
# ------------ COMMAND: /embed-rapido -------------
# ==================================================

@bot.tree.command(name="embed-rapido", description="Envia uma embed simples rapidamente")
@app_commands.default_permissions(manage_messages=True)
@app_commands.describe(
    canal="Canal de destino",
    titulo="Título da embed",
    descricao="Descrição/conteúdo",
    cor="Cor em hex (ex: #590CEA) — padrão: roxo",
)
async def embed_rapido(
    interaction: discord.Interaction,
    canal: discord.TextChannel,
    titulo: str,
    descricao: str,
    cor: str = "#590CEA",
):
    try:
        color = int(cor.lstrip("#"), 16)
    except ValueError:
        return await interaction.response.send_message(
            embed=error_embed("Cor inválida", "Use o formato `#RRGGBB`."), ephemeral=True
        )

    embed = discord.Embed(title=titulo, description=descricao, color=color)
    embed.set_footer(text=f"por {interaction.user.display_name}")
    embed.timestamp = discord.utils.utcnow()

    try:
        await canal.send(embed=embed)
        await interaction.response.send_message(
            embed=success_embed("Enviado!", f"Embed publicada em {canal.mention}."), ephemeral=True
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            embed=error_embed("Sem permissão", f"Não posso enviar em {canal.mention}."), ephemeral=True
        )

# ==================================================
# ---------------- COMANDOS PÚBLICOS ---------------
# ==================================================

@bot.tree.command(name="ping", description="Verifica se o bot está online e mostra a latência")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title=f"{E.DISCORD} Pong!",
        description=f"{E.ARROW_BLUE} Latência da API: `{latency}ms`",
        color=Colors.MAIN,
    )
    embed.timestamp = discord.utils.utcnow()
    await interaction.response.send_message(embed=embed)

# ==================================================
# -------------- COMMAND: /userinfo ---------------
# ==================================================

@bot.tree.command(name="userinfo", description="Exibe informações sobre um membro")
@app_commands.describe(membro="Membro a consultar (padrão: você mesmo)")
async def userinfo(interaction: discord.Interaction, membro: discord.Member | None = None):
    membro = membro or interaction.user
    roles = [r.mention for r in reversed(membro.roles) if r.name != "@everyone"]
    embed = discord.Embed(
        title=f"{E.STAFF} {membro.display_name}",
        color=Colors.MAIN,
    )
    embed.set_thumbnail(url=membro.display_avatar.url)
    embed.add_field(name=f"{E.WHITE_IC} Tag",             value=str(membro), inline=True)
    embed.add_field(name=f"{E.INFO_IC} ID",               value=f"`{membro.id}`", inline=True)
    embed.add_field(name=f"{E.VERIFY} Bot?",              value="Sim" if membro.bot else "Não", inline=True)
    embed.add_field(
        name=f"{E.ARROW_BLUE} Entrou no servidor",
        value=discord.utils.format_dt(membro.joined_at, "R") if membro.joined_at else "Desconhecido",
        inline=True,
    )
    embed.add_field(
        name=f"{E.STAR} Conta criada",
        value=discord.utils.format_dt(membro.created_at, "R"),
        inline=True,
    )
    embed.add_field(
        name=f"{E.SETTINGS} Cargos ({len(roles)})",
        value=" ".join(roles[:10]) + ("..." if len(roles) > 10 else "") if roles else "Nenhum",
        inline=False,
    )
    embed.set_footer(text=f"Solicitado por {interaction.user.display_name}")
    embed.timestamp = discord.utils.utcnow()
    await interaction.response.send_message(embed=embed)

# ==================================================
# -------------- COMMAND: /serverinfo -------------
# ==================================================

@bot.tree.command(name="serverinfo", description="Exibe informações sobre o servidor")
async def serverinfo(interaction: discord.Interaction):
    g = interaction.guild
    embed = discord.Embed(
        title=f"{E.DISCORD} {g.name}",
        color=Colors.MAIN,
    )
    if g.icon:
        embed.set_thumbnail(url=g.icon.url)
    embed.add_field(name=f"{E.INFO_IC} ID",       value=f"`{g.id}`", inline=True)
    embed.add_field(name=f"{E.STAFF} Dono",       value=f"<@{g.owner_id}>", inline=True)
    embed.add_field(name=f"{E.STAGE} Região",     value=str(g.preferred_locale), inline=True)
    embed.add_field(name=f"{E.VERIFY} Membros",   value=f"`{g.member_count}`", inline=True)
    embed.add_field(name=f"{E.ANNOUNCE} Canais",  value=f"`{len(g.channels)}`", inline=True)
    embed.add_field(name=f"{E.SETTINGS} Cargos",  value=f"`{len(g.roles)}`", inline=True)
    embed.add_field(name=f"{E.STAR_P} Emojis",    value=f"`{len(g.emojis)}`", inline=True)
    embed.add_field(
        name=f"{E.NITRO} Boosts",
        value=f"`{g.premium_subscription_count}` (Nível {g.premium_tier})",
        inline=True,
    )
    embed.add_field(
        name=f"{E.ARROW_BLUE} Criado em",
        value=discord.utils.format_dt(g.created_at, "D"),
        inline=True,
    )
    embed.set_footer(text=f"Solicitado por {interaction.user.display_name}")
    embed.timestamp = discord.utils.utcnow()
    await interaction.response.send_message(embed=embed)

# ==================================================
# -------------- COMMAND: /avatar -----------------
# ==================================================

@bot.tree.command(name="avatar", description="Exibe o avatar de um membro em alta resolução")
@app_commands.describe(membro="Membro cujo avatar exibir")
async def avatar(interaction: discord.Interaction, membro: discord.Member | None = None):
    membro = membro or interaction.user
    embed = discord.Embed(
        title=f"{E.STAR} Avatar de {membro.display_name}",
        color=Colors.MAIN,
    )
    embed.set_image(url=membro.display_avatar.with_size(1024).url)
    embed.add_field(name=f"{E.SEARCH} Links", value=(
        f"[PNG]({membro.display_avatar.with_format('png').url}) · "
        f"[JPG]({membro.display_avatar.with_format('jpg').url}) · "
        f"[WEBP]({membro.display_avatar.with_format('webp').url})"
    ))
    embed.set_footer(text=f"Solicitado por {interaction.user.display_name}")
    embed.timestamp = discord.utils.utcnow()
    await interaction.response.send_message(embed=embed)

# ==================================================
# ------------------ SETUP (ADMIN) -----------------
# ==================================================

@bot.tree.command(name="setup", description="Define o canal de logs do servidor")
@app_commands.default_permissions(administrator=True)
async def setup(interaction: discord.Interaction, canal: discord.TextChannel):
    bot.log_channel_id = canal.id
    await interaction.response.send_message(
        embed=success_embed(
            "Configuração salva",
            f"{E.ARROW_BLUE} Canal de logs definido para {canal.mention}.",
        ),
        ephemeral=True,
    )
    log.info(f"Canal de logs atualizado para #{canal.name} ({canal.id})")

# ==================================================
# ------------------ BAN --------------------------
# ==================================================

@bot.tree.command(name="ban", description="Banir um membro do servidor")
@app_commands.default_permissions(ban_members=True)
@app_commands.checks.has_permissions(ban_members=True)
@app_commands.describe(membro="Membro a ser banido", motivo="Motivo do banimento")
async def ban(interaction: discord.Interaction, membro: discord.Member, motivo: str = "Sem motivo especificado"):
    if membro == interaction.user:
        return await interaction.response.send_message(
            embed=error_embed("Erro", "Você não pode se banir."), ephemeral=True
        )
    if membro.top_role >= interaction.guild.me.top_role:
        return await interaction.response.send_message(
            embed=error_embed("Sem permissão", "Não consigo banir esse membro (cargo superior ao meu)."), ephemeral=True
        )
    await interaction.response.defer()
    try:
        await membro.send(f"Você foi **banido** do servidor **{interaction.guild.name}**.\nMotivo: {motivo}")
    except (discord.Forbidden, discord.HTTPException):
        pass
    await membro.ban(reason=f"{interaction.user} — {motivo}", delete_message_days=0)
    embed = mod_embed(
        f"{E.ARROW_RED} Membro Banido",
        f"{E.STAFF} **Usuário:** {membro.mention} (`{membro}`)\n"
        f"{E.PIN} **Motivo:** {motivo}\n"
        f"{E.BRANCORE} **Moderador:** {interaction.user.mention}",
    )
    await interaction.followup.send(embed=embed)
    await bot.log_action(
        title=f"{E.ARROW_RED} Ban",
        description=f"{membro} banido por {interaction.user}.",
        fields=[("Motivo", motivo, False)],
    )

# ==================================================
# ------------------ UNBAN ------------------------
# ==================================================

@bot.tree.command(name="unban", description="Desbanir um usuário pelo ID")
@app_commands.default_permissions(ban_members=True)
@app_commands.checks.has_permissions(ban_members=True)
@app_commands.describe(user_id="ID do usuário banido", motivo="Motivo do desbanimento")
async def unban(interaction: discord.Interaction, user_id: str, motivo: str = "Sem motivo especificado"):
    await interaction.response.defer(ephemeral=True)
    try:
        uid = int(user_id)
    except ValueError:
        return await interaction.followup.send(
            embed=error_embed("ID inválido", "O ID precisa ser um número."), ephemeral=True
        )
    try:
        user = await bot.fetch_user(uid)
        await interaction.guild.unban(user, reason=f"{interaction.user} — {motivo}")
        await interaction.followup.send(
            embed=success_embed(
                "Usuário desbanido",
                f"{E.ARROW_GREEN} {user} (`{uid}`) foi desbanido.\n{E.PIN} **Motivo:** {motivo}",
            ),
            ephemeral=True,
        )
        await bot.log_action(
            title=f"{E.ARROW_GREEN} Unban",
            description=f"{user} desbanido por {interaction.user}.",
            fields=[("Motivo", motivo, False)],
        )
    except discord.NotFound:
        await interaction.followup.send(
            embed=error_embed("Não encontrado", "Usuário não encontrado ou não está banido."), ephemeral=True
        )
    except discord.HTTPException as e:
        await interaction.followup.send(embed=error_embed("Erro", str(e)), ephemeral=True)

# ==================================================
# ------------------ KICK -------------------------
# ==================================================

@bot.tree.command(name="kick", description="Expulsar um membro do servidor")
@app_commands.default_permissions(kick_members=True)
@app_commands.checks.has_permissions(kick_members=True)
@app_commands.describe(membro="Membro a ser expulso", motivo="Motivo da expulsão")
async def kick(interaction: discord.Interaction, membro: discord.Member, motivo: str = "Sem motivo especificado"):
    if membro == interaction.user:
        return await interaction.response.send_message(
            embed=error_embed("Erro", "Você não pode se expulsar."), ephemeral=True
        )
    if membro.top_role >= interaction.guild.me.top_role:
        return await interaction.response.send_message(
            embed=error_embed("Sem permissão", "Não consigo expulsar esse membro (cargo superior ao meu)."), ephemeral=True
        )
    await interaction.response.defer()
    try:
        await membro.send(f"Você foi **expulso** do servidor **{interaction.guild.name}**.\nMotivo: {motivo}")
    except (discord.Forbidden, discord.HTTPException):
        pass
    await membro.kick(reason=f"{interaction.user} — {motivo}")
    embed = mod_embed(
        f"{E.ARROW_ORANGE} Membro Expulso",
        f"{E.STAFF} **Usuário:** {membro.mention} (`{membro}`)\n"
        f"{E.PIN} **Motivo:** {motivo}\n"
        f"{E.BRANCORE} **Moderador:** {interaction.user.mention}",
    )
    await interaction.followup.send(embed=embed)
    await bot.log_action(
        title=f"{E.ARROW_ORANGE} Kick",
        description=f"{membro} expulso por {interaction.user}.",
        fields=[("Motivo", motivo, False)],
    )

# ==================================================
# ------------------ MUTE --------------------------
# ==================================================

@bot.tree.command(name="mute", description="Aplicar timeout em um membro")
@app_commands.default_permissions(moderate_members=True)
@app_commands.checks.has_permissions(moderate_members=True)
@app_commands.describe(membro="Membro a silenciar", minutos="Duração em minutos (máx. 40320)")
async def mute(interaction: discord.Interaction, membro: discord.Member, minutos: app_commands.Range[int, 1, 40320]):
    if membro.top_role >= interaction.guild.me.top_role:
        return await interaction.response.send_message(
            embed=error_embed("Sem permissão", "Não consigo silenciar esse membro."), ephemeral=True
        )
    await interaction.response.defer()
    until = discord.utils.utcnow() + timedelta(minutes=minutos)
    await membro.timeout(until, reason=f"Mute por {interaction.user} — {minutos} min")
    embed = mod_embed(
        f"{E.ARROW_YELLOW} Membro Silenciado",
        f"{E.STAFF} **Usuário:** {membro.mention}\n"
        f"{E.ARROW_BLUE} **Duração:** {minutos} minuto(s)\n"
        f"{E.BRANCORE} **Moderador:** {interaction.user.mention}\n"
        f"{E.LOADING} **Expira:** {discord.utils.format_dt(until, 'R')}",
    )
    await interaction.followup.send(embed=embed)
    await bot.log_action(
        title=f"{E.ARROW_YELLOW} Mute",
        description=f"{membro} silenciado por {interaction.user} por {minutos} minuto(s).",
    )

# ==================================================
# ------------------ UNMUTE -----------------------
# ==================================================

@bot.tree.command(name="unmute", description="Remover timeout de um membro")
@app_commands.default_permissions(moderate_members=True)
@app_commands.checks.has_permissions(moderate_members=True)
@app_commands.describe(membro="Membro para remover o timeout")
async def unmute(interaction: discord.Interaction, membro: discord.Member):
    await interaction.response.defer()
    if not membro.timed_out_until:
        return await interaction.followup.send(
            embed=error_embed("Erro", f"{membro.mention} não está em timeout."), ephemeral=True
        )
    await membro.timeout(None, reason=f"Unmute por {interaction.user}")
    embed = mod_embed(
        f"{E.ARROW_GREEN} Timeout Removido",
        f"{E.STAFF} **Usuário:** {membro.mention}\n"
        f"{E.BRANCORE} **Moderador:** {interaction.user.mention}",
    )
    await interaction.followup.send(embed=embed)
    await bot.log_action(
        title=f"{E.ARROW_GREEN} Unmute",
        description=f"Timeout de {membro} removido por {interaction.user}.",
    )

# ==================================================
# ------------------ CLEAR ------------------------
# ==================================================

@bot.tree.command(name="clear", description="Apagar mensagens do canal")
@app_commands.default_permissions(manage_messages=True)
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.describe(quantidade="Número de mensagens a apagar (1–100)")
async def clear(interaction: discord.Interaction, quantidade: app_commands.Range[int, 1, 100]):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=quantidade)
    await interaction.followup.send(
        embed=success_embed(
            "Mensagens apagadas",
            f"{E.ARROW_BLUE} `{len(deleted)}` mensagem(ns) apagada(s) em {interaction.channel.mention}.",
        ),
        ephemeral=True,
    )
    await bot.log_action(
        title=f"{E.WARN_IC} Clear",
        description=f"{interaction.user} apagou `{len(deleted)}` mensagem(ns) em {interaction.channel.mention}.",
    )

# ==================================================
# -------------- COMMAND: /warn -------------------
# ==================================================

# Aviso em memória (reseta ao reiniciar; para persistência use um banco de dados)
_warns: dict[int, list[str]] = {}

@bot.tree.command(name="warn", description="Avisar um membro")
@app_commands.default_permissions(moderate_members=True)
@app_commands.checks.has_permissions(moderate_members=True)
@app_commands.describe(membro="Membro a ser avisado", motivo="Motivo do aviso")
async def warn(interaction: discord.Interaction, membro: discord.Member, motivo: str):
    _warns.setdefault(membro.id, []).append(motivo)
    total = len(_warns[membro.id])
    embed = mod_embed(
        f"{E.WARN_IC} Aviso Aplicado",
        f"{E.STAFF} **Usuário:** {membro.mention}\n"
        f"{E.PIN} **Motivo:** {motivo}\n"
        f"{E.BRANCORE} **Moderador:** {interaction.user.mention}\n"
        f"{E.STAR} **Total de avisos:** `{total}`",
    )
    await interaction.response.send_message(embed=embed)
    try:
        await membro.send(
            f"{E.WARN_IC} Você recebeu um aviso no servidor **{interaction.guild.name}**.\n"
            f"**Motivo:** {motivo}\n**Total de avisos:** {total}"
        )
    except (discord.Forbidden, discord.HTTPException):
        pass
    await bot.log_action(
        title=f"{E.WARN_IC} Warn",
        description=f"{membro} avisado por {interaction.user}.",
        fields=[("Motivo", motivo, False), ("Total de avisos", str(total), True)],
    )

@bot.tree.command(name="warns", description="Ver os avisos de um membro")
@app_commands.default_permissions(moderate_members=True)
@app_commands.checks.has_permissions(moderate_members=True)
@app_commands.describe(membro="Membro a consultar")
async def warns(interaction: discord.Interaction, membro: discord.Member):
    lista = _warns.get(membro.id, [])
    if not lista:
        return await interaction.response.send_message(
            embed=success_embed("Sem avisos", f"{membro.mention} não tem nenhum aviso registrado."),
            ephemeral=True,
        )
    desc = "\n".join(f"{E.ARROW_BLUE} `{i+1}.` {w}" for i, w in enumerate(lista))
    embed = discord.Embed(
        title=f"{E.WARN_IC} Avisos de {membro.display_name}",
        description=desc,
        color=Colors.MAIN,
    )
    embed.set_thumbnail(url=membro.display_avatar.url)
    embed.set_footer(text=f"Total: {len(lista)} aviso(s)")
    embed.timestamp = discord.utils.utcnow()
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="clearwarns", description="Limpar todos os avisos de um membro")
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(membro="Membro cujos avisos serão removidos")
async def clearwarns(interaction: discord.Interaction, membro: discord.Member):
    _warns.pop(membro.id, None)
    await interaction.response.send_message(
        embed=success_embed(
            "Avisos removidos",
            f"{E.ARROW_GREEN} Todos os avisos de {membro.mention} foram removidos.",
        ),
        ephemeral=True,
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
        f"{E.SEARCH} Stanford Encyclopedia": (f"https://plato.stanford.edu/search/searcher.py?query={normal}", "SEP"),
        f"{E.ARROW_BLUE} Google Scholar":     (f"https://scholar.google.com/scholar?q={encoded}", "Academic paper"),
        f"{E.ARROW_BLUE} PhilPapers":         (f"https://philpapers.org/s/{normal}", "PhilPapers"),
        f"{E.ARROW_BLUE} Springer":           (f"https://link.springer.com/search?query={normal}", "Journal article"),
        f"{E.ARROW_BLUE} Anna's Archive":     (f"https://annas-archive.org/search?q={normal}", "Book sources"),
        f"{E.ARROW_BLUE} Internet Archive":   (f"https://archive.org/search?query={normal}", "Digital archive"),
    }
    embed = discord.Embed(
        title=f"{E.VERIFY} Recursos Acadêmicos",
        description=f"{E.ARROW_BLUE} **Busca:** {termo}",
        color=Colors.MAIN,
    )
    for field_name, (url, label) in links.items():
        embed.add_field(name=field_name, value=f"[{titulo} — {label}]({url})", inline=False)
    embed.set_footer(text=f"Solicitado por {interaction.user.display_name}")
    embed.timestamp = discord.utils.utcnow()
    await interaction.followup.send(embed=embed)

# ==================================================
# ---------------- STATUS ROTATIVO ----------------
# ==================================================

_STATUS_LIST = [
    ("Aprendendo matemática 🩵", discord.ActivityType.watching),
    ("Olimpíadas ⚡",            discord.ActivityType.watching),
    ("OBMEP 🏆",                 discord.ActivityType.watching),
    ("Filosofia 🏮",             discord.ActivityType.watching),
]

_cycle_status = itertools.cycle(_STATUS_LIST)


@tasks.loop(seconds=30)
async def rotate_status():
    name, activity_type = next(_cycle_status)
    await bot.change_presence(
        activity=discord.Activity(type=activity_type, name=name)
    )


@rotate_status.before_loop
async def before_rotate():
    await bot.wait_until_ready()

# ==================================================
# ------------------- ENTRY -----------------------
# ==================================================

if __name__ == "__main__":
    bot.run(TOKEN)
