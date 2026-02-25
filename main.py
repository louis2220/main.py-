import asyncio
import itertools
import logging
import os
from datetime import timedelta

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
    MAIN = 0x590CEA

# ==================================================
# ------------------- EMOJIS ----------------------
# ==================================================

class E:
    # Mapeamento pela ordem visual das imagens enviadas
    # Foto 1 (de cima pra baixo) + Foto 2 (continuação)
    HEART      = "<a:1000006091:1475984862140825833>"   # coração roxo animado
    STAR       = "<a:1000006093:1475982082709655714>"   # estrela roxa animada
    LOADING    = "<a:1000006103:1475984937835565227>"   # loading/pontinhos animado
    DECO_BOX   = "<a:1000006120:1475985083818053642>"   # ícone decorativo animado
    ENVELOPE   = "<a:1000006121:1475984619638620221>"   # envelope/carta animado
    MASCOT     = "<:1000006124:1475984717751783617>"    # mascote/raposa estático
    SYMBOL     = "<:1000006128:1475984311030251722>"    # símbolo circular ⊕
    LEAF       = "<:1000006129:1475984352696471623>"    # folha/planta dourada
    SNOWFLAKE  = "<:1000006130:1475984405339045981>"    # floco de neve
    DIAMOND    = "<:1000006131:1475984449656324311>"    # losango/diamante
    FLAME_ORG  = "<:1000006132:1475984492161273967>"    # chama laranja/vermelha
    SPIRAL     = "<:1000006133:1475984534192394354>"    # espiral verde
    FLAME_PUR  = "<:1000006134:1475984576819237080>"    # chama roxa
    DECO_PINK  = "<a:1000006138:1475984121653235866>"   # bloco/item rosa animado
    CROWN_PINK = "<a:1000006139:1475984068251226245>"   # coroa rosa animada
    CHIBI      = "<:1000006140:1475984183246585979>"    # personagem chibi estático
    RING       = "<a:1000006151:1475983991352852714>"   # anel/círculo animado
    ORB_GREEN  = "<a:1000006152:1475983799568433355>"   # orbe verde animado
    ORB_DARK   = "<a:1000006157:1475983848838795528>"   # orbe escuro animado
    TROPHY     = "<a:1000006179:1475983063581331569>"   # troféu animado
    ALERT      = "<:1000006181:1475983204577054880>"    # alerta/aviso ⚠️
    PEN        = "<:1000006182:1475983151712174290>"    # caneta/lápis
    CALENDAR   = "<:1000006183:1475983251414847704>"    # calendário
    LINK       = "<:1000006184:1475983337645674528>"    # corrente/link
    BULB       = "<a:1000006186:1475983407287631984>"   # lâmpada animada
    GEM        = "<a:1000006188:1475983501487771819>"   # diamante azul animado
    HAT        = "<a:1000006193:1475982817195331787>"   # chapéu animado
    DISCORD    = "<a:1000006197:1475982907612070000>"   # ícone Discord animado
    GEM_SHINE  = "<a:1000006229:1475982680012230787>"   # diamante brilhante animado
    N1         = "<:1000006244:1475982552488607815>"    # número 1
    N2         = "<:1000006242:1475982573846139001>"    # número 2
    N3         = "<:1000006239:1475982464928452678>"    # número 3
    N4         = "<:1000006240:1475982529243643967>"    # número 4
    N5         = "<:1000006247:1475982600463187990>"    # número 5
    N6         = "<:1000006236:1475982635384836126>"    # número 6
    LINE1      = "<:Z24_WG:1451041436077391943>"        # separador/linha 1
    LINE2      = "<:AZ_8white:1444502142898540545>"     # separador/linha 2
    RULES      = "<:regras:1444711583669551358>"        # caderno checklist (regras)
    PIN        = "<:w_p:1445474432893063299>"           # alfinete/pin
    ANNOUNCE   = "<:branxo:1445594793508864211>"        # megafone (anúncio)
    CHAT       = "<:util_chat:1448790192033890429>"     # balão de chat
    HEARTS_S   = "<a:1503hearts:1430339028720549908>"   # corações animados pequenos
    SPARKLE    = "<a:1812purple:1430339025520164974>"   # estrelinhas/faíscas animadas
    VERIFY     = "<a:8111discordverifypurple:1430269168908894369>"  # verificado roxo
    ARROW      = "<a:73288animatedarrowpurple:1430339013276991528>" # seta roxa animada »
    ARROW_W    = "<a:51047animatedarrowwhite:1430338988765347850>"  # seta branca animada »
    FIRE       = "<a:5997purplefire:1430338774835003513>"           # chama roxa animada
    WARN_IC    = "<a:i_exclamation:1446591025622679644>"            # exclamação de aviso
    # ── Aliases usados no resto do código ─────────
    INFO_IC    = SYMBOL      # ⊕ usado como info
    SETTINGS   = SNOWFLAKE   # floco usado como settings/config
    STAFF      = CALENDAR    # calendário usado para "aberto por"
    BRANCORE   = ANNOUNCE
    BRANXO     = ANNOUNCE
    ARROW_BLUE   = ARROW
    ARROW_GREEN  = ARROW_W
    ARROW_RED    = WARN_IC
    ARROW_ORANGE = ARROW
    ARROW_YELLOW = ARROW_W
    DIAMOND      = GEM        # diamante azul usado para "Motivo" no ticket

# ==================================================
# ------------------- BOT -------------------------
# ==================================================

class ModBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.log_channel_id:        int | None = None
        self.ticket_category_id:    int | None = None
        self.staff_role_id:         int | None = None
        self.ticket_log_channel_id: int | None = None
        self.open_tickets: dict[int, int] = {}
        self.ticket_banner_url:     str | None = None
        self.ticket_atendentes: dict[int, int] = {}

    async def setup_hook(self):
        # ─────────────────────────────────────────────────────────────────
        # CORREÇÃO DE SYNC GLOBAL
        # O sync() sem guild envia os comandos para a API do Discord de
        # forma global. Pode levar até 1h na primeira vez, mas depois é
        # quase instantâneo. Nunca use guild= fixo no sync para produção,
        # pois aí os comandos ficam presos naquele servidor.
        # ─────────────────────────────────────────────────────────────────
        synced = await self.tree.sync()
        log.info(f"Slash commands sincronizados globalmente: {len(synced)} comando(s).")

    async def on_ready(self):
        log.info(f"Bot online como {self.user} (ID: {self.user.id})")
        if not rotate_status.is_running():
            rotate_status.start()

    async def on_guild_join(self, guild: discord.Guild):
        # Quando entra em um novo servidor, força o sync para garantir
        # que os comandos apareçam imediatamente.
        try:
            await self.tree.sync()
            log.info(f"Sync forçado ao entrar em: {guild.name} ({guild.id})")
        except discord.HTTPException as e:
            log.warning(f"Falha no sync ao entrar em {guild.name}: {e}")

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

