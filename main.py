import asyncio
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
    PRIMARY   = 0x5865F2  # Blurple Discord
    SUCCESS   = 0x57F287  # Verde
    WARNING   = 0xFEE75C  # Amarelo
    ERROR     = 0xED4245  # Vermelho
    INFO      = 0xEB459E  # Rosa
    DARK      = 0x2B2D31  # Fundo escuro Discord
    ORANGE    = 0xE67E22
    TEAL      = 0x1ABC9C

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
        # Primeira propagação pode levar até 1h pelo cache do Discord
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
            msg = "❌ Você não tem permissão para usar este comando."
        elif isinstance(error, app_commands.BotMissingPermissions):
            msg = "❌ Eu não tenho permissões suficientes para executar isso."
        elif isinstance(error, app_commands.CommandOnCooldown):
            msg = f"⏳ Aguarde {error.retry_after:.1f}s antes de usar este comando novamente."
        else:
            msg = "❌ Ocorreu um erro ao executar esse comando."
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
        color: int = Colors.WARNING,
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
    e = discord.Embed(title=f"✅ {title}", description=description, color=Colors.SUCCESS)
    e.timestamp = discord.utils.utcnow()
    return e

def error_embed(title: str, description: str) -> discord.Embed:
    e = discord.Embed(title=f"❌ {title}", description=description, color=Colors.ERROR)
    e.timestamp = discord.utils.utcnow()
    return e

def mod_embed(title: str, description: str, color: int) -> discord.Embed:
    e = discord.Embed(title=title, description=description, color=color)
    e.timestamp = discord.utils.utcnow()
    return e

# ==================================================
# -------------- MODAL DE EMBED -------------------
# ==================================================

