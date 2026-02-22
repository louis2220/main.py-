import itertools
import logging
import os
from datetime import timedelta
from urllib.parse import quote_plus

import discord
from discord import app_commands
from discord.ext import tasks
from discord.ui import View, Modal, TextInput, Select

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

        # IDs configuráveis via /setup
        self.log_channel_id:      int | None = None
        self.ticket_category_id:  int | None = None
        self.staff_role_id:       int | None = None
        self.ticket_log_channel_id: int | None = None

        # Controle de tickets abertos: user_id -> channel_id
        self.open_tickets: dict[int, int] = {}

    async def setup_hook(self):
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
            log.warning(
                f"Erro no comando '{interaction.command.name if interaction.command else 'unknown'}': {error}"
            )
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
# =========== SISTEMA DE EMBEDS ===================
# ==================================================

# -------------- MODAL: CRIAR EMBED ---------------

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
                embed=success_embed("Embed enviada!", f"Publicada em {self.canal.mention}."),
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("Sem permissão", f"Não tenho permissão para enviar em {self.canal.mention}."),
                ephemeral=True,
            )
        except discord.HTTPException as exc:
            await interaction.response.send_message(
                embed=error_embed("Erro", f"Falha ao enviar embed: {exc}"),
                ephemeral=True,
            )

# -------------- MODAL: EDITAR EMBED --------------

class EmbedEditModal(Modal, title="Editar Embed"):
    novo_titulo = TextInput(
        label="Novo título (deixe em branco para manter)",
        required=False,
        max_length=256,
    )
    nova_descricao = TextInput(
        label="Nova descrição (deixe em branco para manter)",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=4000,
    )
    nova_cor = TextInput(
        label="Nova cor hex (ex: #590CEA)",
        placeholder="#590CEA",
        required=False,
        max_length=7,
    )
    novo_rodape = TextInput(
        label="Novo rodapé (deixe em branco para manter)",
        required=False,
        max_length=2048,
    )
    nova_imagem = TextInput(
        label="Nova URL de imagem (deixe em branco para manter)",
        required=False,
        max_length=512,
    )

    def __init__(self, message: discord.Message):
        super().__init__()
        self.target_message = message
        # Pré-preencher com valores atuais da embed
        old = message.embeds[0] if message.embeds else None
        if old:
            if old.title:
                self.novo_titulo.default = old.title
            if old.description:
                self.nova_descricao.default = old.description[:4000]
            if old.color:
                self.nova_cor.default = f"#{old.color.value:06X}"
            if old.footer and old.footer.text:
                self.novo_rodape.default = old.footer.text
            if old.image and old.image.url:
                self.nova_imagem.default = old.image.url

    async def on_submit(self, interaction: discord.Interaction):
        old_embed = self.target_message.embeds[0] if self.target_message.embeds else discord.Embed()

        # Cor
        color = old_embed.color.value if old_embed.color else Colors.MAIN
        raw_color = self.nova_cor.value.strip()
        if raw_color:
            try:
                color = int(raw_color.lstrip("#"), 16)
            except ValueError:
                return await interaction.response.send_message(
                    embed=error_embed("Cor inválida", "Use o formato `#RRGGBB`."), ephemeral=True
                )

        new_embed = discord.Embed(
            title=self.novo_titulo.value.strip() or old_embed.title,
            description=self.nova_descricao.value.strip() or old_embed.description,
            color=color,
        )
        new_embed.timestamp = discord.utils.utcnow()

        rodape = self.novo_rodape.value.strip()
        if rodape:
            new_embed.set_footer(text=rodape)
        elif old_embed.footer and old_embed.footer.text:
            new_embed.set_footer(text=old_embed.footer.text)

        imagem = self.nova_imagem.value.strip()
        if imagem:
            new_embed.set_image(url=imagem)
        elif old_embed.image and old_embed.image.url:
            new_embed.set_image(url=old_embed.image.url)

        try:
            await self.target_message.edit(embed=new_embed)
            await interaction.response.send_message(
                embed=success_embed("Embed editada!", "As alterações foram aplicadas com sucesso."),
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("Sem permissão", "Não consigo editar essa mensagem."), ephemeral=True
            )
        except discord.HTTPException as exc:
            await interaction.response.send_message(
                embed=error_embed("Erro", str(exc)), ephemeral=True
            )