class EmbedModal(Modal, title="Criar Embed"):
    titulo = TextInput(label="Título", placeholder="Título do embed...", required=True, max_length=256)
    descricao = TextInput(label="Descrição", placeholder="Conteúdo principal do embed...", style=discord.TextStyle.paragraph, required=True, max_length=4000)
    cor = TextInput(label="Cor (hex, ex: #590CEA)", placeholder="#590CEA", required=False, max_length=7)
    rodape = TextInput(label="Rodapé", placeholder="Texto do rodapé (opcional)...", required=False, max_length=2048)
    imagem_url = TextInput(label="URL da imagem (opcional)", placeholder="https://...", required=False, max_length=512)

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
                return await interaction.response.send_message(
                    embed=error_embed("Cor inválida", "Use o formato `#RRGGBB`, ex: `#590CEA`."), ephemeral=True
                )
        embed = discord.Embed(title=self.titulo.value, description=self.descricao.value, color=color)
        embed.timestamp = discord.utils.utcnow()
        if self.rodape.value.strip():
            embed.set_footer(text=self.rodape.value.strip())
        if self.imagem_url.value.strip():
            embed.set_image(url=self.imagem_url.value.strip())
        try:
            await self.canal.send(embed=embed)
            await interaction.response.send_message(
                embed=success_embed("Embed enviada!", f"Publicada em {self.canal.mention}."), ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("Sem permissão", f"Não tenho permissão para enviar em {self.canal.mention}."), ephemeral=True
            )
        except discord.HTTPException as exc:
            await interaction.response.send_message(
                embed=error_embed("Erro", f"Falha ao enviar embed: {exc}"), ephemeral=True
            )

class EmbedEditModal(Modal, title="Editar Embed"):
    novo_titulo    = TextInput(label="Novo título (deixe em branco para manter)", required=False, max_length=256)
    nova_descricao = TextInput(label="Nova descrição (deixe em branco para manter)", style=discord.TextStyle.paragraph, required=False, max_length=4000)
    nova_cor       = TextInput(label="Nova cor hex (ex: #590CEA)", placeholder="#590CEA", required=False, max_length=7)
    novo_rodape    = TextInput(label="Novo rodapé (deixe em branco para manter)", required=False, max_length=2048)
    nova_imagem    = TextInput(label="Nova URL de imagem (deixe em branco para manter)", required=False, max_length=512)

    def __init__(self, message: discord.Message):
        super().__init__()
        self.target_message = message
        old = message.embeds[0] if message.embeds else None
        if old:
            if old.title:       self.novo_titulo.default    = old.title
            if old.description: self.nova_descricao.default = old.description[:4000]
            if old.color:       self.nova_cor.default       = f"#{old.color.value:06X}"
            if old.footer and old.footer.text: self.novo_rodape.default = old.footer.text
            if old.image and old.image.url:    self.nova_imagem.default = old.image.url

    async def on_submit(self, interaction: discord.Interaction):
        old_embed = self.target_message.embeds[0] if self.target_message.embeds else discord.Embed()
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
                embed=success_embed("Embed editada!", "As alterações foram aplicadas com sucesso."), ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=error_embed("Sem permissão", "Não consigo editar essa mensagem."), ephemeral=True
            )
        except discord.HTTPException as exc:
            await interaction.response.send_message(embed=error_embed("Erro", str(exc)), ephemeral=True)

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
            embed=success_embed("Anúncio enviado!", f"Publicado em {self.canal.mention}."), ephemeral=True
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
            embed=success_embed("Regras enviadas!", f"Publicado em {self.canal.mention}."), ephemeral=True
        )

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.danger, emoji="✖️")
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        await interaction.response.send_message(f"{E.ARROW_RED} Criação cancelada.", ephemeral=True)

# ==================================================
# =========== SISTEMA DE TICKETS ==================
# ==================================================

# ── Dados extras do bot para tickets ──────────────
# bot.ticket_banner_url  → URL do banner exibido no ticket aberto
# bot.ticket_atendentes  → dict[channel_id, user_id] atendente assumiu
# Adicionamos esses atributos no __init__ do ModBot abaixo via monkey-patch
#   (para não precisar mexer na classe no topo)
# ──────────────────────────────────────────────────

TICKET_CATEGORIES = [
    discord.SelectOption(label="Suporte Geral",    value="suporte",    description="Dúvidas gerais ou ajuda",           emoji="<:1000006244:1475982552488607815>"),
    discord.SelectOption(label="Denúncias",         value="denuncia",   description="Denunciar um membro ou situação",   emoji="<:1000006242:1475982573846139001>"),
    discord.SelectOption(label="Compra de VIP",     value="vip",        description="Adquirir um cargo VIP",             emoji="<:1000006239:1475982464928452678>"),
    discord.SelectOption(label="Resgate de Prêmio", value="premio",     description="Resgatar um prêmio conquistado",    emoji="<:1000006240:1475982529243643967>"),
    discord.SelectOption(label="Patrocínio",        value="patrocinio", description="Proposta de parceria ou patrocínio",emoji="<1000006247:1475982600463187990>"),
    discord.SelectOption(label="Outros",            value="outros",     description="Outros assuntos",                   emoji="<1000006236:1475982635384836126>"),
]

TICKET_EMOJI_MAP = {
    "suporte":    "<:1000006244:1475982552488607815>",
    "denuncia":   "<:1000006242:1475982573846139001>",
    "vip":        "<:1000006239:1475982464928452678>",
    "premio":     "<:1000006240:1475982529243643967>",
    "patrocinio": "<1000006247:1475982600463187990>",
    "outros":     "<1000006236:1475982635384836126>",
}
TICKET_LABEL_MAP = {
    "suporte":    "Suporte Geral",
    "denuncia":   "Denúncias",
    "vip":        "Compra de VIP",
    "premio":     "Resgate de Prêmio",
    "patrocinio": "Patrocínio",
    "outros":     "Outros",
}

# ── Modal: usuário descreve o motivo ao abrir ──────
class TicketMotivoModal(Modal, title="Descreva seu ticket"):
    motivo = TextInput(
        label="Qual é o motivo do seu ticket?",
        placeholder="Explique brevemente o que você precisa...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500,
    )

    def __init__(self, categoria: str):
        super().__init__()
        self.categoria = categoria

    async def on_submit(self, interaction: discord.Interaction):
        await _criar_ticket(interaction, self.categoria, self.motivo.value)