class EmbedModal(Modal, title="✨ Criar Embed"):
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
        label="Cor (hex, ex: #5865F2)",
        placeholder="#5865F2",
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
        # Processar cor
        color = Colors.PRIMARY
        raw_color = self.cor.value.strip()
        if raw_color:
            try:
                color = int(raw_color.lstrip("#"), 16)
            except ValueError:
                await interaction.response.send_message(
                    embed=error_embed("Cor inválida", "Use o formato `#RRGGBB`, ex: `#5865F2`."),
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
                embed=success_embed("Embed enviado!", f"Sua embed foi publicada em {self.canal.mention}."),
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
# ------------ EMBED COM CAMPO EXTRA --------------
# ==================================================

class EmbedFieldModal(Modal, title="➕ Adicionar Campo"):
    campo_nome = TextInput(label="Nome do campo", max_length=256, required=True)
    campo_valor = TextInput(
        label="Valor do campo",
        style=discord.TextStyle.paragraph,
        max_length=1024,
        required=True,
    )
    inline = TextInput(
        label="Inline? (sim/não)",
        placeholder="sim",
        max_length=3,
        required=False,
    )

    def __init__(self, embed: discord.Embed, canal: discord.TextChannel):
        super().__init__()
        self.embed_data = embed
        self.canal = canal

    async def on_submit(self, interaction: discord.Interaction):
        is_inline = self.inline.value.strip().lower() in ("sim", "s", "yes", "y", "1")
        self.embed_data.add_field(
            name=self.campo_nome.value,
            value=self.campo_valor.value,
            inline=is_inline,
        )
        await self.canal.send(embed=self.embed_data)
        await interaction.response.send_message(
            embed=success_embed("Embed com campo enviado!", f"Publicado em {self.canal.mention}."),
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
        self.embed_atual: discord.Embed | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.autor.id:
            await interaction.response.send_message("❌ Apenas quem iniciou pode usar esses botões.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="✏️ Criar Embed", style=discord.ButtonStyle.primary)
    async def criar(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = EmbedModal(self.canal)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="📢 Anunciar", style=discord.ButtonStyle.success)
    async def anunciar(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📢 Anúncio",
            description="*(edite o conteúdo acima depois de enviar usando o botão Criar Embed)*",
            color=Colors.INFO,
        )
        embed.timestamp = discord.utils.utcnow()
        await self.canal.send(embed=embed)
        await interaction.response.send_message(
            embed=success_embed("Anúncio enviado!", f"Publicado em {self.canal.mention}."),
            ephemeral=True,
        )

    @discord.ui.button(label="📌 Regras", style=discord.ButtonStyle.secondary)
    async def regras(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📌 Regras do Servidor",
            description=(
                "Bem-vindo! Por favor, leia e respeite as regras abaixo.\n\n"
                "**1.** Respeite todos os membros.\n"
                "**2.** Sem spam ou flood.\n"
                "**3.** Sem conteúdo NSFW fora dos canais permitidos.\n"
                "**4.** Siga os Termos de Serviço do Discord.\n"
                "**5.** Decisões da staff são finais."
            ),
            color=Colors.PRIMARY,
        )
        embed.set_footer(text="Ao participar, você concorda com essas regras.")
        embed.timestamp = discord.utils.utcnow()
        await self.canal.send(embed=embed)
        await interaction.response.send_message(
            embed=success_embed("Regras enviadas!", f"Publicado em {self.canal.mention}."),
            ephemeral=True,
        )

    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.danger)
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        await interaction.response.send_message("❌ Criação de embed cancelada.", ephemeral=True)

# ==================================================
# ------------ COMMAND: /embed --------------------
# ==================================================

@bot.tree.command(name="embed", description="Criar e enviar uma embed personalizada em um canal")
@app_commands.default_permissions(manage_messages=True)
@app_commands.describe(canal="Canal onde a embed será enviada")
async def embed_cmd(interaction: discord.Interaction, canal: discord.TextChannel):
    view = EmbedBuilderView(autor=interaction.user, canal=canal)
    preview = discord.Embed(
        title="✨ Construtor de Embeds",
        description=(
            f"Escolha uma opção abaixo para enviar uma embed em {canal.mention}.\n\n"
            "**✏️ Criar Embed** — cria um embed totalmente customizado via formulário\n"
            "**📢 Anunciar** — envia um template de anúncio\n"
            "**📌 Regras** — envia um template de regras"
        ),
        color=Colors.PRIMARY,
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
    cor="Cor em hex (ex: #5865F2) — padrão: azul Discord",
)
async def embed_rapido(
    interaction: discord.Interaction,
    canal: discord.TextChannel,
    titulo: str,
    descricao: str,
    cor: str = "#5865F2",
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
        title="🏓 Pong!",
        description=f"Latência da API: `{latency}ms`",
        color=Colors.SUCCESS if latency < 150 else Colors.WARNING,
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
        title=f"👤 {membro.display_name}",
        color=membro.color if membro.color.value else Colors.PRIMARY,
    )
    embed.set_thumbnail(url=membro.display_avatar.url)
    embed.add_field(name="Tag", value=str(membro), inline=True)
    embed.add_field(name="ID", value=f"`{membro.id}`", inline=True)
    embed.add_field(name="Bot?", value="✅ Sim" if membro.bot else "❌ Não", inline=True)
    embed.add_field(
        name="Entrou no servidor",
        value=discord.utils.format_dt(membro.joined_at, "R") if membro.joined_at else "Desconhecido",
        inline=True,
    )
    embed.add_field(
        name="Conta criada",
        value=discord.utils.format_dt(membro.created_at, "R"),
        inline=True,
    )
    embed.add_field(
        name=f"Cargos ({len(roles)})",
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
        title=f"🏠 {g.name}",
        color=Colors.PRIMARY,
    )
    if g.icon:
        embed.set_thumbnail(url=g.icon.url)
    embed.add_field(name="ID", value=f"`{g.id}`", inline=True)
    embed.add_field(name="Dono", value=f"<@{g.owner_id}>", inline=True)
    embed.add_field(name="Região", value=str(g.preferred_locale), inline=True)
    embed.add_field(name="Membros", value=f"`{g.member_count}`", inline=True)
    embed.add_field(name="Canais", value=f"`{len(g.channels)}`", inline=True)
    embed.add_field(name="Cargos", value=f"`{len(g.roles)}`", inline=True)
    embed.add_field(name="Emojis", value=f"`{len(g.emojis)}`", inline=True)
    embed.add_field(
        name="Boosts",
        value=f"`{g.premium_subscription_count}` (Nível {g.premium_tier})",
        inline=True,
    )
    embed.add_field(
        name="Criado em",
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
        title=f"🖼️ Avatar de {membro.display_name}",
        color=Colors.PRIMARY,
    )
    embed.set_image(url=membro.display_avatar.with_size(1024).url)
    embed.add_field(name="Links", value=(
        f"[PNG]({membro.display_avatar.with_format('png').url}) • "
        f"[JPG]({membro.display_avatar.with_format('jpg').url}) • "
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
        embed=success_embed("Configuração salva", f"Canal de logs definido para {canal.mention}."),
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
        return await interaction.response.send_message(embed=error_embed("Erro", "Você não pode se banir."), ephemeral=True)
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
        "🔨 Membro Banido",
        f"**Usuário:** {membro.mention} (`{membro}`)\n**Motivo:** {motivo}\n**Moderador:** {interaction.user.mention}",
        Colors.ERROR,
    )
    await interaction.followup.send(embed=embed)
    await bot.log_action(
        title="🔨 Ban",
        description=f"{membro} banido por {interaction.user}.",
        color=Colors.ERROR,
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
        return await interaction.followup.send(embed=error_embed("ID inválido", "O ID precisa ser um número."), ephemeral=True)
    try:
        user = await bot.fetch_user(uid)
        await interaction.guild.unban(user, reason=f"{interaction.user} — {motivo}")
        await interaction.followup.send(
            embed=success_embed("Usuário desbanido", f"{user} (`{uid}`) foi desbanido.\nMotivo: {motivo}"),
            ephemeral=True,
        )
        await bot.log_action(
            title="✅ Unban",
            description=f"{user} desbanido por {interaction.user}.",
            color=Colors.SUCCESS,
            fields=[("Motivo", motivo, False)],
        )
    except discord.NotFound:
        await interaction.followup.send(embed=error_embed("Não encontrado", "Usuário não encontrado ou não está banido."), ephemeral=True)
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
        return await interaction.response.send_message(embed=error_embed("Erro", "Você não pode se expulsar."), ephemeral=True)
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
        "👢 Membro Expulso",
        f"**Usuário:** {membro.mention} (`{membro}`)\n**Motivo:** {motivo}\n**Moderador:** {interaction.user.mention}",
        Colors.ORANGE,
    )
    await interaction.followup.send(embed=embed)
    await bot.log_action(
        title="👢 Kick",
        description=f"{membro} expulso por {interaction.user}.",
        color=Colors.ORANGE,
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
        "🔇 Membro Silenciado",
        f"**Usuário:** {membro.mention}\n**Duração:** {minutos} minuto(s)\n**Moderador:** {interaction.user.mention}\n**Expira:** {discord.utils.format_dt(until, 'R')}",
        Colors.WARNING,
    )
    await interaction.followup.send(embed=embed)
    await bot.log_action(
        title="🔇 Mute",
        description=f"{membro} silenciado por {interaction.user} por {minutos} minuto(s).",
        color=Colors.WARNING,
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
        "🔊 Timeout Removido",
        f"**Usuário:** {membro.mention}\n**Moderador:** {interaction.user.mention}",
        Colors.SUCCESS,
    )
    await interaction.followup.send(embed=embed)
    await bot.log_action(
        title="🔊 Unmute",
        description=f"Timeout de {membro} removido por {interaction.user}.",
        color=Colors.SUCCESS,
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
        embed=success_embed("Mensagens apagadas", f"{len(deleted)} mensagem(ns) apagada(s) em {interaction.channel.mention}."),
        ephemeral=True,
    )
    await bot.log_action(
        title="🗑️ Clear",
        description=f"{interaction.user} apagou {len(deleted)} mensagem(ns) em {interaction.channel.mention}.",
        color=Colors.PRIMARY,
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
        "⚠️ Aviso Aplicado",
        f"**Usuário:** {membro.mention}\n**Motivo:** {motivo}\n**Moderador:** {interaction.user.mention}\n**Total de avisos:** `{total}`",
        Colors.WARNING,
    )
    await interaction.response.send_message(embed=embed)
    try:
        await membro.send(
            f"⚠️ Você recebeu um aviso no servidor **{interaction.guild.name}**.\n"
            f"**Motivo:** {motivo}\n**Total de avisos:** {total}"
        )
    except (discord.Forbidden, discord.HTTPException):
        pass
    await bot.log_action(
        title="⚠️ Warn",
        description=f"{membro} avisado por {interaction.user}.",
        color=Colors.WARNING,
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
            embed=success_embed("Sem avisos", f"{membro.mention} não tem nenhum aviso."), ephemeral=True
        )
    desc = "\n".join(f"`{i+1}.` {w}" for i, w in enumerate(lista))
    embed = discord.Embed(
        title=f"⚠️ Avisos de {membro.display_name}",
        description=desc,
        color=Colors.WARNING,
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
        embed=success_embed("Avisos removidos", f"Todos os avisos de {membro.mention} foram removidos."),
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
        color=Colors.DARK,
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