# -------------- VIEW DO BUILDER DE EMBED ---------

class EmbedBuilderView(View):
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
            description="*(edite o conteúdo usando /embed-editar)*",
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
            f"{E.ARROW_RED} Criação cancelada.", ephemeral=True
        )

# ==================================================
# =========== SISTEMA DE TICKETS ==================
# ==================================================

# Categorias disponíveis para tickets
TICKET_CATEGORIES = [
    discord.SelectOption(
        label="Denúncias",
        value="denuncia",
        description="Denunciar um membro ou situação",
        emoji="🚨",
    ),
    discord.SelectOption(
        label="Compra de VIP",
        value="vip",
        description="Adquirir um cargo VIP",
        emoji="👑",
    ),
    discord.SelectOption(
        label="Resgate de Prêmio",
        value="premio",
        description="Resgatar um prêmio conquistado",
        emoji="🎁",
    ),
    discord.SelectOption(
        label="Patrocínio",
        value="patrocinio",
        description="Proposta de parceria ou patrocínio",
        emoji="🤝",
    ),
    discord.SelectOption(
        label="Outros",
        value="outros",
        description="Dúvidas gerais ou outros assuntos",
        emoji="💬",
    ),
]

TICKET_EMOJI_MAP = {
    "denuncia":   "🚨",
    "vip":        "👑",
    "premio":     "🎁",
    "patrocinio": "🤝",
    "outros":     "💬",
}

TICKET_LABEL_MAP = {
    "denuncia":   "Denúncias",
    "vip":        "Compra de VIP",
    "premio":     "Resgate de Prêmio",
    "patrocinio": "Patrocínio",
    "outros":     "Outros",
}

# -------------- SELECT DE CATEGORIA --------------