# ── Modal: adicionar membro ao ticket ─────────────
class AdicionarMembroModal(Modal, title="Adicionar Membro ao Ticket"):
    user_id = TextInput(
        label="ID do usuário a adicionar",
        placeholder="Ex: 123456789012345678",
        required=True,
        max_length=20,
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            uid = int(self.user_id.value.strip())
        except ValueError:
            return await interaction.response.send_message(
                embed=error_embed("ID inválido", "Digite um ID numérico válido."), ephemeral=True
            )
        member = interaction.guild.get_member(uid)
        if not member:
            return await interaction.response.send_message(
                embed=error_embed("Não encontrado", "Membro não está no servidor."), ephemeral=True
            )
        await interaction.channel.set_permissions(
            member,
            view_channel=True, send_messages=True, read_message_history=True,
        )
        await interaction.response.send_message(
            embed=success_embed("Membro adicionado", f"{E.ARROW_GREEN} {member.mention} foi adicionado ao ticket."),
            ephemeral=True,
        )
        await interaction.channel.send(
            embed=mod_embed(f"{E.ARROW_GREEN} Membro Adicionado", f"{member.mention} foi adicionado ao ticket por {interaction.user.mention}.")
        )


# ── Modal: remover membro do ticket ───────────────
class RemoverMembroModal(Modal, title="Remover Membro do Ticket"):
    user_id = TextInput(
        label="ID do usuário a remover",
        placeholder="Ex: 123456789012345678",
        required=True,
        max_length=20,
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            uid = int(self.user_id.value.strip())
        except ValueError:
            return await interaction.response.send_message(
                embed=error_embed("ID inválido", "Digite um ID numérico válido."), ephemeral=True
            )
        member = interaction.guild.get_member(uid)
        if not member:
            return await interaction.response.send_message(
                embed=error_embed("Não encontrado", "Membro não está no servidor."), ephemeral=True
            )
        await interaction.channel.set_permissions(member, overwrite=None)
        await interaction.response.send_message(
            embed=success_embed("Membro removido", f"{E.ARROW_RED} {member.mention} foi removido do ticket."),
            ephemeral=True,
        )
        await interaction.channel.send(
            embed=mod_embed(f"{E.ARROW_RED} Membro Removido", f"{member.mention} foi removido do ticket por {interaction.user.mention}.")
        )


# ── Painel Admin (Modal de renomear canal) ─────────
class RenomearCanalModal(Modal, title="Renomear Canal do Ticket"):
    novo_nome = TextInput(
        label="Novo nome do canal",
        placeholder="Ex: ticket-vip-pedro",
        required=True,
        max_length=50,
    )

    async def on_submit(self, interaction: discord.Interaction):
        nome = self.novo_nome.value.strip().lower().replace(" ", "-")
        try:
            await interaction.channel.edit(name=nome)
            await interaction.response.send_message(
                embed=success_embed("Canal renomeado", f"{E.ARROW_BLUE} Canal renomeado para `{nome}`."), ephemeral=True
            )
        except discord.HTTPException as e:
            await interaction.response.send_message(embed=error_embed("Erro", str(e)), ephemeral=True)


# ── View: Painel Admin ────────────────────────────
class TicketAdminView(View):
    def __init__(self, opener_id: int):
        super().__init__(timeout=None)
        self.opener_id = opener_id

    def _is_staff(self, interaction: discord.Interaction) -> bool:
        is_staff = bot.staff_role_id and any(r.id == bot.staff_role_id for r in interaction.user.roles)
        return bool(is_staff or interaction.user.guild_permissions.administrator)

    @discord.ui.button(label="Adicionar Membro", style=discord.ButtonStyle.primary, emoji="➕", row=0)
    async def add_member(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self._is_staff(interaction):
            return await interaction.response.send_message(embed=error_embed("Sem permissão", "Apenas a staff pode usar isso."), ephemeral=True)
        await interaction.response.send_modal(AdicionarMembroModal())

    @discord.ui.button(label="Remover Membro", style=discord.ButtonStyle.secondary, emoji="➖", row=0)
    async def remove_member(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self._is_staff(interaction):
            return await interaction.response.send_message(embed=error_embed("Sem permissão", "Apenas a staff pode usar isso."), ephemeral=True)
        await interaction.response.send_modal(RemoverMembroModal())

    @discord.ui.button(label="Renomear Canal", style=discord.ButtonStyle.secondary, emoji="✏️", row=0)
    async def renomear(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self._is_staff(interaction):
            return await interaction.response.send_message(embed=error_embed("Sem permissão", "Apenas a staff pode usar isso."), ephemeral=True)
        await interaction.response.send_modal(RenomearCanalModal())

    @discord.ui.button(label="Transcript", style=discord.ButtonStyle.success, emoji="📄", row=1)
    async def transcript(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self._is_staff(interaction):
            return await interaction.response.send_message(embed=error_embed("Sem permissão", "Apenas a staff pode usar isso."), ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        linhas = []
        async for msg in interaction.channel.history(limit=200, oldest_first=True):
            ts = msg.created_at.strftime("%d/%m/%Y %H:%M")
            conteudo = msg.content or "[embed/anexo]"
            linhas.append(f"[{ts}] {msg.author} ({msg.author.id}): {conteudo}")
        texto = "\n".join(linhas) or "Nenhuma mensagem encontrada."
        arquivo = discord.File(
            fp=__import__("io").BytesIO(texto.encode("utf-8")),
            filename=f"transcript-{interaction.channel.name}.txt",
        )
        await interaction.followup.send(
            embed=success_embed("Transcript gerado", f"{E.ARROW_BLUE} Log do canal `{interaction.channel.name}`."),
            file=arquivo,
            ephemeral=True,
        )

    @discord.ui.button(label="Fechar Silenciosamente", style=discord.ButtonStyle.danger, emoji="🗑️", row=1)
    async def fechar_silencioso(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self._is_staff(interaction):
            return await interaction.response.send_message(embed=error_embed("Sem permissão", "Apenas a staff pode usar isso."), ephemeral=True)
        await interaction.response.send_message(
            embed=mod_embed(f"{E.ARROW_RED} Fechando...", f"{E.LOADING} Canal será deletado em **3 segundos**.")
        )
        for uid, cid in list(bot.open_tickets.items()):
            if cid == interaction.channel.id:
                del bot.open_tickets[uid]
                break
        await bot.log_action(
            title="🗑️ Ticket Fechado (Admin)",
            description=f"Ticket `{interaction.channel.name}` fechado silenciosamente por {interaction.user.mention}.",
        )
        await asyncio.sleep(3)
        try:
            await interaction.channel.delete()
        except discord.HTTPException:
            pass


# ── View: Painel principal do ticket ──────────────
class TicketMainView(View):
    def __init__(self, opener_id: int):
        super().__init__(timeout=None)
        self.opener_id = opener_id

    def _is_staff(self, interaction: discord.Interaction) -> bool:
        is_staff = bot.staff_role_id and any(r.id == bot.staff_role_id for r in interaction.user.roles)
        return bool(is_staff or interaction.user.guild_permissions.administrator)

    @discord.ui.button(label="Atender", style=discord.ButtonStyle.success, emoji=discord.PartialEmoji.from_str("<a:1000006152:1475983799568433355>"), custom_id="ticket_atender", row=0)
    async def atender(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self._is_staff(interaction):
            return await interaction.response.send_message(embed=error_embed("Sem permissão", "Apenas a staff pode assumir tickets."), ephemeral=True)
        # Registra atendente
        if not hasattr(bot, "ticket_atendentes"):
            bot.ticket_atendentes = {}
        bot.ticket_atendentes[interaction.channel.id] = interaction.user.id
        embed = discord.Embed(
            title=f"{E.VERIFY} Ticket Assumido",
            description=(
                f"{E.CALENDAR} **Atendente:** {interaction.user.mention}\n\n"
                f"{E.ARROW} Olá! Estou aqui para te ajudar.\n"
                f"{E.SPARKLE} Em que posso ser útil?"
            ),
            color=Colors.MAIN,
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed)
        await bot.log_action(
            title=f"{E.VERIFY} Ticket Assumido",
            description=f"{interaction.user.mention} assumiu o ticket `{interaction.channel.name}`.",
        )

    @discord.ui.button(label="Painel Admin", style=discord.ButtonStyle.primary, emoji=discord.PartialEmoji.from_str("<:1000006182:1475983151712174290>"), custom_id="ticket_admin_panel", row=0)
    async def painel_admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self._is_staff(interaction):
            return await interaction.response.send_message(embed=error_embed("Sem permissão", "Apenas a staff pode acessar o painel admin."), ephemeral=True)
        embed = discord.Embed(
            title=f"{E.SETTINGS} Painel Admin",
            description=(
                f"{E.ARROW} Use os botões abaixo para gerenciar este ticket.\n\n"
                f"{E.PIN} **Adicionar Membro** — adiciona alguém ao canal\n"
                f"{E.WARN_IC} **Remover Membro** — remove acesso de alguém\n"
                f"{E.PEN} **Renomear Canal** — altera o nome do ticket\n"
                f"{E.RULES} **Transcript** — gera log das mensagens\n"
                f"{E.FIRE} **Fechar Silenciosamente** — deleta sem aviso"
            ),
            color=Colors.MAIN,
        )
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed, view=TicketAdminView(self.opener_id), ephemeral=True)

    @discord.ui.button(label="Fechar", style=discord.ButtonStyle.danger, emoji=discord.PartialEmoji.from_str("<a:i_exclamation:1446591025622679644>"), custom_id="ticket_fechar", row=1)
    async def fechar(self, interaction: discord.Interaction, button: discord.ui.Button):
        is_staff = self._is_staff(interaction)
        is_owner = interaction.user.id == self.opener_id
        if not (is_staff or is_owner):
            return await interaction.response.send_message(
                embed=error_embed("Sem permissão", "Apenas a staff ou quem abriu o ticket pode fechá-lo."), ephemeral=True
            )
        await interaction.response.send_message(
            embed=mod_embed(f"{E.ARROW_YELLOW} Fechando ticket...", f"{E.LOADING} Este canal será deletado em **5 segundos**.")
        )
        for uid, cid in list(bot.open_tickets.items()):
            if cid == interaction.channel.id:
                del bot.open_tickets[uid]
                break
        await bot.log_action(
            title="🔒 Ticket Fechado",
            description=f"Ticket `{interaction.channel.name}` fechado por {interaction.user.mention}.",
            fields=[("Canal", interaction.channel.name, True)],
        )
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason=f"Ticket fechado por {interaction.user}")
        except discord.HTTPException:
            pass

    @discord.ui.button(label="Notificar Atendente", style=discord.ButtonStyle.secondary, emoji=discord.PartialEmoji.from_str("<a:1503hearts:1430339028720549908>"), custom_id="ticket_notificar", row=1)
    async def notificar(self, interaction: discord.Interaction, button: discord.ui.Button):
        staff_role = interaction.guild.get_role(bot.staff_role_id) if bot.staff_role_id else None
        # Se há atendente assumido, menciona ele diretamente
        atendente_id = getattr(bot, "ticket_atendentes", {}).get(interaction.channel.id)
        if atendente_id:
            atendente = interaction.guild.get_member(atendente_id)
            if atendente:
                await interaction.response.send_message(
                    content=atendente.mention,
                    embed=mod_embed(
                        f"{E.WARN_IC} Atendente Notificado",
                        f"{interaction.user.mention} está aguardando sua atenção neste ticket!",
                    ),
                )
                return
        # Fallback: menciona o cargo da staff
        if staff_role:
            await interaction.response.send_message(
                content=staff_role.mention,
                embed=mod_embed(
                    f"{E.WARN_IC} Staff Notificada",
                    f"{interaction.user.mention} está aguardando atendimento neste ticket!",
                ),
            )
        else:
            await interaction.response.send_message(
                embed=error_embed("Sem staff configurada", "Nenhum cargo de staff foi definido. Use `/setup-tickets` para configurar."),
                ephemeral=True,
            )


# ── View: Select para abrir ticket ────────────────
class TicketSelectView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCategorySelect())


class TicketCategorySelect(Select):
    def __init__(self):
        super().__init__(
            placeholder="Selecione o motivo do seu ticket...",
            options=TICKET_CATEGORIES,
            min_values=1, max_values=1,
            custom_id="ticket_category_select",
        )

    async def callback(self, interaction: discord.Interaction):
        categoria = self.values[0]
        if interaction.user.id in bot.open_tickets:
            canal_existente = interaction.guild.get_channel(bot.open_tickets[interaction.user.id])
            if canal_existente:
                return await interaction.response.send_message(
                    embed=error_embed(
                        "Ticket já aberto",
                        f"{E.ARROW_BLUE} Você já tem um ticket aberto: {canal_existente.mention}\nFeche-o antes de abrir outro.",
                    ),
                    ephemeral=True,
                )
            else:
                del bot.open_tickets[interaction.user.id]

        if not bot.ticket_category_id:
            return await interaction.response.send_message(
                embed=error_embed(
                    "Não configurado",
                    f"{E.SETTINGS} O sistema de tickets não está configurado.\nUm administrador precisa usar `/setup-tickets`.",
                ),
                ephemeral=True,
            )
        # Abre modal para o usuário descrever o motivo
        await interaction.response.send_modal(TicketMotivoModal(categoria))


# ── Função central de criação de ticket ───────────
async def _criar_ticket(interaction: discord.Interaction, categoria: str, motivo_usuario: str):
    await interaction.response.defer(ephemeral=True)

    guild      = interaction.guild
    category   = guild.get_channel(bot.ticket_category_id)
    staff_role = guild.get_role(bot.staff_role_id) if bot.staff_role_id else None
    emoji      = TICKET_EMOJI_MAP.get(categoria, "💬")
    label      = TICKET_LABEL_MAP.get(categoria, "Ticket")
    nome_canal = f"ticket-{interaction.user.name}".lower().replace(" ", "-")[:50]

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(
            view_channel=True, send_messages=True,
            read_message_history=True, attach_files=True,
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True,
            manage_channels=True, manage_messages=True,
            read_message_history=True,
        ),
    }
    if staff_role:
        overwrites[staff_role] = discord.PermissionOverwrite(
            view_channel=True, send_messages=True,
            read_message_history=True, manage_messages=True,
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
            embed=error_embed("Sem permissão", "Não consigo criar canais. Verifique as permissões do bot."), ephemeral=True
        )
    except discord.HTTPException as exc:
        return await interaction.followup.send(
            embed=error_embed("Erro", f"Falha ao criar canal: {exc}"), ephemeral=True
        )

    bot.open_tickets[interaction.user.id] = ticket_channel.id

    # ── Embed de boas-vindas ──
    welcome_embed = discord.Embed(
        title=f"{E.FIRE} {label}",
        description=(
            f"{E.SYMBOL}{E.LEAF}\n"
            f"{E.CALENDAR} **Aberto por:** {interaction.user.mention}\n"
            f"{E.RULES} **Categoria:** {label}\n"
            f"{E.DIAMOND} **Motivo:** {motivo_usuario}\n"
            f"{E.SYMBOL}{E.LEAF}\n\n"
            f"{E.ARROW} Olá, {interaction.user.mention}!\n"
            f"{E.ORB_GREEN} Me diga mais detalhes enquanto aguarda a equipe responsável.\n\n"
            f"{E.RING} Nossa equipe irá te atender em breve {E.HEARTS_S}"
        ),
        color=Colors.MAIN,
    )
    welcome_embed.set_thumbnail(url=interaction.user.display_avatar.url)
    welcome_embed.set_footer(text=f"{guild.name} • ID do usuário: {interaction.user.id}")
    welcome_embed.timestamp = discord.utils.utcnow()

    # Banner (se configurado via /setup-tickets)
    banner_url = getattr(bot, "ticket_banner_url", None)
    if banner_url:
        welcome_embed.set_image(url=banner_url)

    main_view  = TicketMainView(opener_id=interaction.user.id)
    staff_ping = staff_role.mention if staff_role else ""
    await ticket_channel.send(
        content=f"{interaction.user.mention} {staff_ping}".strip(),
        embed=welcome_embed,
        view=main_view,
    )

    await interaction.followup.send(
        embed=success_embed("Ticket criado!", f"{E.ARROW_BLUE} Seu ticket foi aberto em {ticket_channel.mention}."),
        ephemeral=True,
    )
    await bot.log_action(
        title=f"{emoji} Ticket Aberto",
        description=f"{interaction.user} abriu um ticket de **{label}**.",
        fields=[
            ("Canal", ticket_channel.mention, True),
            ("Categoria", label, True),
            ("Usuário ID", str(interaction.user.id), True),
            ("Motivo", motivo_usuario[:200], False),
        ],
    )
    log.info(f"Ticket criado: #{nome_canal} por {interaction.user} ({categoria})")


# ── View legada (compatibilidade) ─────────────────
class TicketCloseView(View):
    """Mantida para tickets abertos antes da atualização."""
    def __init__(self, opener_id: int):
        super().__init__(timeout=None)
        self.opener_id = opener_id

    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="ticket_close_legacy")
    async def fechar(self, interaction: discord.Interaction, button: discord.ui.Button):
        is_staff = bot.staff_role_id and any(r.id == bot.staff_role_id for r in interaction.user.roles)
        is_owner = interaction.user.id == self.opener_id
        is_admin = interaction.user.guild_permissions.administrator
        if not (is_staff or is_owner or is_admin):
            return await interaction.response.send_message(
                embed=error_embed("Sem permissão", "Apenas a staff ou quem abriu o ticket pode fechá-lo."), ephemeral=True
            )
        await interaction.response.send_message(
            embed=mod_embed(f"{E.ARROW_YELLOW} Fechando ticket...", f"{E.LOADING} Este canal será deletado em **5 segundos**.")
        )
        for uid, cid in list(bot.open_tickets.items()):
            if cid == interaction.channel.id:
                del bot.open_tickets[uid]
                break
        await bot.log_action(
            title="🔒 Ticket Fechado",
            description=f"Ticket `{interaction.channel.name}` fechado por {interaction.user.mention}.",
            fields=[("Canal", interaction.channel.name, True)],
        )
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason=f"Ticket fechado por {interaction.user}")
        except discord.HTTPException:
            pass

# ==================================================
# ============= COMANDOS DE TICKET ================
# ==================================================

@bot.tree.command(name="setup-tickets", description="Configura o sistema de tickets do servidor")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    categoria="Categoria onde os canais de ticket serão criados",
    cargo_staff="Cargo da staff que terá acesso aos tickets",
    canal_log="Canal para logs de tickets (opcional)",
    banner_url="URL do banner/imagem exibido dentro do ticket ao abrir (opcional)",
)
async def setup_tickets(
    interaction: discord.Interaction,
    categoria: discord.CategoryChannel,
    cargo_staff: discord.Role,
    canal_log: discord.TextChannel | None = None,
    banner_url: str | None = None,
):
    bot.ticket_category_id = categoria.id
    bot.staff_role_id      = cargo_staff.id
    if canal_log:
        bot.ticket_log_channel_id = canal_log.id
        bot.log_channel_id        = canal_log.id
    if banner_url:
        bot.ticket_banner_url = banner_url

    embed = success_embed(
        "Tickets configurados!",
        f"{E.SYMBOL} **Categoria:** {categoria.name}\n"
        f"{E.CALENDAR} **Cargo staff:** {cargo_staff.mention}\n"
        f"{E.LINK} **Log:** {canal_log.mention if canal_log else 'Não definido'}\n"
        f"{E.GEM} **Banner:** {'Configurado ✅' if banner_url else 'Não definido'}\n\n"
        f"{E.ARROW} Use `/ticket-painel` para enviar o painel de tickets em um canal.",
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)
    log.info(f"Tickets configurados: categoria={categoria.id}, staff={cargo_staff.id}")

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
        title=f"{E.FIRE} {titulo}",
        description=(
            f"{E.SYMBOL}{E.LEAF}\n"
            f"{E.ARROW} {descricao}\n"
            f"{E.SYMBOL}{E.LEAF}\n\n"
            f"{E.SPARKLE} **Categorias disponíveis:**\n"
            f"{E.ARROW} Suporte Geral\n"
            f"{E.ARROW} Denúncias\n"
            f"{E.ARROW} Compra de VIP\n"
            f"{E.ARROW} Resgate de Prêmio\n"
            f"{E.ARROW} Patrocínio\n"
            f"{E.ARROW} Outros\n\n"
            f"{E.ORB_GREEN} Selecione abaixo e aguarde nossa equipe! {E.HEARTS_S}"
        ),
        color=Colors.MAIN,
    )
    embed.set_footer(text=f"{interaction.guild.name} • Ticket")
    embed.timestamp = discord.utils.utcnow()
    if imagem_url:
        embed.set_image(url=imagem_url)

    view = TicketSelectView()
    try:
        await canal.send(embed=embed, view=view)
        await interaction.response.send_message(
            embed=success_embed("Painel enviado!", f"{E.ARROW_BLUE} Painel de tickets publicado em {canal.mention}."), ephemeral=True
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            embed=error_embed("Sem permissão", f"Não consigo enviar em {canal.mention}."), ephemeral=True
        )

@bot.tree.command(name="fechar-ticket", description="Fecha e deleta o ticket atual")
@app_commands.default_permissions(manage_channels=True)
async def fechar_ticket(interaction: discord.Interaction):
    is_ticket = any(cid == interaction.channel.id for cid in bot.open_tickets.values())
    if not is_ticket:
        return await interaction.response.send_message(
            embed=error_embed("Erro", "Este canal não é um ticket aberto."), ephemeral=True
        )
    await interaction.response.send_message(
        embed=mod_embed(f"{E.ARROW_YELLOW} Fechando ticket...", f"{E.LOADING} Este canal será deletado em **5 segundos**.")
    )
    for uid, cid in list(bot.open_tickets.items()):
        if cid == interaction.channel.id:
            del bot.open_tickets[uid]
            break

    await bot.log_action(title="🔒 Ticket Fechado", description=f"Ticket `{interaction.channel.name}` fechado por {interaction.user.mention}.")
    await asyncio.sleep(5)
    try:
        await interaction.channel.delete(reason=f"Ticket fechado por {interaction.user}")
    except discord.HTTPException:
        pass

# ==================================================
# =========== SISTEMA DE AUTOMOD ==================
# ==================================================

AUTOMOD_KEYWORDS = [
    ["idiota", "imbecil", "cretino", "babaca", "otário", "fdp", "vsf", "porra", "merda", "caralho"],
    ["viado", "bicha", "sapatão", "*macaco*", "judeu", "cigano"],
    ["*vou te matar*", "*te mato*", "*explodir*", "*atirar em*"],
    ["discord.gg/*", "*discordapp.com/invite*", "bit.ly/*", "tinyurl.com/*", "*free nitro*"],
    ["*porn*", "*nude*", "*nudes*", "*pack*", "onlyfans.com/*"],
    ["*ganhe nitro*", "*ganhe robux*", "*acesse agora*", "*clique aqui*", "*promoção exclusiva*"],
]

async def _criar_regra_http(guild: discord.Guild, payload: dict) -> bool:
    import aiohttp
    url = f"https://discord.com/api/v10/guilds/{guild.id}/auto-moderation/rules"
    headers = {
        "Authorization": f"Bot {TOKEN}",
        "Content-Type": "application/json",
        "X-Audit-Log-Reason": "AutoMod setup automatico pelo bot",
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            return resp.status in (200, 201)

async def create_automod_rules(guild: discord.Guild) -> tuple[int, int]:
    criadas = 0
    erros   = 0

    for i, keywords in enumerate(AUTOMOD_KEYWORDS):
        payload = {
            "name": f"[Bot] Palavras bloqueadas #{i+1}",
            "event_type": 1,
            "trigger_type": 1,
            "trigger_metadata": {"keyword_filter": keywords},
            "actions": [{"type": 1, "metadata": {"custom_message": "Sua mensagem foi bloqueada por conter conteúdo proibido."}}],
            "enabled": True,
        }
        ok = await _criar_regra_http(guild, payload)
        if ok: criadas += 1
        else:  erros   += 1

    # Anti-Mention Spam
    ok = await _criar_regra_http(guild, {
        "name": "[Bot] Anti-Mention Spam",
        "event_type": 1, "trigger_type": 5,
        "trigger_metadata": {"mention_total_limit": 5, "mention_raid_protection_enabled": True},
        "actions": [
            {"type": 1, "metadata": {"custom_message": "Muitas menções em uma só mensagem."}},
            {"type": 3, "metadata": {"duration_seconds": 600}},
        ],
        "enabled": True,
    })
    if ok: criadas += 1
    else:  erros   += 1

    # Anti-Spam
    ok = await _criar_regra_http(guild, {
        "name": "[Bot] Anti-Spam de Conteúdo",
        "event_type": 1, "trigger_type": 3,
        "actions": [{"type": 1, "metadata": {"custom_message": "Conteúdo identificado como spam."}}],
        "enabled": True,
    })
    if ok: criadas += 1
    else:  erros   += 1

    # Keyword Preset
    ok = await _criar_regra_http(guild, {
        "name": "[Bot] Conteúdo Explícito (Preset)",
        "event_type": 1, "trigger_type": 4,
        "trigger_metadata": {"presets": [1, 2, 3]},
        "actions": [{"type": 1, "metadata": {"custom_message": "Conteúdo não permitido neste servidor."}}],
        "enabled": True,
    })
    if ok: criadas += 1
    else:  erros   += 1

    # Member Profile
    ok = await _criar_regra_http(guild, {
        "name": "[Bot] Perfil Inadequado",
        "event_type": 2, "trigger_type": 6,
        "trigger_metadata": {"keyword_filter": ["*porn*", "*nude*", "*hack*", "*fdp*", "*porra*", "*merda*", "*caralho*", "*viado*", "*putaria*"]},
        "actions": [{"type": 4, "metadata": {}}],
        "enabled": True,
    })
    if ok: criadas += 1
    else:  erros   += 1

    return criadas, erros

@bot.tree.command(name="automod-setup", description="Cria regras de AutoMod automáticas neste servidor")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(canal_log="Canal onde o AutoMod vai registrar as ocorrências (opcional)")
async def automod_setup(interaction: discord.Interaction, canal_log: discord.TextChannel | None = None):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    try:
        existing      = await guild.fetch_automod_rules()
        existing_names = {r.name for r in existing}
    except discord.Forbidden:
        return await interaction.followup.send(
            embed=error_embed("Sem permissão", "Preciso da permissão **Gerenciar Servidor** para criar regras de AutoMod."), ephemeral=True
        )

    bot_rules = [n for n in existing_names if n.startswith("[Bot]")]
    if bot_rules:
        return await interaction.followup.send(
            embed=error_embed(
                "Já configurado",
                f"{E.INFO_IC} Este servidor já tem **{len(bot_rules)}** regra(s) criadas pelo bot.\n"
                f"{E.ARROW_BLUE} Use `/automod-status` para ver o total ou `/automod-reset` para recriar.",
            ),
            ephemeral=True,
        )

    criadas, erros = await create_automod_rules(guild)

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
            + (f"{E.ARROW_RED} **{erros}** regra(s) falharam.\n" if erros else "")
            + (f"{E.INFO_IC} Logs serão enviados em {canal_log.mention}.\n" if canal_log else "")
            + f"\n{E.STAR} **Regras ativas protegem contra:**\n"
            f"{E.ARROW_BLUE} Palavrões e ofensas (6 blocos de keywords)\n"
            f"{E.ARROW_BLUE} Mention spam (timeout automático)\n"
            f"{E.ARROW_BLUE} Spam de conteúdo genérico\n"
            f"{E.ARROW_BLUE} Conteúdo explícito (preset Discord)\n"
            f"{E.ARROW_BLUE} Perfis inadequados (bio/nick)\n"
            f"\n{E.INFO_IC} Máximo possível: **10 regras** por servidor."
        ),
        color=Colors.MAIN,
    )
    embed.set_footer(text=f"Servidor: {guild.name} • {guild.id}")
    embed.timestamp = discord.utils.utcnow()
    await interaction.followup.send(embed=embed, ephemeral=True)
    await bot.log_action(
        title=f"{E.SETTINGS} AutoMod Setup",
        description=f"{interaction.user} configurou o AutoMod em **{guild.name}**.",
        fields=[("Regras criadas", str(criadas), True), ("Erros", str(erros), True), ("Log", canal_log.mention if canal_log else "Não definido", True)],
    )

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
    desc = "\n".join(f"{E.ARROW_BLUE} {r.name}" for r in bot_rules) or f"{E.ARROW_RED} Nenhuma regra encontrada."
    embed = discord.Embed(
        title=f"{E.SETTINGS} Status do AutoMod",
        description=(
            f"{E.INFO_IC} **Regras do bot neste servidor:** `{len(bot_rules)}`\n"
            f"{E.STAR} **Total de regras no servidor:** `{len(rules)}`\n\n"
            f"{E.ARROW_BLUE} **Regras criadas pelo bot:**\n{desc}"
        ),
        color=Colors.MAIN,
    )
    embed.set_footer(text=f"Servidor: {interaction.guild.name}")
    embed.timestamp = discord.utils.utcnow()
    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="automod-reset", description="Deleta as regras antigas do bot e recria tudo do zero")