class TicketCategorySelect(Select):
    def __init__(self):
        super().__init__(
            placeholder="Selecione o motivo do seu ticket...",
            options=TICKET_CATEGORIES,
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction):
        categoria = self.values[0]
        # Verifica se já tem ticket aberto
        if interaction.user.id in bot.open_tickets:
            canal_existente = interaction.guild.get_channel(bot.open_tickets[interaction.user.id])
            if canal_existente:
                return await interaction.response.send_message(
                    embed=error_embed(
                        "Ticket já aberto",
                        f"{E.ARROW_BLUE} Você já tem um ticket aberto: {canal_existente.mention}\n"
                        f"Feche-o antes de abrir outro.",
                    ),
                    ephemeral=True,
                )
            else:
                # Canal foi deletado manualmente, limpar registro
                del bot.open_tickets[interaction.user.id]

        # Verificar configuração
        if not bot.ticket_category_id:
            return await interaction.response.send_message(
                embed=error_embed(
                    "Não configurado",
                    f"{E.SETTINGS} O sistema de tickets não está configurado.\n"
                    f"Um administrador precisa usar `/setup-tickets`.",
                ),
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        category = guild.get_channel(bot.ticket_category_id)
        staff_role = guild.get_role(bot.staff_role_id) if bot.staff_role_id else None

        emoji = TICKET_EMOJI_MAP.get(categoria, "💬")
        label = TICKET_LABEL_MAP.get(categoria, "Ticket")

        # Nome do canal: ticket-usuario
        nome_canal = f"ticket-{interaction.user.name}".lower().replace(" ", "-")[:50]

        # Permissões do canal
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                manage_messages=True,
                read_message_history=True,
            ),
        }
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True,
            )

        try:
            ticket_channel = await guild.create_text_channel(
                name=nome_canal,
                category=category if isinstance(category, discord.CategoryChannel) else None,
                overwrites=overwrites,
                reason=f"Ticket aberto por {interaction.user} — {label}",
            )
        except discord.Forbidden:
            return await interaction.followup.send(
                embed=error_embed("Sem permissão", "Não consigo criar canais. Verifique as permissões do bot."),
                ephemeral=True,
            )
        except discord.HTTPException as exc:
            return await interaction.followup.send(
                embed=error_embed("Erro", f"Falha ao criar canal: {exc}"), ephemeral=True
            )

        # Registrar ticket
        bot.open_tickets[interaction.user.id] = ticket_channel.id

        # Embed de boas-vindas no canal do ticket
        welcome_embed = discord.Embed(
            title=f"{emoji} {label}",
            description=(
                f"{E.STAFF} **Aberto por:** {interaction.user.mention}\n"
                f"{E.PIN} **Categoria:** {label}\n\n"
                f"{E.ARROW_BLUE} Olá, {interaction.user.mention}! Descreva seu caso com o máximo de detalhes possível.\n"
                f"{E.LOADING} Nossa equipe irá te atender em breve."
            ),
            color=Colors.MAIN,
        )
        welcome_embed.set_thumbnail(url=interaction.user.display_avatar.url)
        welcome_embed.set_footer(text=f"ID do usuário: {interaction.user.id}")
        welcome_embed.timestamp = discord.utils.utcnow()

        # View com botão de fechar
        close_view = TicketCloseView(opener_id=interaction.user.id)

        # Ping da staff
        staff_ping = staff_role.mention if staff_role else ""
        await ticket_channel.send(
            content=f"{interaction.user.mention} {staff_ping}".strip(),
            embed=welcome_embed,
            view=close_view,
        )

        # DM de confirmação
        try:
            dm_embed = discord.Embed(
                title=f"{E.VERIFY} Ticket aberto!",
                description=(
                    f"{E.ARROW_BLUE} Seu ticket de **{label}** foi aberto em **{guild.name}**.\n"
                    f"{E.INFO_IC} Acesse: {ticket_channel.mention}\n"
                    f"{E.LOADING} Aguarde o atendimento da staff."
                ),
                color=Colors.MAIN,
            )
            dm_embed.timestamp = discord.utils.utcnow()
            await interaction.user.send(embed=dm_embed)
        except (discord.Forbidden, discord.HTTPException):
            pass

        await interaction.followup.send(
            embed=success_embed(
                "Ticket criado!",
                f"{E.ARROW_BLUE} Seu ticket foi aberto em {ticket_channel.mention}.",
            ),
            ephemeral=True,
        )

        # Log
        await bot.log_action(
            title=f"{emoji} Ticket Aberto",
            description=f"{interaction.user} abriu um ticket de **{label}**.",
            fields=[
                ("Canal", ticket_channel.mention, True),
                ("Categoria", label, True),
                ("Usuário ID", str(interaction.user.id), True),
            ],
        )

        log.info(f"Ticket criado: #{nome_canal} por {interaction.user} ({categoria})")

class TicketSelectView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCategorySelect())

# -------------- VIEW DO CANAL DO TICKET ----------

class TicketCloseView(View):
    def __init__(self, opener_id: int):
        super().__init__(timeout=None)
        self.opener_id = opener_id

    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="ticket_close")
    async def fechar(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Apenas staff ou o próprio dono pode fechar
        is_staff = (
            bot.staff_role_id
            and any(r.id == bot.staff_role_id for r in interaction.user.roles)
        )
        is_owner = interaction.user.id == self.opener_id
        is_admin = interaction.user.guild_permissions.administrator

        if not (is_staff or is_owner or is_admin):
            return await interaction.response.send_message(
                embed=error_embed("Sem permissão", "Apenas a staff ou quem abriu o ticket pode fechá-lo."),
                ephemeral=True,
            )

        await interaction.response.send_message(
            embed=mod_embed(
                f"{E.ARROW_YELLOW} Fechando ticket...",
                f"{E.LOADING} Este canal será deletado em **5 segundos**.",
            )
        )

        # Remover do registro
        for uid, cid in list(bot.open_tickets.items()):
            if cid == interaction.channel.id:
                del bot.open_tickets[uid]
                break

        # Log antes de deletar
        await bot.log_action(
            title=f"🔒 Ticket Fechado",
            description=f"Ticket `{interaction.channel.name}` fechado por {interaction.user.mention}.",
            fields=[("Canal", interaction.channel.name, True)],
        )

        import asyncio
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason=f"Ticket fechado por {interaction.user}")
        except discord.HTTPException:
            pass