@app_commands.default_permissions(administrator=True)
async def automod_reset(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    try:
        rules = await guild.fetch_automod_rules()
    except discord.Forbidden:
        return await interaction.followup.send(
            embed=error_embed("Sem permissão", "Preciso da permissão **Gerenciar Servidor**."), ephemeral=True
        )

    bot_rules = [r for r in rules if r.name.startswith("[Bot]")]
    deletadas = 0
    for rule in bot_rules:
        try:
            await rule.delete(reason="AutoMod reset pelo bot")
            deletadas += 1
        except discord.HTTPException:
            pass

    await asyncio.sleep(2)
    criadas, erros = await create_automod_rules(guild)

    embed = discord.Embed(
        title=f"{E.VERIFY} AutoMod Resetado!",
        description=(
            f"{E.ARROW_RED} **{deletadas}** regra(s) antiga(s) deletada(s).\n"
            f"{E.ARROW_GREEN} **{criadas}** regra(s) nova(s) criadas.\n"
            + (f"{E.WARN_IC} **{erros}** falha(s) ao criar.\n" if erros else "")
        ),
        color=Colors.MAIN,
    )
    embed.set_footer(text=f"Servidor: {guild.name}")
    embed.timestamp = discord.utils.utcnow()
    await interaction.followup.send(embed=embed, ephemeral=True)
    await bot.log_action(
        title=f"{E.SETTINGS} AutoMod Reset",
        description=f"{interaction.user} resetou o AutoMod em **{guild.name}**.",
        fields=[("Deletadas", str(deletadas), True), ("Criadas", str(criadas), True), ("Erros", str(erros), True)],
    )

# ==================================================
# =========== SISTEMA DE EMBEDS (COMANDOS) =========
# ==================================================

# ─────────────────────────────────────────────────────────────────────────────
# CORREÇÃO DE VISIBILIDADE
# default_permissions define QUEM VÊ o comando na lista do Discord.
# Membros sem a permissão não veem o comando — exatamente como a Loritta faz.
# manage_messages = staff/admin veem; membros normais não veem.
# ─────────────────────────────────────────────────────────────────────────────

@bot.tree.command(name="embed", description="Criar e enviar uma embed personalizada em um canal")
@app_commands.default_permissions(manage_messages=True)
@app_commands.describe(canal="Canal onde a embed será enviada")
async def embed_cmd(interaction: discord.Interaction, canal: discord.TextChannel):
    view    = EmbedBuilderView(autor=interaction.user, canal=canal)
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
@app_commands.describe(canal="Canal de destino", titulo="Título da embed", descricao="Descrição/conteúdo", cor="Cor em hex (ex: #590CEA)")
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
@app_commands.describe(canal="Canal onde a mensagem está", message_id="ID da mensagem com a embed")
async def embed_editar(interaction: discord.Interaction, canal: discord.TextChannel, message_id: str):
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
            embed=error_embed("Mensagem não encontrada", f"Não encontrei a mensagem `{mid}` em {canal.mention}."), ephemeral=True
        )
    except discord.Forbidden:
        return await interaction.response.send_message(
            embed=error_embed("Sem permissão", f"Não consigo acessar mensagens em {canal.mention}."), ephemeral=True
        )
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
# Estes NÃO têm default_permissions, então aparecem
# para TODOS os membros — igual /ping da Loritta.
# ==================================================