# -------------- COMMAND: /ticket-setup -----------

@bot.tree.command(name="setup-tickets", description="Configura o sistema de tickets do servidor")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    categoria="Categoria onde os canais de ticket serão criados",
    cargo_staff="Cargo da staff que terá acesso aos tickets",
    canal_log="Canal para logs de tickets (opcional)",
)
async def setup_tickets(
    interaction: discord.Interaction,
    categoria: discord.CategoryChannel,
    cargo_staff: discord.Role,
    canal_log: discord.TextChannel | None = None,
):
    bot.ticket_category_id = categoria.id
    bot.staff_role_id = cargo_staff.id
    if canal_log:
        bot.ticket_log_channel_id = canal_log.id
        bot.log_channel_id = canal_log.id

    embed = success_embed(
        "Tickets configurados!",
        f"{E.ARROW_BLUE} **Categoria:** {categoria.name}\n"
        f"{E.STAFF} **Cargo staff:** {cargo_staff.mention}\n"
        f"{E.INFO_IC} **Log:** {canal_log.mention if canal_log else 'Não definido'}\n\n"
        f"{E.ARROW_GREEN} Use `/ticket-painel` para enviar o painel de tickets em um canal.",
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)
    log.info(f"Tickets configurados: categoria={categoria.id}, staff={cargo_staff.id}")

# -------------- COMMAND: /ticket-painel ----------

@bot.tree.command(name="ticket-painel", description="Envia o painel de abertura de tickets em um canal")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    canal="Canal onde o painel será enviado",
    titulo="Título do painel (opcional)",
    descricao="Descrição do painel (opcional)",
    imagem_url="URL de imagem/banner para o painel (opcional)",
)
async def ticket_painel(
    interaction: discord.Interaction,
    canal: discord.TextChannel,
    titulo: str = "Suporte | Ticket",
    descricao: str = "Abra um ticket escolhendo a opção que mais se encaixa no seu caso.",
    imagem_url: str | None = None,
):
    embed = discord.Embed(
        title=f"{E.INFO_IC} {titulo}",
        description=(
            f"{E.ARROW_BLUE} {descricao}\n\n"
            f"{E.FIRE} **Categorias disponíveis:**\n"
            f"🚨 Denúncias\n"
            f"👑 Compra de VIP\n"
            f"🎁 Resgate de Prêmio\n"
            f"🤝 Patrocínio\n"
            f"💬 Outros"
        ),
        color=Colors.MAIN,
    )
    embed.set_footer(text=f"{interaction.guild.name} • Suporte")
    embed.timestamp = discord.utils.utcnow()

    if imagem_url:
        embed.set_image(url=imagem_url)

    view = TicketSelectView()
    try:
        await canal.send(embed=embed, view=view)
        await interaction.response.send_message(
            embed=success_embed("Painel enviado!", f"{E.ARROW_BLUE} Painel de tickets publicado em {canal.mention}."),
            ephemeral=True,
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            embed=error_embed("Sem permissão", f"Não consigo enviar em {canal.mention}."), ephemeral=True
        )

# -------------- COMMAND: /fechar-ticket ----------

@bot.tree.command(name="fechar-ticket", description="Fecha e deleta o ticket atual")
@app_commands.default_permissions(manage_channels=True)
async def fechar_ticket(interaction: discord.Interaction):
    # Verifica se o canal atual é um ticket
    is_ticket = any(cid == interaction.channel.id for cid in bot.open_tickets.values())
    if not is_ticket:
        return await interaction.response.send_message(
            embed=error_embed("Erro", "Este canal não é um ticket aberto."), ephemeral=True
        )

    await interaction.response.send_message(
        embed=mod_embed(
            f"{E.ARROW_YELLOW} Fechando ticket...",
            f"{E.LOADING} Este canal será deletado em **5 segundos**.",
        )
    )

    for uid, cid in list(bot.open_tickets.items()):
        if cid == interaction.channel.id:
            del bot.open_tickets[uid]
            break

    await bot.log_action(
        title="🔒 Ticket Fechado",
        description=f"Ticket `{interaction.channel.name}` fechado por {interaction.user.mention}.",
    )

    import asyncio
    await asyncio.sleep(5)
    try:
        await interaction.channel.delete(reason=f"Ticket fechado por {interaction.user}")
    except discord.HTTPException:
        pass

# ==================================================
# =========== SISTEMA DE AUTOMOD ==================
# ==================================================
#
# Cada servidor suporta até 6 regras de keyword +
# regras de spam, menções, links e conteúdo de perfil.
# Rodando /automod-setup em vários servidores, o total
# acumulado pode bater 100 e garantir a badge.
# ==================================================

AUTOMOD_KEYWORDS = [
    # Bloco 1 — Palavrões e ofensas gerais
    ["idiota", "imbecil", "cretino", "babaca", "otário", "fdp", "vsf", "porra", "merda", "caralho"],
    # Bloco 2 — Slurs e discriminação
    ["viado", "bicha", "sapatão", "negro", "macaco", "judeu", "cigano", "nordestino de merda"],
    # Bloco 3 — Ameaças e violência
    ["vou te matar", "te mato", "sua vida não vale", "bomba", "explodir", "atirar em"],
    # Bloco 4 — Spam e autopromoção
    ["discord.gg", "discordapp.com/invite", "bit.ly", "tinyurl", "free nitro", "click here"],
    # Bloco 5 — Conteúdo adulto
    ["porn", "nude", "nudes", "sexo grátis", "pack", "onlyfans", "privacy"],
    # Bloco 6 — Golpes e phishing
    ["ganhe dinheiro", "ganhe robux", "ganhe nitro", "acesse agora", "promoção exclusiva", "clique aqui"],
]

async def create_automod_rules(guild: discord.Guild) -> tuple[int, int]:
    """
    Cria todas as regras de AutoMod possíveis no servidor.
    Retorna (criadas, erros).
    """
    criadas = 0
    erros = 0

    # ── 1. Regras de keyword (máx. 6 por servidor) ──────────────────────────
    for i, keywords in enumerate(AUTOMOD_KEYWORDS):
        try:
            await guild.create_automod_rule(
                name=f"[Bot] Palavras bloqueadas #{i+1}",
                event_type=discord.AutoModRuleEventType.message_send,
                trigger=discord.AutoModTrigger(
                    type=discord.AutoModRuleTriggerType.keyword,
                    keyword_filter=keywords,
                ),
                actions=[
                    discord.AutoModRuleAction(
                        type=discord.AutoModRuleActionType.block_message,
                        custom_message="Sua mensagem foi bloqueada por conter conteúdo proibido.",
                    )
                ],
                enabled=True,
                reason="AutoMod setup automático pelo bot",
            )
            criadas += 1
        except discord.HTTPException:
            erros += 1

    # ── 2. Regra anti-spam (menções excessivas) ──────────────────────────────
    try:
        await guild.create_automod_rule(
            name="[Bot] Anti-Mention Spam",
            event_type=discord.AutoModRuleEventType.message_send,
            trigger=discord.AutoModTrigger(
                type=discord.AutoModRuleTriggerType.mention_spam,
                mention_total_limit=5,
            ),
            actions=[
                discord.AutoModRuleAction(
                    type=discord.AutoModRuleActionType.block_message,
                    custom_message="Muitas menções em uma só mensagem.",
                ),
                discord.AutoModRuleAction(
                    type=discord.AutoModRuleActionType.timeout,
                    duration=timedelta(minutes=10),
                ),
            ],
            enabled=True,
            reason="AutoMod setup automático pelo bot",
        )
        criadas += 1
    except discord.HTTPException:
        erros += 1

    # ── 3. Regra anti-spam de conteúdo ──────────────────────────────────────
    try:
        await guild.create_automod_rule(
            name="[Bot] Anti-Spam de Conteúdo",
            event_type=discord.AutoModRuleEventType.message_send,
            trigger=discord.AutoModTrigger(
                type=discord.AutoModRuleTriggerType.spam,
            ),
            actions=[
                discord.AutoModRuleAction(
                    type=discord.AutoModRuleActionType.block_message,
                    custom_message="Conteúdo identificado como spam.",
                ),
                discord.AutoModRuleAction(
                    type=discord.AutoModRuleActionType.timeout,
                    duration=timedelta(minutes=5),
                ),
            ],
            enabled=True,
            reason="AutoMod setup automático pelo bot",
        )
        criadas += 1
    except discord.HTTPException:
        erros += 1

    # ── 4. Regra de keyword preset (conteúdo sexual/violência) ──────────────
    try:
        await guild.create_automod_rule(
            name="[Bot] Conteúdo Explícito (Preset)",
            event_type=discord.AutoModRuleEventType.message_send,
            trigger=discord.AutoModTrigger(
                type=discord.AutoModRuleTriggerType.keyword_preset,
                presets=discord.AutoModPresets.sexual_content | discord.AutoModPresets.slurs,
            ),
            actions=[
                discord.AutoModRuleAction(
                    type=discord.AutoModRuleActionType.block_message,
                    custom_message="Conteúdo não permitido neste servidor.",
                )
            ],
            enabled=True,
            reason="AutoMod setup automático pelo bot",
        )
        criadas += 1
    except discord.HTTPException:
        erros += 1

    return criadas, erros