@bot.tree.command(name="ping", description="Verifica se o bot está online e mostra a latência")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    embed   = discord.Embed(
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
    roles  = [r.mention for r in reversed(membro.roles) if r.name != "@everyone"]
    embed  = discord.Embed(title=f"{E.STAFF} {membro.display_name}", color=Colors.MAIN)
    embed.set_thumbnail(url=membro.display_avatar.url)
    embed.add_field(name=f"{E.SPARKLE} Tag",   value=str(membro), inline=True)
    embed.add_field(name=f"{E.INFO_IC} ID",     value=f"`{membro.id}`", inline=True)
    embed.add_field(name=f"{E.VERIFY} Bot?",    value="Sim" if membro.bot else "Não", inline=True)
    embed.add_field(
        name=f"{E.ARROW_BLUE} Entrou no servidor",
        value=discord.utils.format_dt(membro.joined_at, "R") if membro.joined_at else "Desconhecido",
        inline=True,
    )
    embed.add_field(name=f"{E.STAR} Conta criada", value=discord.utils.format_dt(membro.created_at, "R"), inline=True)
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
    embed.add_field(name=f"{E.DISCORD} Região",     value=str(g.preferred_locale), inline=True)
    embed.add_field(name=f"{E.VERIFY} Membros",   value=f"`{g.member_count}`", inline=True)
    embed.add_field(name=f"{E.ANNOUNCE} Canais",  value=f"`{len(g.channels)}`", inline=True)
    embed.add_field(name=f"{E.SETTINGS} Cargos",  value=f"`{len(g.roles)}`", inline=True)
    embed.add_field(name=f"{E.STAR} Emojis",    value=f"`{len(g.emojis)}`", inline=True)
    embed.add_field(name=f"{E.GEM_SHINE} Boosts",     value=f"`{g.premium_subscription_count}` (Nível {g.premium_tier})", inline=True)
    embed.add_field(name=f"{E.ARROW_BLUE} Criado em", value=discord.utils.format_dt(g.created_at, "D"), inline=True)
    embed.set_footer(text=f"Solicitado por {interaction.user.display_name}")
    embed.timestamp = discord.utils.utcnow()
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="avatar", description="Exibe o avatar de um membro em alta resolução")
@app_commands.describe(membro="Membro cujo avatar exibir")
async def avatar(interaction: discord.Interaction, membro: discord.Member | None = None):
    membro = membro or interaction.user
    embed  = discord.Embed(title=f"{E.STAR} Avatar de {membro.display_name}", color=Colors.MAIN)
    embed.set_image(url=membro.display_avatar.with_size(1024).url)
    embed.add_field(name=f"{E.INFO_IC} Links", value=(
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
        embed=success_embed("Configuração salva", f"{E.ARROW_BLUE} Canal de logs definido para {canal.mention}."),
        ephemeral=True,
    )
    log.info(f"Canal de logs atualizado para #{canal.name} ({canal.id})")

# ==================================================
# ============= MODERAÇÃO =========================
# ==================================================

@bot.tree.command(name="ban", description="Banir um membro do servidor")
@app_commands.default_permissions(ban_members=True)
@app_commands.describe(membro="Membro a ser banido", motivo="Motivo do banimento")
async def ban(interaction: discord.Interaction, membro: discord.Member, motivo: str = "Sem motivo especificado"):
    if membro == interaction.user:
        return await interaction.response.send_message(embed=error_embed("Erro", "Você não pode se banir."), ephemeral=True)
    if membro.top_role >= interaction.guild.me.top_role:
        return await interaction.response.send_message(
            embed=error_embed("Sem permissão", "Não consigo banir esse membro (cargo superior ao meu)."), ephemeral=True
        )
    await interaction.response.defer(ephemeral=True)
    try:
        await membro.send(f"Você foi **banido** do servidor **{interaction.guild.name}**.\nMotivo: {motivo}")
    except (discord.Forbidden, discord.HTTPException):
        pass
    await membro.ban(reason=f"{interaction.user} — {motivo}", delete_message_days=0)
    embed = mod_embed(
        f"{E.ARROW_RED} Membro Banido",
        f"{E.STAFF} **Usuário:** {membro.mention} (`{membro}`)\n"
        f"{E.PIN} **Motivo:** {motivo}\n"
        f"{E.BRANXO} **Moderador:** {interaction.user.mention}",
    )
    await interaction.followup.send(embed=embed, ephemeral=True)
    await bot.log_action(title=f"{E.ARROW_RED} Ban", description=f"{membro} banido por {interaction.user}.", fields=[("Motivo", motivo, False)])

@bot.tree.command(name="unban", description="Desbanir um usuário pelo ID")
@app_commands.default_permissions(ban_members=True)
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
            embed=success_embed("Usuário desbanido", f"{E.ARROW_GREEN} {user} (`{uid}`) foi desbanido.\n{E.PIN} **Motivo:** {motivo}"),
            ephemeral=True,
        )
        await bot.log_action(title=f"{E.ARROW_GREEN} Unban", description=f"{user} desbanido por {interaction.user}.", fields=[("Motivo", motivo, False)])
    except discord.NotFound:
        await interaction.followup.send(embed=error_embed("Não encontrado", "Usuário não encontrado ou não está banido."), ephemeral=True)
    except discord.HTTPException as exc:
        await interaction.followup.send(embed=error_embed("Erro", str(exc)), ephemeral=True)

@bot.tree.command(name="kick", description="Expulsar um membro do servidor")
@app_commands.default_permissions(kick_members=True)
@app_commands.describe(membro="Membro a ser expulso", motivo="Motivo da expulsão")
async def kick(interaction: discord.Interaction, membro: discord.Member, motivo: str = "Sem motivo especificado"):
    if membro == interaction.user:
        return await interaction.response.send_message(embed=error_embed("Erro", "Você não pode se expulsar."), ephemeral=True)
    if membro.top_role >= interaction.guild.me.top_role:
        return await interaction.response.send_message(
            embed=error_embed("Sem permissão", "Não consigo expulsar esse membro (cargo superior ao meu)."), ephemeral=True
        )
    await interaction.response.defer(ephemeral=True)
    try:
        await membro.send(f"Você foi **expulso** do servidor **{interaction.guild.name}**.\nMotivo: {motivo}")
    except (discord.Forbidden, discord.HTTPException):
        pass
    await membro.kick(reason=f"{interaction.user} — {motivo}")
    embed = mod_embed(
        f"{E.ARROW_ORANGE} Membro Expulso",
        f"{E.STAFF} **Usuário:** {membro.mention} (`{membro}`)\n"
        f"{E.PIN} **Motivo:** {motivo}\n"
        f"{E.BRANXO} **Moderador:** {interaction.user.mention}",
    )
    await interaction.followup.send(embed=embed, ephemeral=True)
    await bot.log_action(title=f"{E.ARROW_ORANGE} Kick", description=f"{membro} expulso por {interaction.user}.", fields=[("Motivo", motivo, False)])