@bot.tree.command(name="automod-setup", description="Cria regras de AutoMod automáticas neste servidor")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    canal_log="Canal onde o AutoMod vai registrar as ocorrências (opcional)"
)
async def automod_setup(
    interaction: discord.Interaction,
    canal_log: discord.TextChannel | None = None,
):
    await interaction.response.defer(ephemeral=True)

    guild = interaction.guild

    # Verificar regras existentes para não duplicar
    try:
        existing = await guild.fetch_automod_rules()
        existing_names = {r.name for r in existing}
    except discord.Forbidden:
        return await interaction.followup.send(
            embed=error_embed(
                "Sem permissão",
                "Preciso da permissão **Gerenciar Servidor** para criar regras de AutoMod.",
            ),
            ephemeral=True,
        )

    bot_rules = [n for n in existing_names if n.startswith("[Bot]")]
    if bot_rules:
        return await interaction.followup.send(
            embed=error_embed(
                "Já configurado",
                f"{E.INFO_IC} Este servidor já tem **{len(bot_rules)}** regra(s) criadas pelo bot.\n"
                f"{E.ARROW_BLUE} Use `/automod-status` para ver o total acumulado.",
            ),
            ephemeral=True,
        )

    # Criar as regras
    criadas, erros = await create_automod_rules(guild)

    # Configurar canal de log nas regras existentes se fornecido
    if canal_log:
        try:
            rules = await guild.fetch_automod_rules()
            for rule in rules:
                if rule.name.startswith("[Bot]"):
                    actions_with_log = list(rule.actions) + [
                        discord.AutoModRuleAction(
                            type=discord.AutoModRuleActionType.send_alert_message,
                            channel=canal_log,
                        )
                    ]
                    try:
                        await rule.edit(actions=actions_with_log)
                    except discord.HTTPException:
                        pass
        except discord.HTTPException:
            pass

    embed = discord.Embed(
        title=f"{E.VERIFY} AutoMod Configurado!",
        description=(
            f"{E.ARROW_GREEN} **{criadas}** regra(s) criadas neste servidor.\n"
            + (f"{E.ARROW_RED} **{erros}** regra(s) falharam (limite do servidor atingido).\n" if erros else "")
            + (f"{E.INFO_IC} Logs serão enviados em {canal_log.mention}.\n" if canal_log else "")
            + f"\n{E.STAR} **Regras ativas protegem contra:**\n"
            f"{E.ARROW_BLUE} Palavrões e ofensas\n"
            f"{E.ARROW_BLUE} Slurs e discriminação\n"
            f"{E.ARROW_BLUE} Ameaças e violência\n"
            f"{E.ARROW_BLUE} Spam de links e autopromoção\n"
            f"{E.ARROW_BLUE} Conteúdo adulto\n"
            f"{E.ARROW_BLUE} Golpes e phishing\n"
            f"{E.ARROW_BLUE} Mention spam\n"
            f"{E.ARROW_BLUE} Conteúdo explícito (preset)\n"
            f"\n{E.LOADING} Rode este comando em mais servidores para acumular regras e conquistar a badge!"
        ),
        color=Colors.MAIN,
    )
    embed.set_footer(text=f"Servidor: {guild.name} • {guild.id}")
    embed.timestamp = discord.utils.utcnow()
    await interaction.followup.send(embed=embed, ephemeral=True)

    await bot.log_action(
        title=f"{E.SETTINGS} AutoMod Setup",
        description=f"{interaction.user} configurou o AutoMod em **{guild.name}**.",
        fields=[
            ("Regras criadas", str(criadas), True),
            ("Erros", str(erros), True),
            ("Log", canal_log.mention if canal_log else "Não definido", True),
        ],
    )
    log.info(f"AutoMod setup: {criadas} regras em {guild.name} ({guild.id})")