@bot.tree.command(name="mute", description="Aplicar timeout em um membro")
@app_commands.default_permissions(moderate_members=True)
@app_commands.describe(membro="Membro a silenciar", minutos="Duração em minutos (máx. 40320)")
async def mute(interaction: discord.Interaction, membro: discord.Member, minutos: app_commands.Range[int, 1, 40320]):
    if membro.top_role >= interaction.guild.me.top_role:
        return await interaction.response.send_message(
            embed=error_embed("Sem permissão", "Não consigo silenciar esse membro."), ephemeral=True
        )
    await interaction.response.defer(ephemeral=True)
    until = discord.utils.utcnow() + timedelta(minutes=minutos)
    await membro.timeout(until, reason=f"Mute por {interaction.user} — {minutos} min")
    embed = mod_embed(
        f"{E.ARROW_YELLOW} Membro Silenciado",
        f"{E.STAFF} **Usuário:** {membro.mention}\n"
        f"{E.ARROW_BLUE} **Duração:** {minutos} minuto(s)\n"
        f"{E.BRANXO} **Moderador:** {interaction.user.mention}\n"
        f"{E.LOADING} **Expira:** {discord.utils.format_dt(until, 'R')}",
    )
    await interaction.followup.send(embed=embed, ephemeral=True)
    await bot.log_action(title=f"{E.ARROW_YELLOW} Mute", description=f"{membro} silenciado por {interaction.user} por {minutos} minuto(s).")