@bot.tree.command(name="automod-status", description="Mostra quantas regras de AutoMod o bot criou neste servidor")
@app_commands.default_permissions(manage_guild=True)
async def automod_status(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        rules = await interaction.guild.fetch_automod_rules()
    except discord.Forbidden:
        return await interaction.followup.send(
            embed=error_embed("Sem permissão", "Não consigo verificar as regras de AutoMod."), ephemeral=True
        )

    bot_rules = [r for r in rules if r.name.startswith("[Bot]")]
    total = len(rules)
    bot_total = len(bot_rules)

    desc = "\n".join(f"{E.ARROW_BLUE} {r.name}" for r in bot_rules) or f"{E.ARROW_RED} Nenhuma regra encontrada."
    embed = discord.Embed(
        title=f"{E.SETTINGS} Status do AutoMod",
        description=(
            f"{E.INFO_IC} **Regras do bot neste servidor:** `{bot_total}`\n"
            f"{E.STAR} **Total de regras no servidor:** `{total}`\n\n"
            f"{E.ARROW_BLUE} **Regras criadas pelo bot:**\n{desc}\n\n"
            f"{E.LOADING} Para a badge, você precisa de **100 regras** somando todos os servidores.\n"
            f"Adicione o bot em mais servidores e rode `/automod-setup` em cada um!"
        ),
        color=Colors.MAIN,
    )
    embed.set_footer(text=f"Servidor: {interaction.guild.name}")
    embed.timestamp = discord.utils.utcnow()
    await interaction.followup.send(embed=embed, ephemeral=True)

# ==================================================
# =========== SISTEMA DE EMBEDS (COMANDOS) =========
# ==================================================

@bot.tree.command(name="embed", description="Criar e enviar uma embed personalizada em um canal")
@app_commands.default_permissions(manage_messages=True)
@app_commands.describe(canal="Canal onde a embed será enviada")
async def embed_cmd(interaction: discord.Interaction, canal: discord.TextChannel):
    view = EmbedBuilderView(autor=interaction.user, canal=canal)
    preview = discord.Embed(
        title=f"{E.STAR} Construtor de Embeds",
        description=(
            f"Escolha uma opção para enviar uma embed em {canal.mention}.\n\n"
            f"{E.ARROW_BLUE} **Criar Embed** — totalmente customizado via formulário\n"
            f"{E.ARROW_BLUE} **Anunciar** — template de anúncio pronto\n"
            f"{E.ARROW_BLUE} **Regras** — template de regras formatado"
        ),
        color=Colors.MAIN,
    )
    preview.set_footer(text=f"Solicitado por {interaction.user.display_name}")
    preview.timestamp = discord.utils.utcnow()
    await interaction.response.send_message(embed=preview, view=view, ephemeral=True)

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

@bot.tree.command(name="embed-editar", description="Edita uma embed existente pelo ID da mensagem")
@app_commands.default_permissions(manage_messages=True)
@app_commands.describe(
    canal="Canal onde a mensagem está",
    message_id="ID da mensagem com a embed",
)
async def embed_editar(
    interaction: discord.Interaction,
    canal: discord.TextChannel,
    message_id: str,
):
    try:
        mid = int(message_id)
    except ValueError:
        return await interaction.response.send_message(
            embed=error_embed("ID inválido", "O ID da mensagem precisa ser um número."), ephemeral=True
        )

    try:
        message = await canal.fetch_message(mid)
    except discord.NotFound:
        return await interaction.response.send_message(
            embed=error_embed("Mensagem não encontrada", f"Não encontrei a mensagem `{mid}` em {canal.mention}."),
            ephemeral=True,
        )
    except discord.Forbidden:
        return await interaction.response.send_message(
            embed=error_embed("Sem permissão", f"Não consigo acessar mensagens em {canal.mention}."), ephemeral=True
        )

    # Verificar se a mensagem é do bot e tem embed
    if message.author.id != bot.user.id:
        return await interaction.response.send_message(
            embed=error_embed("Erro", "Só consigo editar embeds enviadas por mim."), ephemeral=True
        )
    if not message.embeds:
        return await interaction.response.send_message(
            embed=error_embed("Sem embed", "Essa mensagem não contém nenhuma embed."), ephemeral=True
        )

    await interaction.response.send_modal(EmbedEditModal(message))

# ==================================================
# ============= COMANDOS PÚBLICOS =================
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

@bot.tree.command(name="userinfo", description="Exibe informações sobre um membro")
@app_commands.describe(membro="Membro a consultar (padrão: você mesmo)")
async def userinfo(interaction: discord.Interaction, membro: discord.Member | None = None):
    membro = membro or interaction.user
    roles = [r.mention for r in reversed(membro.roles) if r.name != "@everyone"]
    embed = discord.Embed(title=f"{E.STAFF} {membro.display_name}", color=Colors.MAIN)
    embed.set_thumbnail(url=membro.display_avatar.url)
    embed.add_field(name=f"{E.WHITE_IC} Tag",   value=str(membro), inline=True)
    embed.add_field(name=f"{E.INFO_IC} ID",     value=f"`{membro.id}`", inline=True)
    embed.add_field(name=f"{E.VERIFY} Bot?",    value="Sim" if membro.bot else "Não", inline=True)
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

@bot.tree.command(name="serverinfo", description="Exibe informações sobre o servidor")
async def serverinfo(interaction: discord.Interaction):
    g = interaction.guild
    embed = discord.Embed(title=f"{E.DISCORD} {g.name}", color=Colors.MAIN)
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

@bot.tree.command(name="avatar", description="Exibe o avatar de um membro em alta resolução")
@app_commands.describe(membro="Membro cujo avatar exibir")
async def avatar(interaction: discord.Interaction, membro: discord.Member | None = None):
    membro = membro or interaction.user
    embed = discord.Embed(title=f"{E.STAR} Avatar de {membro.display_name}", color=Colors.MAIN)
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
# ============= SETUP (ADMIN) =====================
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
# ============= MODERAÇÃO =========================
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
    except discord.HTTPException as exc:
        await interaction.followup.send(embed=error_embed("Erro", str(exc)), ephemeral=True)

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
# ============= SISTEMA DE WARNS ==================
# ==================================================

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
# ============= FILOSOFIA / PESQUISA ==============
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
# ============= STATUS ROTATIVO ===================
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
# =================== ENTRY =======================
# ==================================================

if __name__ == "__main__":
    bot.run(TOKEN)