@bot.tree.command(name="unmute", description="Remover timeout de um membro")
@app_commands.default_permissions(moderate_members=True)
@app_commands.describe(membro="Membro para remover o timeout")
async def unmute(interaction: discord.Interaction, membro: discord.Member):
    await interaction.response.defer(ephemeral=True)
    if not membro.timed_out_until:
        return await interaction.followup.send(
            embed=error_embed("Erro", f"{membro.mention} não está em timeout."), ephemeral=True
        )
    await membro.timeout(None, reason=f"Unmute por {interaction.user}")
    embed = mod_embed(
        f"{E.ARROW_GREEN} Timeout Removido",
        f"{E.STAFF} **Usuário:** {membro.mention}\n{E.BRANXO} **Moderador:** {interaction.user.mention}",
    )
    await interaction.followup.send(embed=embed, ephemeral=True)
    await bot.log_action(title=f"{E.ARROW_GREEN} Unmute", description=f"Timeout de {membro} removido por {interaction.user}.")

@bot.tree.command(name="clear", description="Apagar mensagens do canal")
@app_commands.default_permissions(manage_messages=True)
@app_commands.describe(quantidade="Número de mensagens a apagar (1–100)")
async def clear(interaction: discord.Interaction, quantidade: app_commands.Range[int, 1, 100]):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=quantidade)
    await interaction.followup.send(
        embed=success_embed("Mensagens apagadas", f"{E.ARROW_BLUE} `{len(deleted)}` mensagem(ns) apagada(s) em {interaction.channel.mention}."),
        ephemeral=True,
    )
    await bot.log_action(title=f"{E.WARN_IC} Clear", description=f"{interaction.user} apagou `{len(deleted)}` mensagem(ns) em {interaction.channel.mention}.")

# ==================================================
# ============= SISTEMA DE WARNS ==================
# ==================================================

_warns: dict[int, list[str]] = {}

@bot.tree.command(name="warn", description="Avisar um membro")
@app_commands.default_permissions(moderate_members=True)
@app_commands.describe(membro="Membro a ser avisado", motivo="Motivo do aviso")
async def warn(interaction: discord.Interaction, membro: discord.Member, motivo: str):
    _warns.setdefault(membro.id, []).append(motivo)
    total = len(_warns[membro.id])
    embed = mod_embed(
        f"{E.WARN_IC} Aviso Aplicado",
        f"{E.STAFF} **Usuário:** {membro.mention}\n"
        f"{E.PIN} **Motivo:** {motivo}\n"
        f"{E.BRANXO} **Moderador:** {interaction.user.mention}\n"
        f"{E.STAR} **Total de avisos:** `{total}`",
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)
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
@app_commands.describe(membro="Membro a consultar")
async def warns_cmd(interaction: discord.Interaction, membro: discord.Member):
    lista = _warns.get(membro.id, [])
    if not lista:
        return await interaction.response.send_message(
            embed=success_embed("Sem avisos", f"{membro.mention} não tem nenhum aviso registrado."), ephemeral=True
        )
    desc  = "\n".join(f"{E.ARROW_BLUE} `{i+1}.` {w}" for i, w in enumerate(lista))
    embed = discord.Embed(title=f"{E.WARN_IC} Avisos de {membro.display_name}", description=desc, color=Colors.MAIN)
    embed.set_thumbnail(url=membro.display_avatar.url)
    embed.set_footer(text=f"Total: {len(lista)} aviso(s)")
    embed.timestamp = discord.utils.utcnow()
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="clearwarns", description="Limpar todos os avisos de um membro")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(membro="Membro cujos avisos serão removidos")
async def clearwarns(interaction: discord.Interaction, membro: discord.Member):
    _warns.pop(membro.id, None)
    await interaction.response.send_message(
        embed=success_embed("Avisos removidos", f"{E.ARROW_GREEN} Todos os avisos de {membro.mention} foram removidos."),
        ephemeral=True,
    )

# ==================================================
# ============= STATUS ROTATIVO ===================
# ==================================================

_STATUS_LIST = [
    "☕️ | bebendo um cafezinho",
    "📖 | lendo romance",
    "✨️ | me adicione!",
    "🌙 | vivendo por aí",
    "🍳 | comendo cuscuz com ovo",
    "✂️ | indo arrumar o cabelo",
    "🎵 | ouvindo música no fone",
    "💤 | descansando na segunda",
    "🌿 | tomando um ar fresco",
    "🎮 | jogando Mine",
]

_cycle_status = itertools.cycle(_STATUS_LIST)

@tasks.loop(seconds=30)
async def rotate_status():
    status_text = next(_cycle_status)
    await bot.change_presence(
        activity=discord.CustomActivity(name=status_text),
        status=discord.Status.online,
    )

@rotate_status.before_loop
async def before_rotate():
    await bot.wait_until_ready()

# ==================================================
# =================== ENTRY =======================
# ==================================================

if __name__ == "__main__":
    bot.run(TOKEN)
