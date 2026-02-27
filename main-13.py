import asyncio
import itertools
import logging
import os
import random
from collections import defaultdict
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
    HEART      = "<a:1000006091:1475984862140825833>"
    STAR       = "<a:1000006093:1475982082709655714>"
    LOADING    = "<a:1000006103:1475984937835565227>"
    DECO_BOX   = "<a:1000006120:1475985083818053642>"
    ENVELOPE   = "<a:1000006121:1475984619638620221>"
    MASCOT     = "<:1000006124:1475984717751783617>"
    SYMBOL     = "<:1000006128:1475984311030251722>"
    LEAF       = "<:1000006129:1475984352696471623>"
    SNOWFLAKE  = "<:1000006130:1475984405339045981>"
    DIAMOND    = "<:1000006131:1475984449656324311>"
    FLAME_ORG  = "<:1000006132:1475984492161273967>"
    SPIRAL     = "<:1000006133:1475984534192394354>"
    FLAME_PUR  = "<:1000006134:1475984576819237080>"
    DECO_PINK  = "<a:1000006138:1475984121653235866>"
    CROWN_PINK = "<a:1000006139:1475984068251226245>"
    CHIBI      = "<:1000006140:1475984183246585979>"
    RING       = "<a:1000006151:1475983991352852714>"
    ORB_GREEN  = "<a:1000006152:1475983799568433355>"
    ORB_DARK   = "<a:1000006157:1475983848838795528>"
    TROPHY     = "<a:1000006179:1475983063581331569>"
    ALERT      = "<:1000006181:1475983204577054880>"
    PEN        = "<:1000006182:1475983151712174290>"
    CALENDAR   = "<:1000006183:1475983251414847704>"
    LINK       = "<:1000006184:1475983337645674528>"
    BULB       = "<a:1000006186:1475983407287631984>"
    GEM        = "<a:1000006188:1475983501487771819>"
    HAT        = "<a:1000006193:1475982817195331787>"
    DISCORD    = "<a:1000006197:1475982907612070000>"
    GEM_SHINE  = "<a:1000006229:1475982680012230787>"
    N1         = "<:1000006244:1475982552488607815>"
    N2         = "<:1000006242:1475982573846139001>"
    N3         = "<:1000006239:1475982464928452678>"
    N4         = "<:1000006240:1475982529243643967>"
    N5         = "<:1000006247:1475982600463187990>"
    N6         = "<:1000006236:1475982635384836126>"
    LINE1      = "<:Z24_WG:1451041436077391943>"
    LINE2      = "<:AZ_8white:1444502142898540545>"
    RULES      = "<:regras:1444711583669551358>"
    PIN        = "<:w_p:1445474432893063299>"
    ANNOUNCE   = "<:branxo:1445594793508864211>"
    CHAT       = "<:util_chat:1448790192033890429>"
    HEARTS_S   = "<a:1503hearts:1430339028720549908>"
    SPARKLE    = "<a:1812purple:1430339025520164974>"
    VERIFY     = "<a:8111discordverifypurple:1430269168908894369>"
    ARROW      = "<a:73288animatedarrowpurple:1430339013276991528>"
    ARROW_W    = "<a:51047animatedarrowwhite:1430338988765347850>"
    FIRE       = "<a:5997purplefire:1430338774835003513>"
    WARN_IC    = "<a:i_exclamation:1446591025622679644>"
    SPOTIFY    = "<:1000006554:1476373945673580836>"
    YOUTUBE    = "<:1000006556:1476374025948369010>"
    # ── Aliases usados no resto do código ─────────
    INFO_IC    = SYMBOL
    SETTINGS   = SNOWFLAKE
    STAFF      = CALENDAR
    BRANCORE   = ANNOUNCE
    BRANXO     = ANNOUNCE
    ARROW_BLUE   = ARROW
    ARROW_GREEN  = ARROW_W
    ARROW_RED    = WARN_IC
    ARROW_ORANGE = ARROW
    ARROW_YELLOW = ARROW_W
    DIAMOND      = GEM

# ==================================================
# ----------- SISTEMA DE XP (dados globais) --------
# ==================================================
# Estrutura: _xp_data[guild_id][user_id] = {"xp": int, "level": int}
_xp_data: dict[int, dict[int, dict]] = defaultdict(lambda: defaultdict(lambda: {"xp": 0, "level": 0}))

# Cooldown de XP: evita farm por mensagem (1 msg/min por usuário por guild)
_xp_cooldown: dict[tuple[int, int], float] = {}

# Configurações de XP por servidor (admin pode editar via /xp-config)
# Estrutura: _xp_config[guild_id] = {"xp_canal": int|None, "max_level": int, "cargo_nivel": {level: role_id}, ...}
_xp_config: dict[int, dict] = defaultdict(lambda: {
    "xp_canal":     None,      # canal onde anuncia subida de nível (None = canal da mensagem)
    "max_level":    100,       # nível máximo configurável pelo admin
    "cargo_nivel":  {},        # {level: role_id} cargos automáticos ao subir de nível
    "xp_ativo":     True,      # liga/desliga o sistema de XP no servidor
    "embed_cor":    Colors.MAIN,  # cor da embed de anúncio de nível
    "embed_banner": None,         # banner/imagem da embed de nível
    "embed_titulo": None,         # título personalizado (None = padrão)
    "embed_rodape": None,         # rodapé personalizado (None = padrão)
})

def _xp_para_nivel(level: int) -> int:
    """Retorna o XP total necessário para atingir determinado nível."""
    return 1000 + (level * 500)

def _xp_total_acumulado(level: int) -> int:
    """Retorna o XP acumulado até atingir o nível informado."""
    total = 0
    for lv in range(level):
        total += _xp_para_nivel(lv)
    return total

def _level_bar(xp_atual: int, xp_necessario: int, tamanho: int = 10) -> str:
    """Barra de progresso de XP com emojis."""
    progresso = min(int((xp_atual / xp_necessario) * tamanho), tamanho)
    cheio  = "█"
    vazio  = "░"
    return cheio * progresso + vazio * (tamanho - progresso)

# ==================================================
# ----------- DADOS DE BOAS-VINDAS ----------------
# ==================================================
# _welcome_config[guild_id] = {"canal": int|None, "mensagem": str|None, "banner": str|None, "dm": bool, "cor": int, "titulo": str|None, "rodape": str|None}
_welcome_config: dict[int, dict] = defaultdict(lambda: {
    "canal":    None,
    "mensagem": None,
    "banner":   None,
    "dm":       False,
    "cor":      Colors.MAIN,   # Cor da embed de boas-vindas
    "titulo":   None,           # Título personalizado da embed
    "rodape":   None,           # Rodapé personalizado
})

# ==================================================
# ------------------- BOT -------------------------
# ==================================================

class ModBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.log_channel_id:        int | None = None
        self.ticket_category_id:    int | None = None
        self.staff_role_id:         int | None = None          # cargo principal (legado)
        self.staff_role_ids:        list[int]  = []            # lista com até 5 cargos de staff
        self.ticket_log_channel_id: int | None = None
        self.open_tickets: dict[int, int] = {}
        self.ticket_banner_url:     str | None = None
        self.ticket_atendentes: dict[int, int] = {}

    async def setup_hook(self):
        synced = await self.tree.sync()
        log.info(f"Slash commands sincronizados globalmente: {len(synced)} comando(s).")

    async def on_ready(self):
        log.info(f"Bot online como {self.user} (ID: {self.user.id})")
        # Re-registra as Views persistentes para que funcionem após reinicialização
        self.add_view(TicketSelectView())
        self.add_view(TicketMainView(opener_id=0))
        self.add_view(TicketCloseView(opener_id=0))
        if not rotate_status.is_running():
            rotate_status.start()

    async def on_guild_join(self, guild: discord.Guild):
        try:
            await self.tree.sync()
            log.info(f"Sync forçado ao entrar em: {guild.name} ({guild.id})")
        except discord.HTTPException as e:
            log.warning(f"Falha no sync ao entrar em {guild.name}: {e}")

    # ── Boas-vindas ──────────────────────────────
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        cfg   = _welcome_config[guild.id]

        # ── Mensagem no canal configurado ──
        canal_id = cfg.get("canal")
        canal    = guild.get_channel(canal_id) if canal_id else None

        msg_template = cfg.get("mensagem") or (
            f"{E.CROWN_PINK} Seja muito bem-vindo(a), **{{nome}}**!\n\n"
            f"{E.SPARKLE} Você é o **{{count}}°** membro do servidor.\n"
            f"{E.ARROW} Leia as regras e aproveite bastante! {E.HEARTS_S}"
        )

        msg_final = (
            msg_template
            .replace("{nome}", member.display_name)
            .replace("{mencao}", member.mention)
            .replace("{servidor}", guild.name)
            .replace("{count}", str(guild.member_count))
        )

        titulo_cfg = cfg.get("titulo") or f"{E.RING} Novo membro chegou! {E.DECO_PINK}"
        rodape_cfg = cfg.get("rodape") or f"{guild.name} • Bem-vindo(a)!"
        cor_cfg    = cfg.get("cor", Colors.MAIN)

        embed = discord.Embed(
            title=titulo_cfg,
            description=msg_final,
            color=cor_cfg,
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=rodape_cfg)
        embed.timestamp = discord.utils.utcnow()

        banner = cfg.get("banner")
        if banner:
            embed.set_image(url=banner)

        if canal and isinstance(canal, discord.TextChannel):
            try:
                await canal.send(content=member.mention, embed=embed)
            except discord.HTTPException:
                pass

        # ── DM de boas-vindas (se ativado) ──
        if cfg.get("dm"):
            dm_embed = discord.Embed(
                title=f"{E.HEART} Olá, {member.display_name}!",
                description=(
                    f"{E.SPARKLE} Você acabou de entrar em **{guild.name}**!\n\n"
                    f"{E.ARROW} Leia as regras do servidor para não perder nada.\n"
                    f"{E.HEARTS_S} Esperamos que você curta muito por aqui!"
                ),
                color=Colors.MAIN,
            )
            dm_embed.set_thumbnail(url=guild.icon.url if guild.icon else member.display_avatar.url)
            dm_embed.timestamp = discord.utils.utcnow()
            try:
                await member.send(embed=dm_embed)
            except (discord.Forbidden, discord.HTTPException):
                pass

    # ── Sistema de XP por mensagem ───────────────
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        guild_id  = message.guild.id
        user_id   = message.author.id
        cfg       = _xp_config[guild_id]

        if not cfg.get("xp_ativo", True):
            return

        import time as _time
        agora     = _time.time()
        cooldown_key = (guild_id, user_id)

        # Cooldown de 60 segundos entre ganhos de XP
        if agora - _xp_cooldown.get(cooldown_key, 0) < 60:
            return

        _xp_cooldown[cooldown_key] = agora

        # XP aleatório entre 15 e 40 por mensagem
        xp_ganho  = random.randint(15, 40)
        dados     = _xp_data[guild_id][user_id]
        max_level = cfg.get("max_level", 100)

        dados["xp"] += xp_ganho
        xp_necessario = _xp_para_nivel(dados["level"])

        # Verifica se sobe de nível
        while dados["xp"] >= xp_necessario and dados["level"] < max_level:
            dados["xp"]   -= xp_necessario
            dados["level"] += 1
            novo_nivel     = dados["level"]
            xp_necessario  = _xp_para_nivel(novo_nivel)

            # Cargo automático por nível
            cargo_map = cfg.get("cargo_nivel", {})
            if novo_nivel in cargo_map:
                role = message.guild.get_role(cargo_map[novo_nivel])
                if role:
                    try:
                        await message.author.add_roles(role, reason=f"Subiu para o nível {novo_nivel}")
                    except discord.HTTPException:
                        pass

            # Anúncio de subida de nível
            canal_xp_id = cfg.get("xp_canal")
            canal_xp    = message.guild.get_channel(canal_xp_id) if canal_xp_id else message.channel

            if isinstance(canal_xp, discord.TextChannel):
                titulo_xp  = cfg.get("embed_titulo") or f"{E.TROPHY} Nível Alcançado!"
                rodape_xp  = cfg.get("embed_rodape") or f"XP necessário para o próximo nível: {_xp_para_nivel(novo_nivel):,}"
                cor_xp     = cfg.get("embed_cor", Colors.MAIN)
                embed = discord.Embed(
                    title=titulo_xp,
                    description=(
                        f"{E.CROWN_PINK} {message.author.mention} subiu para o **Nível {novo_nivel}**!\n\n"
                        f"{E.STAR} Continue conversando para subir ainda mais! {E.SPARKLE}"
                    ),
                    color=cor_xp,
                )
                embed.set_thumbnail(url=message.author.display_avatar.url)
                embed.set_footer(text=rodape_xp)
                banner_xp = cfg.get("embed_banner")
                if banner_xp:
                    embed.set_image(url=banner_xp)
                embed.timestamp = discord.utils.utcnow()
                try:
                    await canal_xp.send(embed=embed)
                except discord.HTTPException:
                    pass

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
# ============= SISTEMA DE BOAS-VINDAS (ADMIN) =====
# ==================================================

# ── Modal para editar o embed de boas-vindas ──────────────────────────────────
class BoasVindasEmbedModal(Modal, title="Editar Embed de Boas-vindas"):
    titulo_embed = TextInput(
        label="Título da embed",
        placeholder="Ex: Bem-vindo ao servidor!",
        required=False,
        max_length=256,
    )
    descricao_embed = TextInput(
        label="Mensagem / Descrição",
        placeholder="Use {nome}, {mencao}, {servidor}, {count}",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=2000,
    )
    cor_embed = TextInput(
        label="Cor hex da embed (ex: #590CEA)",
        placeholder="#590CEA",
        required=False,
        max_length=7,
    )
    rodape_embed = TextInput(
        label="Rodapé da embed",
        placeholder="Ex: Seja bem-vindo(a)!",
        required=False,
        max_length=256,
    )
    banner_embed = TextInput(
        label="URL do banner/imagem",
        placeholder="https://i.imgur.com/exemplo.png",
        required=False,
        max_length=512,
    )

    def __init__(self, guild_id: int):
        super().__init__()
        self.guild_id = guild_id
        cfg = _welcome_config[guild_id]
        if cfg.get("titulo"):
            self.titulo_embed.default = cfg["titulo"]
        if cfg.get("mensagem"):
            self.descricao_embed.default = cfg["mensagem"][:2000]
        cor = cfg.get("cor", Colors.MAIN)
        self.cor_embed.default = f"#{cor:06X}"
        if cfg.get("rodape"):
            self.rodape_embed.default = cfg["rodape"]
        if cfg.get("banner"):
            self.banner_embed.default = cfg["banner"]

    async def on_submit(self, interaction: discord.Interaction):
        cfg = _welcome_config[self.guild_id]
        # Cor
        raw_cor = self.cor_embed.value.strip()
        if raw_cor:
            try:
                cfg["cor"] = int(raw_cor.lstrip("#"), 16)
            except ValueError:
                return await interaction.response.send_message(
                    embed=error_embed("Cor inválida", f"Use o formato `#RRGGBB`, ex: `#590CEA`."), ephemeral=True
                )
        if self.titulo_embed.value.strip():
            cfg["titulo"] = self.titulo_embed.value.strip()
        if self.descricao_embed.value.strip():
            cfg["mensagem"] = self.descricao_embed.value.strip()
        if self.rodape_embed.value.strip():
            cfg["rodape"] = self.rodape_embed.value.strip()
        if self.banner_embed.value.strip():
            cfg["banner"] = self.banner_embed.value.strip()

        # Preview
        preview = discord.Embed(
            title=cfg.get("titulo") or f"{E.RING} Novo membro chegou! {E.DECO_PINK}",
            description=(
                (cfg.get("mensagem") or "Mensagem padrão do bot")
                .replace("{nome}", interaction.user.display_name)
                .replace("{mencao}", interaction.user.mention)
                .replace("{servidor}", interaction.guild.name)
                .replace("{count}", str(interaction.guild.member_count))
            ),
            color=cfg.get("cor", Colors.MAIN),
        )
        preview.set_thumbnail(url=interaction.user.display_avatar.url)
        preview.set_footer(text=cfg.get("rodape") or f"{interaction.guild.name} • Bem-vindo(a)!")
        if cfg.get("banner"):
            preview.set_image(url=cfg["banner"])
        preview.timestamp = discord.utils.utcnow()

        await interaction.response.send_message(
            content=f"{E.VERIFY} **Embed de boas-vindas atualizada!** Veja o preview abaixo:",
            embed=preview,
            ephemeral=True,
        )


class BoasVindasConfigView(View):
    """View principal do /setup-boas-vindas com botões de ação."""
    def __init__(self, autor_id: int, guild_id: int):
        super().__init__(timeout=300)
        self.autor_id = autor_id
        self.guild_id = guild_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.autor_id:
            await interaction.response.send_message(
                f"{E.ARROW_RED} Apenas quem usou o comando pode interagir aqui.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Editar Embed", style=discord.ButtonStyle.primary, emoji="✏️", row=0)
    async def editar_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(BoasVindasEmbedModal(self.guild_id))

    @discord.ui.button(label="Ativar DM", style=discord.ButtonStyle.secondary, emoji="📩", row=0)
    async def toggle_dm(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = _welcome_config[self.guild_id]
        cfg["dm"] = not cfg["dm"]
        status = "ativada" if cfg["dm"] else "desativada"
        button.label = "Desativar DM" if cfg["dm"] else "Ativar DM"
        button.style = discord.ButtonStyle.success if cfg["dm"] else discord.ButtonStyle.secondary
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(
            embed=success_embed("DM de boas-vindas", f"{E.ENVELOPE} DM de boas-vindas **{status}**."),
            ephemeral=True,
        )

    @discord.ui.button(label="Resetar Config", style=discord.ButtonStyle.danger, emoji="🗑️", row=0)
    async def resetar(self, interaction: discord.Interaction, button: discord.ui.Button):
        _welcome_config[self.guild_id] = {
            "canal": _welcome_config[self.guild_id].get("canal"),
            "mensagem": None, "banner": None, "dm": False,
            "cor": Colors.MAIN, "titulo": None, "rodape": None,
        }
        await interaction.response.send_message(
            embed=success_embed("Config resetada", f"{E.LEAF} Embed de boas-vindas restaurada para o padrão."),
            ephemeral=True,
        )

    @discord.ui.button(label="Testar agora", style=discord.ButtonStyle.success, emoji="🚀", row=1)
    async def testar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await bot.on_member_join(interaction.user)
        await interaction.response.send_message(
            embed=success_embed("Teste enviado!", f"{E.SPARKLE} Simulou boas-vindas para {interaction.user.mention}."),
            ephemeral=True,
        )


@bot.tree.command(name="setup-boas-vindas", description="Configura o sistema de boas-vindas do servidor")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    canal="Canal onde as mensagens de boas-vindas serão enviadas",
    mensagem="Mensagem rápida. Use {nome}, {mencao}, {servidor}, {count}",
    banner_url="URL de banner/imagem para o embed (opcional)",
    cor_hex="Cor do embed em hex (ex: #590CEA). Padrão: roxo",
    dm="Enviar DM de boas-vindas ao novo membro",
)
async def setup_boas_vindas(
    interaction: discord.Interaction,
    canal: discord.TextChannel,
    mensagem: str | None = None,
    banner_url: str | None = None,
    cor_hex: str | None = None,
    dm: bool = False,
):
    cfg = _welcome_config[interaction.guild.id]
    cfg["canal"]    = canal.id
    if mensagem:   cfg["mensagem"] = mensagem
    if banner_url: cfg["banner"]   = banner_url
    cfg["dm"]       = dm

    # Aplica cor se fornecida
    if cor_hex:
        try:
            cfg["cor"] = int(cor_hex.lstrip("#"), 16)
        except ValueError:
            return await interaction.response.send_message(
                embed=error_embed("Cor inválida", "Use o formato `#RRGGBB`, ex: `#590CEA`."), ephemeral=True
            )

    cor_atual = cfg.get("cor", Colors.MAIN)
    embed = success_embed(
        "Boas-vindas configuradas!",
        f"{E.RING} **Canal:** {canal.mention}\n"
        f"{E.CHAT} **Mensagem:** {'Personalizada' if cfg.get('mensagem') else 'Padrão'}\n"
        f"{E.GEM} **Banner:** {'Configurado' if cfg.get('banner') else 'Sem banner'}\n"
        f"{E.ENVELOPE} **DM ao entrar:** {'Ativado' if dm else 'Desativado'}\n"
        f"{E.SPARKLE} **Cor embed:** `#{cor_atual:06X}`\n\n"
        f"{E.ARROW} Use os botões abaixo para editar a embed completa (cor, título, rodapé, banner)."
    )
    view = BoasVindasConfigView(autor_id=interaction.user.id, guild_id=interaction.guild.id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    log.info(f"Boas-vindas configuradas em {interaction.guild.name}: canal={canal.id}")

@bot.tree.command(name="boas-vindas-testar", description="Testa a mensagem de boas-vindas com você mesmo")
@app_commands.default_permissions(administrator=True)
async def boas_vindas_testar(interaction: discord.Interaction):
    # Simula como se você tivesse entrado agora
    await bot.on_member_join(interaction.user)
    await interaction.response.send_message(
        embed=success_embed("Teste enviado!", f"{E.SPARKLE} A mensagem de boas-vindas foi simulada para {interaction.user.mention}."),
        ephemeral=True,
    )

@bot.tree.command(name="boas-vindas-ver", description="Mostra as configurações atuais de boas-vindas")
@app_commands.default_permissions(manage_guild=True)
async def boas_vindas_ver(interaction: discord.Interaction):
    cfg    = _welcome_config[interaction.guild.id]
    canal  = interaction.guild.get_channel(cfg["canal"]) if cfg["canal"] else None
    cor    = cfg.get("cor", Colors.MAIN)
    embed  = discord.Embed(
        title=f"{E.RING} Configurações de Boas-vindas",
        description=(
            f"{E.CHAT} **Canal:** {canal.mention if canal else 'Não configurado'}\n"
            f"{E.PEN} **Título:** {cfg.get('titulo') or 'Padrão'}\n"
            f"{E.PEN} **Mensagem:** {'Personalizada' if cfg.get('mensagem') else 'Padrão'}\n"
            f"{E.GEM} **Banner:** {'Configurado' if cfg.get('banner') else 'Nenhum'}\n"
            f"{E.SPARKLE} **Cor embed:** `#{cor:06X}`\n"
            f"{E.ENVELOPE} **DM:** {'Ativado' if cfg.get('dm') else 'Desativado'}"
        ),
        color=cor,
    )
    embed.set_footer(text=interaction.guild.name)
    embed.timestamp = discord.utils.utcnow()
    view = BoasVindasConfigView(autor_id=interaction.user.id, guild_id=interaction.guild.id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# ==================================================
# ============= SISTEMA DE XP (ADMIN) ==============
# ==================================================

# ── Modal para editar o embed de anúncio de nível ──────────────────────────────
class XPEmbedModal(Modal, title="Editar Embed de Nível"):
    titulo_embed = TextInput(
        label="Título da embed",
        placeholder="Ex: 🏆 Nível Alcançado!",
        required=False,
        max_length=256,
    )
    cor_embed = TextInput(
        label="Cor hex da embed (ex: #590CEA)",
        placeholder="#590CEA",
        required=False,
        max_length=7,
    )
    rodape_embed = TextInput(
        label="Rodapé personalizado",
        placeholder="Deixe em branco para usar o padrão",
        required=False,
        max_length=256,
    )
    banner_embed = TextInput(
        label="URL de banner/imagem da embed",
        placeholder="https://i.imgur.com/exemplo.png",
        required=False,
        max_length=512,
    )

    def __init__(self, guild_id: int):
        super().__init__()
        self.guild_id = guild_id
        cfg = _xp_config[guild_id]
        cor = cfg.get("embed_cor", Colors.MAIN)
        self.cor_embed.default = f"#{cor:06X}"
        if cfg.get("embed_titulo"):
            self.titulo_embed.default = cfg["embed_titulo"]
        if cfg.get("embed_rodape"):
            self.rodape_embed.default = cfg["embed_rodape"]
        if cfg.get("embed_banner"):
            self.banner_embed.default = cfg["embed_banner"]

    async def on_submit(self, interaction: discord.Interaction):
        cfg = _xp_config[self.guild_id]
        raw_cor = self.cor_embed.value.strip()
        if raw_cor:
            try:
                cfg["embed_cor"] = int(raw_cor.lstrip("#"), 16)
            except ValueError:
                return await interaction.response.send_message(
                    embed=error_embed("Cor inválida", "Use o formato `#RRGGBB`, ex: `#590CEA`."), ephemeral=True
                )
        if self.titulo_embed.value.strip():
            cfg["embed_titulo"] = self.titulo_embed.value.strip()
        if self.rodape_embed.value.strip():
            cfg["embed_rodape"] = self.rodape_embed.value.strip()
        if self.banner_embed.value.strip():
            cfg["embed_banner"] = self.banner_embed.value.strip()

        # Preview
        cor = cfg.get("embed_cor", Colors.MAIN)
        preview = discord.Embed(
            title=cfg.get("embed_titulo") or f"{E.TROPHY} Nível Alcançado!",
            description=(
                f"{E.CROWN_PINK} {interaction.user.mention} subiu para o **Nível 5**!\n\n"
                f"{E.STAR} Continue conversando para subir ainda mais! {E.SPARKLE}"
            ),
            color=cor,
        )
        preview.set_thumbnail(url=interaction.user.display_avatar.url)
        preview.set_footer(text=cfg.get("embed_rodape") or "XP necessário para o próximo nível: 3.500")
        if cfg.get("embed_banner"):
            preview.set_image(url=cfg["embed_banner"])
        preview.timestamp = discord.utils.utcnow()

        await interaction.response.send_message(
            content=f"{E.VERIFY} **Embed de XP atualizada!** Preview:",
            embed=preview,
            ephemeral=True,
        )


class XPConfigView(View):
    """View do /xp-config com botões avançados."""
    def __init__(self, autor_id: int, guild_id: int):
        super().__init__(timeout=300)
        self.autor_id = autor_id
        self.guild_id = guild_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.autor_id:
            await interaction.response.send_message(
                f"{E.ARROW_RED} Apenas quem usou o comando pode interagir aqui.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Editar Embed de Nível", style=discord.ButtonStyle.primary, emoji="✏️", row=0)
    async def editar_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(XPEmbedModal(self.guild_id))

    @discord.ui.button(label="Desativar XP", style=discord.ButtonStyle.secondary, emoji="⏸️", row=0)
    async def toggle_xp(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = _xp_config[self.guild_id]
        cfg["xp_ativo"] = not cfg["xp_ativo"]
        status = "ativado" if cfg["xp_ativo"] else "desativado"
        button.label = "Desativar XP" if cfg["xp_ativo"] else "Ativar XP"
        button.style = discord.ButtonStyle.secondary if cfg["xp_ativo"] else discord.ButtonStyle.success
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(
            embed=success_embed("Sistema de XP", f"{E.ORB_GREEN} Sistema de XP **{status}** neste servidor."),
            ephemeral=True,
        )

    @discord.ui.button(label="Ver Cargos de Nível", style=discord.ButtonStyle.secondary, emoji="🏅", row=0)
    async def ver_cargos(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = _xp_config[self.guild_id]
        cargo_map = cfg.get("cargo_nivel", {})
        if not cargo_map:
            return await interaction.response.send_message(
                embed=error_embed("Sem cargos", "Nenhum cargo de nível configurado. Use `/xp-cargo-nivel` para adicionar."),
                ephemeral=True,
            )
        linhas = []
        for lv in sorted(cargo_map.keys()):
            role = interaction.guild.get_role(cargo_map[lv])
            linhas.append(f"{E.CROWN_PINK} Nível **{lv}** → {role.mention if role else f'`ID:{cargo_map[lv]}`'}")
        embed = discord.Embed(
            title=f"{E.TROPHY} Cargos automáticos por nível",
            description="\n".join(linhas),
            color=cfg.get("embed_cor", Colors.MAIN),
        )
        embed.set_footer(text=f"{interaction.guild.name} • Use /xp-cargo-nivel para editar")
        embed.timestamp = discord.utils.utcnow()
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Resetar Embed", style=discord.ButtonStyle.danger, emoji="🗑️", row=1)
    async def resetar_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = _xp_config[self.guild_id]
        cfg["embed_cor"]    = Colors.MAIN
        cfg["embed_banner"] = None
        cfg["embed_titulo"] = None
        cfg["embed_rodape"] = None
        await interaction.response.send_message(
            embed=success_embed("Embed resetada", f"{E.LEAF} Embed de nível restaurada para o padrão."),
            ephemeral=True,
        )


@bot.tree.command(name="xp-config", description="Configura o sistema de XP do servidor")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    canal_nivel="Canal onde serão anunciadas as subidas de nível (opcional)",
    nivel_maximo="Nível máximo atingível (padrão: 100, máx: 1000)",
    ativo="Ativar ou desativar o sistema de XP neste servidor",
    cor_hex="Cor da embed de anúncio de nível (ex: #590CEA)",
    banner_url="URL de banner/imagem da embed de nível",
)
async def xp_config(
    interaction: discord.Interaction,
    canal_nivel: discord.TextChannel | None = None,
    nivel_maximo: app_commands.Range[int, 1, 1000] = 100,
    ativo: bool = True,
    cor_hex: str | None = None,
    banner_url: str | None = None,
):
    cfg = _xp_config[interaction.guild.id]
    cfg["xp_canal"]  = canal_nivel.id if canal_nivel else None
    cfg["max_level"] = nivel_maximo
    cfg["xp_ativo"]  = ativo
    if banner_url:
        cfg["embed_banner"] = banner_url
    if cor_hex:
        try:
            cfg["embed_cor"] = int(cor_hex.lstrip("#"), 16)
        except ValueError:
            return await interaction.response.send_message(
                embed=error_embed("Cor inválida", "Use o formato `#RRGGBB`, ex: `#590CEA`."), ephemeral=True
            )

    cor = cfg.get("embed_cor", Colors.MAIN)
    embed = success_embed(
        "XP configurado!",
        f"{E.TROPHY} **Canal de nível:** {canal_nivel.mention if canal_nivel else 'Canal da mensagem'}\n"
        f"{E.STAR} **Nível máximo:** `{nivel_maximo}`\n"
        f"{E.ORB_GREEN} **Sistema ativo:** {'Sim' if ativo else 'Não'}\n"
        f"{E.SPARKLE} **Cor embed:** `#{cor:06X}`\n"
        f"{E.GEM} **Banner:** {'Configurado' if cfg.get('embed_banner') else 'Nenhum'}\n\n"
        f"{E.ARROW} XP por mensagem: `15–40` (cooldown de 1 minuto)\n"
        f"{E.ARROW} Use **Editar Embed de Nível** abaixo para customizar título, cor, banner e rodapé."
    )
    view = XPConfigView(autor_id=interaction.user.id, guild_id=interaction.guild.id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


@bot.tree.command(name="xp-cargo-nivel", description="Define um cargo automático para um nível específico")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(nivel="Nível em que o cargo será concedido", cargo="Cargo a ser dado automaticamente")
async def xp_cargo_nivel(interaction: discord.Interaction, nivel: app_commands.Range[int, 1, 1000], cargo: discord.Role):
    cfg = _xp_config[interaction.guild.id]
    cfg["cargo_nivel"][nivel] = cargo.id
    embed = success_embed(
        "Cargo de nível configurado!",
        f"{E.CROWN_PINK} Ao atingir o **nível {nivel}**, o membro receberá o cargo {cargo.mention} automaticamente."
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="xp-cargo-nivel-remover", description="Remove o cargo automático de um nível")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(nivel="Nível do qual remover o cargo")
async def xp_cargo_nivel_remover(interaction: discord.Interaction, nivel: app_commands.Range[int, 1, 1000]):
    cfg = _xp_config[interaction.guild.id]
    removido = cfg["cargo_nivel"].pop(nivel, None)
    if removido:
        await interaction.response.send_message(embed=success_embed("Removido", f"Cargo do nível {nivel} removido."), ephemeral=True)
    else:
        await interaction.response.send_message(embed=error_embed("Não encontrado", f"Não há cargo configurado para o nível {nivel}."), ephemeral=True)

@bot.tree.command(name="xp-dar", description="Dá XP manualmente a um membro")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(membro="Membro que receberá o XP", quantidade="Quantidade de XP a dar")
async def xp_dar(interaction: discord.Interaction, membro: discord.Member, quantidade: app_commands.Range[int, 1, 100000]):
    dados = _xp_data[interaction.guild.id][membro.id]
    dados["xp"] += quantidade
    xp_nec = _xp_para_nivel(dados["level"])
    while dados["xp"] >= xp_nec and dados["level"] < _xp_config[interaction.guild.id].get("max_level", 100):
        dados["xp"]   -= xp_nec
        dados["level"] += 1
        xp_nec = _xp_para_nivel(dados["level"])
    embed = success_embed(
        "XP adicionado!",
        f"{E.STAR} {membro.mention} recebeu `{quantidade:,}` XP.\n"
        f"{E.TROPHY} Nível atual: **{dados['level']}** | XP: `{dados['xp']:,}`/`{xp_nec:,}`"
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="xp-remover", description="Remove XP de um membro")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(membro="Membro", quantidade="Quantidade de XP a remover")
async def xp_remover(interaction: discord.Interaction, membro: discord.Member, quantidade: app_commands.Range[int, 1, 100000]):
    dados = _xp_data[interaction.guild.id][membro.id]
    dados["xp"] = max(0, dados["xp"] - quantidade)
    xp_nec = _xp_para_nivel(dados["level"])
    embed = success_embed(
        "XP removido!",
        f"{E.WARN_IC} `{quantidade:,}` XP removidos de {membro.mention}.\n"
        f"{E.TROPHY} Nível atual: **{dados['level']}** | XP: `{dados['xp']:,}`/`{xp_nec:,}`"
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="xp-reset", description="Reseta todo o XP de um membro")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(membro="Membro a ter o XP zerado")
async def xp_reset(interaction: discord.Interaction, membro: discord.Member):
    _xp_data[interaction.guild.id][membro.id] = {"xp": 0, "level": 0}
    await interaction.response.send_message(
        embed=success_embed("XP resetado", f"{E.LEAF} O XP de {membro.mention} foi zerado."), ephemeral=True
    )

# ==================================================
# ============= XP (COMANDOS PÚBLICOS) =============
# ==================================================

@bot.tree.command(name="rank", description="Veja seu nível e XP atual (ou de outro membro)")
@app_commands.describe(membro="Membro a consultar (padrão: você mesmo)")
async def rank(interaction: discord.Interaction, membro: discord.Member | None = None):
    membro = membro or interaction.user
    dados  = _xp_data[interaction.guild.id][membro.id]
    level  = dados["level"]
    xp     = dados["xp"]
    xp_nec = _xp_para_nivel(level)
    cfg    = _xp_config[interaction.guild.id]
    max_lv = cfg.get("max_level", 100)
    barra  = _level_bar(xp, xp_nec)

    # Ranking no servidor
    ranking = sorted(
        _xp_data[interaction.guild.id].items(),
        key=lambda x: (_xp_total_acumulado(x[1]["level"]) + x[1]["xp"]),
        reverse=True,
    )
    posicao = next((i + 1 for i, (uid, _) in enumerate(ranking) if uid == membro.id), "?")

    embed = discord.Embed(
        title=f"{E.TROPHY} Rank de {membro.display_name}",
        color=Colors.MAIN,
    )
    embed.set_thumbnail(url=membro.display_avatar.url)
    embed.add_field(name=f"{E.STAR} Nível",   value=f"`{level}` / `{max_lv}`",     inline=True)
    embed.add_field(name=f"{E.GEM} XP",        value=f"`{xp:,}` / `{xp_nec:,}`", inline=True)
    embed.add_field(name=f"{E.N1} Posição",    value=f"`#{posicao}`",              inline=True)
    embed.add_field(
        name=f"{E.ORB_GREEN} Progresso",
        value=f"`{barra}` `{int(xp/xp_nec*100)}%`",
        inline=False,
    )
    if level >= max_lv:
        embed.add_field(name=f"{E.CROWN_PINK} Status", value="Nível máximo atingido!", inline=False)
    embed.set_footer(text=f"{interaction.guild.name} • XP por mensagem: 15–40 (cooldown 60s)")
    embed.timestamp = discord.utils.utcnow()
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="top", description="Ranking dos membros com mais XP no servidor")
async def top(interaction: discord.Interaction):
    await interaction.response.defer()
    ranking = sorted(
        _xp_data[interaction.guild.id].items(),
        key=lambda x: (_xp_total_acumulado(x[1]["level"]) + x[1]["xp"]),
        reverse=True,
    )[:10]

    if not ranking:
        return await interaction.followup.send(
            embed=error_embed("Sem dados", "Nenhum membro tem XP registrado ainda.")
        )

    medalhas = [E.N1, E.N2, E.N3, E.N4, E.N5, E.N6, "7️⃣", "8️⃣", "9️⃣", "🔟"]
    linhas   = []
    for i, (uid, dados) in enumerate(ranking):
        membro = interaction.guild.get_member(uid)
        nome   = membro.display_name if membro else f"(usuário {uid})"
        medal  = medalhas[i] if i < len(medalhas) else f"`{i+1}.`"
        linhas.append(
            f"{medal} **{nome}** — Nível `{dados['level']}` · `{dados['xp']:,}` XP"
        )

    embed = discord.Embed(
        title=f"{E.TROPHY} Top 10 — {interaction.guild.name}",
        description="\n".join(linhas),
        color=Colors.MAIN,
    )
    embed.set_footer(text="Ranking atualizado em tempo real")
    embed.timestamp = discord.utils.utcnow()
    await interaction.followup.send(embed=embed)

# ==================================================
# ============= COMANDOS DE INTERAÇÃO ==============
# ==================================================

# ── Mapeamento de ação → categoria na API nekos.best ─────────────────────────
# A API https://nekos.best/api/v2/{categoria} retorna GIFs de anime reais,
# hospedados no próprio servidor deles — sem bloqueio de hotlink.
_NEKOS_CAT: dict[str, str] = {
    "kiss":     "kiss",
    "hug":      "hug",
    "pat":      "pat",
    "slap":     "slap",
    "poke":     "poke",
    "bite":     "bite",
    "cry":      "cry",
    "blush":    "blush",
    "dance":    "dance",
    "highfive": "highfive",
    "wave":     "wave",
    "cuddle":   "cuddle",
    "nuzzle":   "nuzzle",
    "lick":     "lick",
    "yeet":     "yeet",
}

async def _get_gif(action: str) -> str:
    """Busca um GIF aleatório de anime via API nekos.best. Retorna a URL do GIF."""
    import aiohttp
    cat = _NEKOS_CAT.get(action, "hug")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://nekos.best/api/v2/{cat}",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["results"][0]["url"]
    except Exception:
        pass
    # Fallback: GIFs estáticos confiáveis do nekos.best caso a API falhe
    _FALLBACK = {
        "kiss":   "https://nekos.best/api/v2/kiss/0001.gif",
        "hug":    "https://nekos.best/api/v2/hug/0001.gif",
        "pat":    "https://nekos.best/api/v2/pat/0001.gif",
        "slap":   "https://nekos.best/api/v2/slap/0001.gif",
        "poke":   "https://nekos.best/api/v2/poke/0001.gif",
        "bite":   "https://nekos.best/api/v2/bite/0001.gif",
        "cry":    "https://nekos.best/api/v2/cry/0001.gif",
        "blush":  "https://nekos.best/api/v2/blush/0001.gif",
        "dance":  "https://nekos.best/api/v2/dance/0001.gif",
        "wave":   "https://nekos.best/api/v2/wave/0001.gif",
        "cuddle": "https://nekos.best/api/v2/cuddle/0001.gif",
        "nuzzle": "https://nekos.best/api/v2/nuzzle/0001.gif",
        "lick":   "https://nekos.best/api/v2/lick/0001.gif",
    }
    return _FALLBACK.get(action, _FALLBACK["hug"])

# ── Dados de cada ação: frases, emoji, retribuição ─
_ACOES: dict[str, dict] = {
    "kiss":     {"emoji": E.HEARTS_S, "emoji2": E.HEART,      "retribuir": True,
                 "frases": ["{a} beijou {b}!", "{a} deu um beijo em {b}!", "{a} não resistiu e beijou {b}!",
                             "{a} surpreendeu {b} com um beijinho!"],
                 "frase_retribuir": "{b} retribuiu o beijo de {a}!"},
    "hug":      {"emoji": E.RING,     "emoji2": E.HEARTS_S,   "retribuir": True,
                 "frases": ["{a} abraçou {b}!", "{a} deu um abraço apertado em {b}!",
                             "{a} e {b} se abraçaram!", "{b} ganhou um abraço de {a}!"],
                 "frase_retribuir": "{b} retribuiu o abraço de {a}!"},
    "pat":      {"emoji": E.SPARKLE,  "emoji2": E.CROWN_PINK, "retribuir": True,
                 "frases": ["{a} fez carinho na cabeça de {b}!", "{a} deu um patinho em {b}!",
                             "{b} ganhou um carinho de {a}!"],
                 "frase_retribuir": "{b} deu um pat em {a} de volta!"},
    "slap":     {"emoji": E.WARN_IC,  "emoji2": E.FLAME_ORG,  "retribuir": True,
                 "frases": ["{a} deu um tapa em {b}!", "{b} levou um tapa de {a}!",
                             "{a} esbofeteou {b}!"],
                 "frase_retribuir": "{b} devolveu o tapa em {a}!"},
    "poke":     {"emoji": E.ARROW,    "emoji2": E.SPARKLE,    "retribuir": True,
                 "frases": ["{a} cutucou {b}!", "{b} foi cutucado(a) por {a}!",
                             "{a} ficou perturbando {b} com cutucadas!"],
                 "frase_retribuir": "{b} cutucou {a} de volta!"},
    "bite":     {"emoji": E.FLAME_PUR,"emoji2": E.HEART,      "retribuir": True,
                 "frases": ["{a} mordeu {b}!", "{b} foi mordido(a) por {a}!",
                             "{a} não resistiu e mordeu {b}!"],
                 "frase_retribuir": "{b} mordeu {a} de volta!"},
    "cry":      {"emoji": E.HEARTS_S, "emoji2": E.RING,       "retribuir": False,
                 "frases": ["{a} está consolando {b}!", "{a} foi confortar {b}!"],
                 "frase_solo": "{a} está chorando..."},
    "blush":    {"emoji": E.HEART,    "emoji2": E.SPARKLE,    "retribuir": False,
                 "frases": ["{a} ficou vermelhinho(a) por causa de {b}!", "{b} fez {a} corar!",
                             "{a} corou de vergonha por {b}!"],
                 "frase_solo": "{a} ficou todo(a) vermelho(a)!"},
    "dance":    {"emoji": E.SPARKLE,  "emoji2": E.GEM_SHINE,  "retribuir": True,
                 "frases": ["{a} chamou {b} para dançar!", "{a} e {b} dançando juntos!"],
                 "frase_solo": "{a} está dançando!",
                 "frase_retribuir": "{b} aceitou dançar com {a}!"},
    "highfive": {"emoji": E.ORB_GREEN,"emoji2": E.VERIFY,     "retribuir": True,
                 "frases": ["{a} deu um toca aqui em {b}!", "{a} e {b}: TOCA AQUI!"],
                 "frase_retribuir": "{b} tocou de volta com {a}!"},
    "wave":     {"emoji": E.ARROW_W,  "emoji2": E.HEARTS_S,   "retribuir": False,
                 "frases": ["{a} acenou para {b}!", "Olá {b}! {a} está acenando para você!"],
                 "frase_solo": "{a} acenou para todo mundo!"},
    "cuddle":   {"emoji": E.HEART,    "emoji2": E.RING,       "retribuir": True,
                 "frases": ["{a} se aconchegou com {b}!", "{a} e {b} num momento fofíssimo!",
                             "{b} ganhou um mimo de {a}!"],
                 "frase_retribuir": "{b} se aconchegou com {a} também!"},
    "lick":     {"emoji": E.FLAME_PUR,"emoji2": E.HEARTS_S,   "retribuir": False,
                 "frases": ["{a} lambeu {b}!!", "{b} foi lambido(a) por {a}... que situação!",
                             "{a} lambeu {b} sem aviso nenhum!"],},
    "yeet":     {"emoji": E.FIRE,     "emoji2": E.FLAME_ORG,  "retribuir": False,
                 "frases": ["{a} yeetou {b} pro espaço!", "{b} foi lançado(a) por {a}! YEEEET!",
                             "{a} arremessou {b} sem dó!"],},
    "nuzzle":   {"emoji": E.CROWN_PINK,"emoji2": E.HEART,     "retribuir": True,
                 "frases": ["{a} nuzzlou {b}!", "{a} esfregou o rosto em {b} com carinho!",
                             "{b} ganhou um nuzzle de {a}!"],
                 "frase_retribuir": "{b} retribuiu o nuzzle de {a}!"},
}

# ── View com botão "Retribuir" ─────────────────────
class InteracaoView(View):
    def __init__(self, action: str, autor: discord.Member, alvo: discord.Member):
        super().__init__(timeout=120)
        self.action = action
        self.autor  = autor
        self.alvo   = alvo

    @discord.ui.button(label="Retribuir", style=discord.ButtonStyle.primary, emoji=discord.PartialEmoji.from_str("<a:1503hearts:1430339028720549908>"))
    async def retribuir(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.alvo.id:
            return await interaction.response.send_message(
                f"{E.ARROW_RED} Apenas {self.alvo.mention} pode retribuir essa ação!",
                ephemeral=True,
            )
        dados   = _ACOES[self.action]
        gif     = await _get_gif(self.action)
        frase_r = dados.get("frase_retribuir", f"{self.alvo.display_name} retribuiu!")
        texto   = frase_r.format(a=self.alvo.mention, b=self.autor.mention)

        embed = discord.Embed(
            description=f"{dados['emoji']} {texto} {dados['emoji2']}",
            color=Colors.MAIN,
        )
        embed.set_image(url=gif)
        embed.set_footer(
            text=f"Pedido por {self.alvo.display_name}",
            icon_url=self.alvo.display_avatar.url,
        )
        embed.timestamp = discord.utils.utcnow()

        button.disabled = True
        button.label    = "Retribuído!"
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(content=self.autor.mention, embed=embed)


async def _build_interacao(
    action: str,
    autor: discord.Member,
    alvo: discord.Member | None = None,
    solo: bool = False,
) -> tuple[discord.Embed, View | None]:
    """Monta o embed no estilo Loritta e a view de retribuição."""
    dados = _ACOES[action]
    gif   = await _get_gif(action)

    if solo or alvo is None:
        frase_solo = dados.get("frase_solo", f"{autor.mention}!")
        texto = frase_solo.format(a=autor.mention, b="")
    else:
        texto = random.choice(dados["frases"]).format(a=autor.mention, b=alvo.mention)

    embed = discord.Embed(
        description=f"{dados['emoji']} {texto} {dados['emoji2']}",
        color=Colors.MAIN,
    )
    embed.set_image(url=gif)
    embed.set_footer(
        text=f"Pedido por {autor.display_name}",
        icon_url=autor.display_avatar.url,
    )
    embed.timestamp = discord.utils.utcnow()

    view = None
    if alvo and not solo and dados.get("retribuir"):
        view = InteracaoView(action=action, autor=autor, alvo=alvo)

    return embed, view


# ── /kiss ─────────────────────────────────────────
@bot.tree.command(name="kiss", description="Dê um beijo em alguém")
@app_commands.describe(membro="Quem você quer beijar")
async def kiss(interaction: discord.Interaction, membro: discord.Member):
    if membro.id == interaction.user.id:
        return await interaction.response.send_message(
            embed=error_embed("Eita!", "Você não pode se beijar... pelo menos não aqui!"), ephemeral=True
        )
    await interaction.response.defer()
    embed, view = await _build_interacao("kiss", interaction.user, membro)
    await interaction.followup.send(content=membro.mention, embed=embed, view=view)

# ── /hug ──────────────────────────────────────────
@bot.tree.command(name="hug", description="Dê um abraço em alguém")
@app_commands.describe(membro="Quem você quer abraçar")
async def hug(interaction: discord.Interaction, membro: discord.Member):
    await interaction.response.defer()
    if membro.id == interaction.user.id:
        embed, _ = await _build_interacao("hug", interaction.user, solo=True)
        return await interaction.followup.send(embed=embed)
    embed, view = await _build_interacao("hug", interaction.user, membro)
    await interaction.followup.send(content=membro.mention, embed=embed, view=view)

# ── /pat ──────────────────────────────────────────
@bot.tree.command(name="pat", description="Faça um carinho na cabeça de alguém")
@app_commands.describe(membro="Quem você quer dar um pat")
async def pat(interaction: discord.Interaction, membro: discord.Member):
    await interaction.response.defer()
    embed, view = await _build_interacao("pat", interaction.user, membro)
    await interaction.followup.send(content=membro.mention, embed=embed, view=view)

# ── /slap ─────────────────────────────────────────
@bot.tree.command(name="slap", description="Dê uma tapa em alguém (de brincadeira!)")
@app_commands.describe(membro="Quem vai levar o tapa")
async def slap(interaction: discord.Interaction, membro: discord.Member):
    if membro.id == interaction.user.id:
        return await interaction.response.send_message(
            embed=error_embed("Ei!", "Você não vai se tapar..."), ephemeral=True
        )
    await interaction.response.defer()
    embed, view = await _build_interacao("slap", interaction.user, membro)
    await interaction.followup.send(content=membro.mention, embed=embed, view=view)

# ── /poke ─────────────────────────────────────────
@bot.tree.command(name="poke", description="Cutuque alguém")
@app_commands.describe(membro="Quem vai ser cutucado")
async def poke(interaction: discord.Interaction, membro: discord.Member):
    await interaction.response.defer()
    embed, view = await _build_interacao("poke", interaction.user, membro)
    await interaction.followup.send(content=membro.mention, embed=embed, view=view)

# ── /bite ─────────────────────────────────────────
@bot.tree.command(name="bite", description="Morda alguém")
@app_commands.describe(membro="Quem você vai morder")
async def bite(interaction: discord.Interaction, membro: discord.Member):
    await interaction.response.defer()
    embed, view = await _build_interacao("bite", interaction.user, membro)
    await interaction.followup.send(content=membro.mention, embed=embed, view=view)

# ── /cry ──────────────────────────────────────────
@bot.tree.command(name="cry", description="Chore (ou console alguém)")
@app_commands.describe(membro="Quem você quer consolar (opcional)")
async def cry(interaction: discord.Interaction, membro: discord.Member | None = None):
    await interaction.response.defer()
    if membro and membro.id != interaction.user.id:
        embed, view = await _build_interacao("cry", interaction.user, membro)
        await interaction.followup.send(content=membro.mention, embed=embed, view=view)
    else:
        embed, _ = await _build_interacao("cry", interaction.user, solo=True)
        await interaction.followup.send(embed=embed)

# ── /blush ────────────────────────────────────────
@bot.tree.command(name="blush", description="Fique vermelho ou elogie alguém")
@app_commands.describe(membro="Quem você quer elogiar (opcional)")
async def blush(interaction: discord.Interaction, membro: discord.Member | None = None):
    await interaction.response.defer()
    if membro and membro.id != interaction.user.id:
        embed, view = await _build_interacao("blush", interaction.user, membro)
        await interaction.followup.send(content=membro.mention, embed=embed, view=view)
    else:
        embed, _ = await _build_interacao("blush", interaction.user, solo=True)
        await interaction.followup.send(embed=embed)

# ── /dance ────────────────────────────────────────
@bot.tree.command(name="dance", description="Dance ou convide alguém para dançar")
@app_commands.describe(membro="Quem você quer chamar para dançar (opcional)")
async def dance(interaction: discord.Interaction, membro: discord.Member | None = None):
    await interaction.response.defer()
    if membro and membro.id != interaction.user.id:
        embed, view = await _build_interacao("dance", interaction.user, membro)
        await interaction.followup.send(content=membro.mention, embed=embed, view=view)
    else:
        embed, _ = await _build_interacao("dance", interaction.user, solo=True)
        await interaction.followup.send(embed=embed)

# ── /highfive ─────────────────────────────────────
@bot.tree.command(name="highfive", description="Dê um toca aqui em alguém")
@app_commands.describe(membro="Com quem vai ser o toca aqui")
async def highfive(interaction: discord.Interaction, membro: discord.Member):
    await interaction.response.defer()
    embed, view = await _build_interacao("highfive", interaction.user, membro)
    await interaction.followup.send(content=membro.mention, embed=embed, view=view)

# ── /wave ─────────────────────────────────────────
@bot.tree.command(name="wave", description="Acene para alguém")
@app_commands.describe(membro="Para quem você quer acenar (opcional)")
async def wave(interaction: discord.Interaction, membro: discord.Member | None = None):
    await interaction.response.defer()
    if membro and membro.id != interaction.user.id:
        embed, view = await _build_interacao("wave", interaction.user, membro)
        await interaction.followup.send(content=membro.mention, embed=embed, view=view)
    else:
        embed, _ = await _build_interacao("wave", interaction.user, solo=True)
        await interaction.followup.send(embed=embed)

# ── /cuddle ───────────────────────────────────────
@bot.tree.command(name="cuddle", description="Se aconchegue com alguém")
@app_commands.describe(membro="Com quem você quer se aconchegar")
async def cuddle(interaction: discord.Interaction, membro: discord.Member):
    await interaction.response.defer()
    embed, view = await _build_interacao("cuddle", interaction.user, membro)
    await interaction.followup.send(content=membro.mention, embed=embed, view=view)

# ── /lick ─────────────────────────────────────────
@bot.tree.command(name="lick", description="Lamba alguém")
@app_commands.describe(membro="Quem vai ser lambido(a)")
async def lick(interaction: discord.Interaction, membro: discord.Member):
    await interaction.response.defer()
    embed, view = await _build_interacao("lick", interaction.user, membro)
    await interaction.followup.send(content=membro.mention, embed=embed, view=view)

# ── /yeet ─────────────────────────────────────────
@bot.tree.command(name="yeet", description="YEET! Lance alguém para longe")
@app_commands.describe(membro="Quem vai ser yeetado(a)")
async def yeet(interaction: discord.Interaction, membro: discord.Member):
    await interaction.response.defer()
    embed, view = await _build_interacao("yeet", interaction.user, membro)
    await interaction.followup.send(content=membro.mention, embed=embed, view=view)

# ── /nuzzle ───────────────────────────────────────
@bot.tree.command(name="nuzzle", description="Esfregue o rosto em alguém carinhosamente")
@app_commands.describe(membro="Com quem você quer nuzzlar")
async def nuzzle(interaction: discord.Interaction, membro: discord.Member):
    await interaction.response.defer()
    embed, view = await _build_interacao("nuzzle", interaction.user, membro)
    await interaction.followup.send(content=membro.mention, embed=embed, view=view)

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

TICKET_CATEGORIES = [
    discord.SelectOption(label="Suporte Geral",    value="suporte",    description="Dúvidas gerais ou ajuda",           emoji="<:1000006244:1475982552488607815>"),
    discord.SelectOption(label="Denúncias",         value="denuncia",   description="Denunciar um membro ou situação",   emoji="<:1000006242:1475982573846139001>"),
    discord.SelectOption(label="Compra de VIP",     value="vip",        description="Adquirir um cargo VIP",             emoji="<:1000006239:1475982464928452678>"),
    discord.SelectOption(label="Resgate de Prêmio", value="premio",     description="Resgatar um prêmio conquistado",    emoji="<:1000006240:1475982529243643967>"),
    discord.SelectOption(label="Patrocínio",        value="patrocinio", description="Proposta de parceria ou patrocínio",emoji="<:1000006247:1475982600463187990>"),
    discord.SelectOption(label="Outros",            value="outros",     description="Outros assuntos",                   emoji="<:1000006236:1475982635384836126>"),
]

TICKET_EMOJI_MAP = {
    "suporte":    "<:1000006244:1475982552488607815>",
    "denuncia":   "<:1000006242:1475982573846139001>",
    "vip":        "<:1000006239:1475982464928452678>",
    "premio":     "<:1000006240:1475982529243643967>",
    "patrocinio": "<:1000006247:1475982600463187990>",
    "outros":     "<:1000006236:1475982635384836126>",
}
TICKET_LABEL_MAP = {
    "suporte":    "Suporte Geral",
    "denuncia":   "Denúncias",
    "vip":        "Compra de VIP",
    "premio":     "Resgate de Prêmio",
    "patrocinio": "Patrocínio",
    "outros":     "Outros",
}

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


class TicketAdminView(View):
    def __init__(self, opener_id: int):
        super().__init__(timeout=None)
        self.opener_id = opener_id

    def _is_staff(self, interaction: discord.Interaction) -> bool:
        user_role_ids = {r.id for r in interaction.user.roles}
        staff_ids = getattr(bot, "staff_role_ids", [])
        if not staff_ids and bot.staff_role_id:
            staff_ids = [bot.staff_role_id]
        is_staff = bool(user_role_ids & set(staff_ids))
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


class TicketMainView(View):
    def __init__(self, opener_id: int):
        super().__init__(timeout=None)
        self.opener_id = opener_id

    def _is_staff(self, interaction: discord.Interaction) -> bool:
        user_role_ids = {r.id for r in interaction.user.roles}
        staff_ids = getattr(bot, "staff_role_ids", [])
        if not staff_ids and bot.staff_role_id:
            staff_ids = [bot.staff_role_id]
        is_staff = bool(user_role_ids & set(staff_ids))
        return bool(is_staff or interaction.user.guild_permissions.administrator)

    @discord.ui.button(label="Atender", style=discord.ButtonStyle.success, emoji=discord.PartialEmoji.from_str("<a:1000006152:1475983799568433355>"), custom_id="ticket_atender", row=0)
    async def atender(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self._is_staff(interaction):
            return await interaction.response.send_message(embed=error_embed("Sem permissão", "Apenas a staff pode assumir tickets."), ephemeral=True)
        if not hasattr(bot, "ticket_atendentes"):
            bot.ticket_atendentes = {}
        bot.ticket_atendentes[interaction.channel.id] = interaction.user.id
        embed = discord.Embed(
            title=f"{E.VERIFY} Ticket Assumido",
            description=(
                f"{E.STAR} **Atendente:** {interaction.user.mention}\n\n"
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
        staff_ids = getattr(bot, "staff_role_ids", [])
        if not staff_ids and bot.staff_role_id:
            staff_ids = [bot.staff_role_id]
        staff_roles = [interaction.guild.get_role(rid) for rid in staff_ids if interaction.guild.get_role(rid)]
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
        if staff_roles:
            mentions = " ".join(r.mention for r in staff_roles)
            await interaction.response.send_message(
                content=mentions,
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
        await interaction.response.send_modal(TicketMotivoModal(categoria))


async def _criar_ticket(interaction: discord.Interaction, categoria: str, motivo_usuario: str):
    await interaction.response.defer(ephemeral=True)

    guild      = interaction.guild
    category   = guild.get_channel(bot.ticket_category_id)
    staff_ids  = getattr(bot, "staff_role_ids", [])
    if not staff_ids and bot.staff_role_id:
        staff_ids = [bot.staff_role_id]
    staff_roles = [guild.get_role(rid) for rid in staff_ids if guild.get_role(rid)]
    # Legado: mantém staff_role para compatibilidade
    staff_role = staff_roles[0] if staff_roles else None
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
    for srole in staff_roles:
        overwrites[srole] = discord.PermissionOverwrite(
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

    welcome_embed = discord.Embed(
        title=f"{E.FIRE} {label}",
        description=(
            f"{E.PIN} **Aberto por:** {interaction.user.mention}\n"
            f"{E.RULES} **Categoria:** {label}\n"
            f"{E.DIAMOND} **Motivo:** {motivo_usuario}\n\n"
            f"{E.ARROW} Olá, {interaction.user.mention}! Me diga mais detalhes enquanto aguarda a equipe responsável.\n\n"
            f"{E.RING} Nossa equipe irá te atender em breve {E.HEARTS_S}"
        ),
        color=Colors.MAIN,
    )
    welcome_embed.set_thumbnail(url=interaction.user.display_avatar.url)
    welcome_embed.set_footer(text=f"{guild.name} • ID do usuário: {interaction.user.id}")
    welcome_embed.timestamp = discord.utils.utcnow()

    banner_url = getattr(bot, "ticket_banner_url", None)
    if banner_url:
        welcome_embed.set_image(url=banner_url)

    main_view  = TicketMainView(opener_id=interaction.user.id)
    staff_ping = " ".join(r.mention for r in staff_roles) if staff_roles else ""
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


class TicketCloseView(View):
    """Mantida para tickets abertos antes da atualização."""
    def __init__(self, opener_id: int):
        super().__init__(timeout=None)
        self.opener_id = opener_id

    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="ticket_close_legacy")
    async def fechar(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_role_ids = {r.id for r in interaction.user.roles}
        staff_ids = getattr(bot, "staff_role_ids", [])
        if not staff_ids and bot.staff_role_id:
            staff_ids = [bot.staff_role_id]
        is_staff = bool(user_role_ids & set(staff_ids))
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
    cargo_staff="Cargo principal da staff (obrigatório)",
    cargo_staff_2="2º cargo de staff com acesso aos tickets (opcional)",
    cargo_staff_3="3º cargo de staff com acesso aos tickets (opcional)",
    cargo_staff_4="4º cargo de staff com acesso aos tickets (opcional)",
    cargo_staff_5="5º cargo de staff com acesso aos tickets (opcional)",
    canal_log="Canal para logs de tickets (opcional)",
    banner_url="URL do banner/imagem exibido dentro do ticket ao abrir (opcional)",
)
async def setup_tickets(
    interaction: discord.Interaction,
    categoria: discord.CategoryChannel,
    cargo_staff: discord.Role,
    cargo_staff_2: discord.Role | None = None,
    cargo_staff_3: discord.Role | None = None,
    cargo_staff_4: discord.Role | None = None,
    cargo_staff_5: discord.Role | None = None,
    canal_log: discord.TextChannel | None = None,
    banner_url: str | None = None,
):
    bot.ticket_category_id = categoria.id
    bot.staff_role_id      = cargo_staff.id   # legado

    # Monta lista de cargos únicos
    cargos = [cargo_staff]
    for c in [cargo_staff_2, cargo_staff_3, cargo_staff_4, cargo_staff_5]:
        if c and c.id not in {x.id for x in cargos}:
            cargos.append(c)
    bot.staff_role_ids = [c.id for c in cargos]

    if canal_log:
        bot.ticket_log_channel_id = canal_log.id
        bot.log_channel_id        = canal_log.id
    if banner_url:
        bot.ticket_banner_url = banner_url

    cargos_texto = "\n".join(f"  {E.ARROW} {c.mention}" for c in cargos)
    embed = success_embed(
        "Tickets configurados!",
        f"{E.SYMBOL} **Categoria:** {categoria.name}\n"
        f"{E.CALENDAR} **Cargos de staff ({len(cargos)}):**\n{cargos_texto}\n"
        f"{E.LINK} **Log:** {canal_log.mention if canal_log else 'Não definido'}\n"
        f"{E.GEM} **Banner:** {'Configurado ✅' if banner_url else 'Não definido'}\n\n"
        f"{E.ARROW} Use `/ticket-painel` para enviar o painel de tickets em um canal.",
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)
    log.info(f"Tickets configurados: categoria={categoria.id}, staff_roles={bot.staff_role_ids}")

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
            f"{E.ARROW} {descricao}\n\n"
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

    ok = await _criar_regra_http(guild, {
        "name": "[Bot] Anti-Spam de Conteúdo",
        "event_type": 1, "trigger_type": 3,
        "actions": [{"type": 1, "metadata": {"custom_message": "Conteúdo identificado como spam."}}],
        "enabled": True,
    })
    if ok: criadas += 1
    else:  erros   += 1

    ok = await _criar_regra_http(guild, {
        "name": "[Bot] Conteúdo Explícito (Preset)",
        "event_type": 1, "trigger_type": 4,
        "trigger_metadata": {"presets": [1, 2, 3]},
        "actions": [{"type": 1, "metadata": {"custom_message": "Conteúdo não permitido neste servidor."}}],
        "enabled": True,
    })
    if ok: criadas += 1
    else:  erros   += 1

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
    dados  = _xp_data[interaction.guild.id][membro.id]
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
    embed.add_field(name=f"{E.TROPHY} Nível XP", value=f"`{dados['level']}` · `{dados['xp']:,}` XP", inline=True)
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
# ============= COMANDO DE AJUDA ==================
# ==================================================

_HELP_PAGES = [
    {
        "titulo": f"{E.MASCOT} Sobre mim",
        "desc": (
            f"Olá! Eu sou um bot multifuncional criado para deixar o seu servidor "
            f"organizado, divertido e bem administrado.\n\n"
            f"{E.SPARKLE} Tenho sistemas de **tickets**, **moderação**, **XP & níveis**, "
            f"**boas-vindas**, **música** e muito mais!\n\n"
            f"{E.ARROW} Use os botões abaixo para navegar pelos meus comandos."
        ),
        "campos": [
            (f"{E.FIRE} Categorias disponíveis", (
                f"{E.SYMBOL} Visão Geral\n"
                f"🎫 Tickets\n"
                f"🛡️ Moderação\n"
                f"⚠️ Avisos\n"
                f"⭐ XP & Níveis\n"
                f"👋 Boas-vindas\n"
                f"🖼️ Embeds\n"
                f"{E.SPOTIFY} Música\n"
                f"🎭 Interações"
            ), False),
        ],
    },
    {
        "titulo": "🎫 Tickets",
        "desc": f"{E.DIAMOND} Sistema completo de atendimento via tickets com categorias, logs e painel infinito.",
        "campos": [
            ("`/setup-tickets`",  f"{E.ARROW} Configura o sistema: categoria, até **5 cargos de staff**, log e banner.", False),
            ("`/ticket-painel`",  f"{E.ARROW} Envia o painel de abertura de tickets em um canal. Fica ativo para sempre.", False),
            ("`/fechar-ticket`",  f"{E.ARROW} Fecha e deleta o ticket atual (staff ou quem abriu).", False),
        ],
    },
    {
        "titulo": "🛡️ Moderação",
        "desc": f"{E.DIAMOND} Ferramentas para manter o servidor seguro e organizado.",
        "campos": [
            ("`/ban`",    f"{E.ARROW} Bane um membro do servidor com motivo.", False),
            ("`/unban`",  f"{E.ARROW} Remove o banimento de um usuário pelo ID.", False),
            ("`/kick`",   f"{E.ARROW} Expulsa um membro do servidor.", False),
            ("`/mute`",   f"{E.ARROW} Aplica timeout em um membro (1–40.320 min).", False),
            ("`/unmute`", f"{E.ARROW} Remove o timeout de um membro.", False),
            ("`/clear`",  f"{E.ARROW} Apaga de 1 a 100 mensagens do canal.", False),
        ],
    },
    {
        "titulo": "⚠️ Avisos",
        "desc": f"{E.DIAMOND} Sistema de advertências para registrar e consultar warns.",
        "campos": [
            ("`/warn`",       f"{E.ARROW} Aplica um aviso a um membro. Notifica por DM.", False),
            ("`/warns`",      f"{E.ARROW} Lista todos os avisos de um membro.", False),
            ("`/clearwarns`", f"{E.ARROW} Remove todos os avisos de um membro.", False),
        ],
    },
    {
        "titulo": "⭐ XP & Níveis",
        "desc": f"{E.DIAMOND} Sistema de XP por mensagens com níveis, ranking e cargos automáticos.",
        "campos": [
            ("`/rank`",                f"{E.ARROW} Veja seu nível, XP e posição no servidor.", False),
            ("`/top`",                 f"{E.ARROW} Ranking dos top 10 membros com mais XP.", False),
            ("`/xp-config`",           f"{E.ARROW} Configura canal de nível, nível máximo e ativa/desativa XP.", False),
            ("`/xp-dar`",              f"{E.ARROW} Dá XP manualmente a um membro.", False),
            ("`/xp-remover`",          f"{E.ARROW} Remove XP de um membro.", False),
            ("`/xp-reset`",            f"{E.ARROW} Zera todo o XP de um membro.", False),
            ("`/xp-cargo-nivel`",      f"{E.ARROW} Define um cargo automático para um nível.", False),
            ("`/xp-cargo-nivel-remover`", f"{E.ARROW} Remove o cargo automático de um nível.", False),
        ],
    },
    {
        "titulo": "👋 Boas-vindas",
        "desc": f"{E.DIAMOND} Mensagem de boas-vindas personalizável com banner, DM e variáveis.",
        "campos": [
            ("`/boas-vindas`",        f"{E.ARROW} Configura canal, mensagem, banner e DM de boas-vindas.", False),
            ("`/boas-vindas-testar`", f"{E.ARROW} Simula a mensagem de boas-vindas com você mesmo.", False),
            ("`/boas-vindas-ver`",    f"{E.ARROW} Mostra as configurações atuais de boas-vindas.", False),
        ],
    },
    {
        "titulo": "🖼️ Embeds",
        "desc": f"{E.DIAMOND} Crie e edite embeds personalizados diretamente pelo bot.",
        "campos": [
            ("`/embed`",        f"{E.ARROW} Abre o criador de embeds com opções de título, cor, imagem e rodapé.", False),
            ("`/embed-editar`", f"{E.ARROW} Edita uma embed já enviada pelo bot (requer ID da mensagem).", False),
        ],
    },
    {
        "titulo": f"{E.SPOTIFY} Música",
        "desc": f"{E.DIAMOND} Toque músicas do {E.YOUTUBE} YouTube e {E.SPOTIFY} Spotify direto no seu servidor!",
        "campos": [
            ("`/tocar`",     f"{E.ARROW} Toca uma música ou playlist (YouTube/Spotify).", False),
            ("`/pausar`",    f"{E.ARROW} Pausa a música atual.", False),
            ("`/retomar`",   f"{E.ARROW} Retoma a música pausada.", False),
            ("`/pular`",     f"{E.ARROW} Pula para a próxima música da fila.", False),
            ("`/fila`",      f"{E.ARROW} Mostra a fila de músicas atual.", False),
            ("`/tocando`",   f"{E.ARROW} Mostra a música que está tocando agora.", False),
            ("`/volume`",    f"{E.ARROW} Ajusta o volume (1–100).", False),
            ("`/parar`",     f"{E.ARROW} Para a música e limpa a fila.", False),
            ("`/sair`",      f"{E.ARROW} Desconecta o bot do canal de voz.", False),
            ("`/embaralhar`",f"{E.ARROW} Embaralha a fila de músicas.", False),
            ("`/repetir`",   f"{E.ARROW} Ativa/desativa a repetição da música atual.", False),
        ],
    },
    {
        "titulo": "🎭 Interações",
        "desc": f"{E.DIAMOND} Comandos de interação de anime entre membros do servidor.",
        "campos": [
            ("`/kiss`",      f"{E.ARROW} Beije alguém.", False),
            ("`/hug`",       f"{E.ARROW} Abrace alguém.", False),
            ("`/pat`",       f"{E.ARROW} Faça carinho em alguém.", False),
            ("`/slap`",      f"{E.ARROW} Dê um tapa em alguém.", False),
            ("`/poke`",      f"{E.ARROW} Cutuque alguém.", False),
            ("`/bite`",      f"{E.ARROW} Morda alguém.", False),
            ("`/cry`",       f"{E.ARROW} Chore ou console alguém.", False),
            ("`/dance`",     f"{E.ARROW} Dance ou convide alguém para dançar.", False),
            ("`/cuddle`",    f"{E.ARROW} Se aconchegue com alguém.", False),
            ("`/wave`",      f"{E.ARROW} Acene para alguém.", False),
            ("`/highfive`",  f"{E.ARROW} Dê um toca aqui em alguém.", False),
            ("`/lick`",      f"{E.ARROW} Lamba alguém.", False),
            ("`/yeet`",      f"{E.ARROW} YEET! Lance alguém para longe.", False),
            ("`/nuzzle`",    f"{E.ARROW} Esfregue o rosto em alguém carinhosamente.", False),
        ],
    },
]

_HELP_PAGE_LABELS = [
    f"Início",
    "Tickets",
    "Moderação",
    "Avisos",
    "XP & Níveis",
    "Boas-vindas",
    "Embeds",
    "Música",
    "Interações",
]

def _build_help_embed(page: int, guild: discord.Guild | None = None) -> discord.Embed:
    data  = _HELP_PAGES[page]
    total = len(_HELP_PAGES)
    embed = discord.Embed(
        title=data["titulo"],
        description=data["desc"],
        color=Colors.MAIN,
    )
    for name, value, inline in data["campos"]:
        embed.add_field(name=name, value=value, inline=inline)
    embed.set_footer(text=f"Página {page + 1} de {total}{' • ' + guild.name if guild else ''}")
    embed.timestamp = discord.utils.utcnow()
    return embed


class AjudaView(View):
    def __init__(self, page: int = 0, autor_id: int = 0):
        super().__init__(timeout=120)
        self.page     = page
        self.autor_id = autor_id
        self._update_buttons()

    def _update_buttons(self):
        self.clear_items()
        total = len(_HELP_PAGES)

        # Botão anterior
        btn_prev = discord.ui.Button(
            label="◀ Anterior",
            style=discord.ButtonStyle.secondary,
            disabled=(self.page == 0),
        )
        btn_prev.callback = self._prev
        self.add_item(btn_prev)

        # Select de categorias
        options = [
            discord.SelectOption(
                label=_HELP_PAGE_LABELS[i],
                value=str(i),
                default=(i == self.page),
            )
            for i in range(total)
        ]
        select = discord.ui.Select(placeholder="Ir para categoria...", options=options)
        select.callback = self._select
        self.add_item(select)

        # Botão próximo
        btn_next = discord.ui.Button(
            label="Próximo ▶",
            style=discord.ButtonStyle.secondary,
            disabled=(self.page == total - 1),
        )
        btn_next.callback = self._next
        self.add_item(btn_next)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.autor_id and interaction.user.id != self.autor_id:
            await interaction.response.send_message(
                f"{E.WARN_IC} Apenas quem usou `/ajuda` pode navegar neste menu.", ephemeral=True
            )
            return False
        return True

    async def _prev(self, interaction: discord.Interaction):
        self.page -= 1
        self._update_buttons()
        await interaction.response.edit_message(
            embed=_build_help_embed(self.page, interaction.guild), view=self
        )

    async def _next(self, interaction: discord.Interaction):
        self.page += 1
        self._update_buttons()
        await interaction.response.edit_message(
            embed=_build_help_embed(self.page, interaction.guild), view=self
        )

    async def _select(self, interaction: discord.Interaction):
        self.page = int(interaction.data["values"][0])
        self._update_buttons()
        await interaction.response.edit_message(
            embed=_build_help_embed(self.page, interaction.guild), view=self
        )

    async def on_timeout(self):
        # Desativa os botões quando expirar
        for item in self.children:
            item.disabled = True


@bot.tree.command(name="ajuda", description="Mostra todos os comandos e informações sobre o bot")
async def ajuda(interaction: discord.Interaction):
    embed = _build_help_embed(0, interaction.guild)
    embed.set_thumbnail(url=bot.user.display_avatar.url if bot.user else None)
    view  = AjudaView(page=0, autor_id=interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view)


# ==================================================
# ============= SISTEMA DE MÚSICA =================
# ==================================================
# Dependências: yt-dlp, PyNaCl, wavelink  OU  yt-dlp + FFmpeg via voice client direto.
# Esta implementação usa yt-dlp + discord.py voice (FFmpegPCMAudio) sem servidor externo.
# Instalar: pip install yt-dlp PyNaCl
#
# Para suporte a Spotify: a URL é convertida para busca no YouTube via yt-dlp.

try:
    import yt_dlp  # type: ignore
    _YTDLP_AVAILABLE = True
except ImportError:
    _YTDLP_AVAILABLE = False
    log.warning("yt-dlp não instalado. Comandos de música ficarão desabilitados. Execute: pip install yt-dlp PyNaCl")

YDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
    "extract_flat": "in_playlist",
}
FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

# Verifica se FFmpeg está instalado
import shutil as _shutil
_FFMPEG_AVAILABLE = bool(_shutil.which("ffmpeg"))
if not _FFMPEG_AVAILABLE:
    log.warning("FFmpeg não encontrado no sistema. Comandos de música ficarão desabilitados. Instale com: apt install ffmpeg")

def _music_unavailable_embed() -> discord.Embed:
    if not _YTDLP_AVAILABLE:
        return error_embed(
            "Música indisponível",
            f"{E.WARN_IC} A biblioteca `yt-dlp` não está instalada.\n"
            f"{E.ARROW} Execute `pip install yt-dlp PyNaCl` e reinicie o bot."
        )
    if not _FFMPEG_AVAILABLE:
        return error_embed(
            "FFmpeg não encontrado",
            f"{E.WARN_IC} O **FFmpeg** não está instalado no servidor.\n\n"
            f"{E.ARROW} Para instalar, execute no terminal do servidor:\n"
            f"```\napt install ffmpeg\n```\n"
            f"{E.SYMBOL} Após instalar, reinicie o bot."
        )
    return error_embed("Música indisponível", f"{E.WARN_IC} Erro desconhecido no sistema de música.")

# Estado de música por servidor
# _music_state[guild_id] = {"queue": [], "loop": False, "volume": 0.5, "current": None}
_music_state: dict[int, dict] = {}

def _get_music_state(guild_id: int) -> dict:
    if guild_id not in _music_state:
        _music_state[guild_id] = {
            "queue":   [],
            "loop":    False,
            "volume":  0.5,
            "current": None,
        }
    return _music_state[guild_id]


async def _fetch_track(query: str) -> dict | None:
    """Busca uma faixa via yt-dlp e retorna SEMPRE com URL de stream de áudio válida."""
    if not _YTDLP_AVAILABLE:
        return None

    # Links do Spotify: converte para busca no YouTube
    if "spotify.com/track" in query:
        import re
        # Tenta extrair nome do artista + título via slug da URL
        slug = query.rstrip("/").split("/")[-1].split("?")[0]
        query = slug.replace("-", " ")

    loop = asyncio.get_running_loop()

    # Opções que SEMPRE extraem a URL real de stream (sem extract_flat)
    ydl_opts = {
        "format": "bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "source_address": "0.0.0.0",
        "extract_flat": False,      # CRÍTICO: False garante URL de stream
        "ignoreerrors": True,
        "socket_timeout": 15,       # timeout de socket para evitar travamento
    }

    def _extract():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_query = query if query.startswith("http") else f"ytsearch1:{query}"
            info = ydl.extract_info(search_query, download=False)
            if not info:
                return None
            # ytsearch retorna um dict com "entries"
            if "entries" in info:
                entries = [e for e in info["entries"] if e]
                info = entries[0] if entries else None
            return info

    try:
        # Timeout de 30s no total para evitar que o Discord marque "app não respondeu"
        info = await asyncio.wait_for(
            loop.run_in_executor(None, _extract),
            timeout=30.0,
        )
        if not info:
            return None

        stream_url = info.get("url", "")
        if not stream_url:
            # Tenta pegar do primeiro formato disponível
            fmts = info.get("formats", [])
            for fmt in reversed(fmts):
                if fmt.get("url") and fmt.get("acodec") != "none":
                    stream_url = fmt["url"]
                    break

        if not stream_url:
            log.warning(f"Nenhuma URL de stream encontrada para: {query}")
            return None

        return {
            "url":         stream_url,
            "title":       info.get("title", "Desconhecido"),
            "duration":    info.get("duration", 0),
            "thumbnail":   info.get("thumbnail", None),
            "webpage_url": info.get("webpage_url", query),
            "uploader":    info.get("uploader", ""),
        }
    except asyncio.TimeoutError:
        log.warning(f"Timeout ao buscar faixa '{query}': yt-dlp demorou mais de 30s")
        return None
    except Exception as exc:
        log.warning(f"Erro ao buscar faixa '{query}': {exc}")
        return None


async def _fetch_playlist(url: str) -> list[dict]:
    """Busca todas as faixas de uma playlist."""
    if not _YTDLP_AVAILABLE:
        return []
    loop = asyncio.get_running_loop()
    ydl_opts = {**YDL_OPTIONS, "noplaylist": False, "extract_flat": True, "socket_timeout": 15}

    def _extract():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    try:
        info = await asyncio.wait_for(
            loop.run_in_executor(None, _extract),
            timeout=45.0,
        )
        if not info:
            return []
        entries = info.get("entries", [info])
        return [
            {
                "url":         e.get("url") or e.get("webpage_url", ""),
                "title":       e.get("title", "Desconhecido"),
                "duration":    e.get("duration", 0),
                "thumbnail":   e.get("thumbnail", None),
                "webpage_url": e.get("webpage_url") or e.get("url", ""),
                "uploader":    e.get("uploader", ""),
            }
            for e in entries if e
        ]
    except asyncio.TimeoutError:
        log.warning(f"Timeout ao buscar playlist '{url}': yt-dlp demorou mais de 45s")
        return []
    except Exception as exc:
        log.warning(f"Erro ao buscar playlist '{url}': {exc}")
        return []


def _format_duration(seconds: int | float) -> str:
    seconds = int(seconds or 0)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _source_emoji(url: str) -> str:
    if "spotify.com" in url:
        return E.SPOTIFY
    return E.YOUTUBE


def _play_next(guild_id: int, voice_client: discord.VoiceClient):
    """Callback chamado quando uma faixa termina. Roda em thread, então agenda coroutine no loop."""
    async def _start_next():
        state = _get_music_state(guild_id)
        if state["loop"] and state["current"]:
            track = state["current"]
        elif state["queue"]:
            track = state["queue"].pop(0)
            state["current"] = track
        else:
            state["current"] = None
            return

        # Se a faixa veio de playlist (extract_flat), pode não ter URL de stream ainda
        if not track.get("url") or not track["url"].startswith("http"):
            try:
                fetched = await asyncio.wait_for(_fetch_track(track.get("webpage_url") or track.get("url", "")), timeout=30.0)
            except asyncio.TimeoutError:
                fetched = None
            if not fetched:
                log.warning(f"Não foi possível obter stream para: {track.get('title')}")
                state["current"] = None
                if state["queue"]:
                    _play_next(guild_id, voice_client)
                return
            track = fetched
            state["current"] = track

        try:
            source = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(track["url"], **FFMPEG_OPTIONS),
                volume=state["volume"],
            )
            voice_client.play(
                source,
                after=lambda e: _play_next(guild_id, voice_client) if not e else log.warning(f"Erro de reprodução: {e}"),
            )
        except Exception as exc:
            log.warning(f"Erro ao iniciar próxima faixa: {exc}")

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(_start_next(), loop)
        else:
            loop.run_until_complete(_start_next())
    except Exception as exc:
        log.warning(f"Erro no _play_next: {exc}")




# ── /tocar ───────────────────────────────────────────
@bot.tree.command(name="tocar", description="Toca uma música ou playlist (YouTube/Spotify)")
@app_commands.describe(musica="Nome, link do YouTube ou link do Spotify")
async def tocar(interaction: discord.Interaction, musica: str):
    if not _YTDLP_AVAILABLE or not _FFMPEG_AVAILABLE:
        return await interaction.response.send_message(embed=_music_unavailable_embed(), ephemeral=True)

    if not interaction.user.voice or not interaction.user.voice.channel:
        return await interaction.response.send_message(
            embed=error_embed("Sem canal de voz", f"{E.WARN_IC} Você precisa estar em um canal de voz!"), ephemeral=True
        )

    await interaction.response.defer()

    vc = interaction.guild.voice_client
    if not vc:
        try:
            vc = await interaction.user.voice.channel.connect()
        except discord.ClientException:
            return await interaction.followup.send(
                embed=error_embed("Erro", f"{E.WARN_IC} Não consegui entrar no canal de voz."), ephemeral=True
            )

    state = _get_music_state(interaction.guild.id)

    # Detecta se é playlist
    is_playlist = (
        ("youtube.com/playlist" in musica or "list=" in musica) or
        ("spotify.com/playlist" in musica) or
        ("spotify.com/album" in musica)
    )

    if is_playlist:
        tracks = await _fetch_playlist(musica)
        if not tracks:
            return await interaction.followup.send(
                embed=error_embed("Não encontrado", f"{E.WARN_IC} Não consegui carregar a playlist. Verifique o link e tente novamente."), ephemeral=True
            )
        state["queue"].extend(tracks)
        emoji = _source_emoji(musica)
        embed = discord.Embed(
            title=f"{emoji} Playlist adicionada!",
            description=(
                f"{E.SPARKLE} **{len(tracks)}** faixas adicionadas à fila.\n"
                f"{E.ARROW} Use `/fila` para ver todas as músicas."
            ),
            color=Colors.MAIN,
        )
        embed.set_footer(text=f"{interaction.guild.name} • Música")
        embed.timestamp = discord.utils.utcnow()
        await interaction.followup.send(embed=embed)
    else:
        track = await _fetch_track(musica)
        if not track:
            return await interaction.followup.send(
                embed=error_embed(
                    "Não encontrado",
                    f"{E.WARN_IC} Não encontrei `{musica}`.\n"
                    f"{E.ARROW} Verifique o link ou tente outro nome.\n"
                    f"{E.SYMBOL} Se for YouTube, o vídeo pode ter restrição de idade ou estar indisponível."
                ), ephemeral=True
            )

        if vc.is_playing() or vc.is_paused():
            state["queue"].append(track)
            emoji = _source_emoji(track["webpage_url"])
            embed = discord.Embed(
                title=f"{emoji} Adicionado à fila",
                description=(
                    f"{E.ARROW} **[{track['title']}]({track['webpage_url']})**\n"
                    f"{E.STAR} Duração: `{_format_duration(track['duration'])}`\n"
                    f"{E.SYMBOL} Posição na fila: `#{len(state['queue'])}`"
                ),
                color=Colors.MAIN,
            )
            if track["thumbnail"]:
                embed.set_thumbnail(url=track["thumbnail"])
            embed.set_footer(text=f"{interaction.guild.name} • Música")
            embed.timestamp = discord.utils.utcnow()
            return await interaction.followup.send(embed=embed)

        state["current"] = track
        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(track["url"], **FFMPEG_OPTIONS),
            volume=state["volume"],
        )
        vc.play(
            source,
            after=lambda e: _play_next(interaction.guild.id, vc) if not e else log.warning(f"Erro: {e}"),
        )
        emoji = _source_emoji(track["webpage_url"])
        embed = discord.Embed(
            title=f"{emoji} Tocando agora",
            description=(
                f"{E.ARROW} **[{track['title']}]({track['webpage_url']})**\n"
                f"{E.STAR} Duração: `{_format_duration(track['duration'])}`\n"
                f"{E.MASCOT} Canal: `{track['uploader']}`\n"
                f"{E.GEM} Volume: `{int(state['volume'] * 100)}%`"
            ),
            color=Colors.MAIN,
        )
        if track["thumbnail"]:
            embed.set_image(url=track["thumbnail"])
        embed.set_footer(text=f"{interaction.guild.name} • Música")
        embed.timestamp = discord.utils.utcnow()
        await interaction.followup.send(embed=embed)


# ── /tocando ─────────────────────────────────────────
@bot.tree.command(name="tocando", description="Mostra a música que está tocando agora")
async def tocando(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if not vc or not vc.is_playing():
        return await interaction.response.send_message(
            embed=error_embed("Nada tocando", f"{E.WARN_IC} Não há nenhuma música tocando no momento."), ephemeral=True
        )
    state   = _get_music_state(interaction.guild.id)
    current = state.get("current")
    if not current:
        return await interaction.response.send_message(
            embed=error_embed("Nada tocando", f"{E.WARN_IC} Não há nenhuma música tocando no momento."), ephemeral=True
        )
    emoji = _source_emoji(current["webpage_url"])
    embed = discord.Embed(
        title=f"{emoji} Tocando agora",
        description=(
            f"{E.ARROW} **[{current['title']}]({current['webpage_url']})**\n"
            f"{E.STAR} Duração: `{_format_duration(current['duration'])}`\n"
            f"{E.MASCOT} Canal: `{current['uploader']}`\n"
            f"{E.GEM} Volume: `{int(state['volume'] * 100)}%`\n"
            f"{E.RING} Repetir: `{'Ativado' if state['loop'] else 'Desativado'}`\n"
            f"{E.SYMBOL} Fila: `{len(state['queue'])}` música(s)"
        ),
        color=Colors.MAIN,
    )
    if current["thumbnail"]:
        embed.set_image(url=current["thumbnail"])
    embed.set_footer(text=f"{interaction.guild.name} • Música")
    embed.timestamp = discord.utils.utcnow()
    await interaction.response.send_message(embed=embed)


# ── /pausar ──────────────────────────────────────────
@bot.tree.command(name="pausar", description="Pausa a música atual")
async def pausar(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if not vc or not vc.is_playing():
        return await interaction.response.send_message(
            embed=error_embed("Erro", f"{E.WARN_IC} Não há nenhuma música tocando."), ephemeral=True
        )
    vc.pause()
    await interaction.response.send_message(
        embed=success_embed("Pausado", f"{E.LOADING} Música pausada. Use `/retomar` para continuar.")
    )


# ── /retomar ─────────────────────────────────────────
@bot.tree.command(name="retomar", description="Retoma a música pausada")
async def retomar(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if not vc or not vc.is_paused():
        return await interaction.response.send_message(
            embed=error_embed("Erro", f"{E.WARN_IC} Não há nenhuma música pausada."), ephemeral=True
        )
    vc.resume()
    await interaction.response.send_message(
        embed=success_embed("Retomado", f"{E.SPARKLE} Música retomada!")
    )


# ── /pular ───────────────────────────────────────────
@bot.tree.command(name="pular", description="Pula para a próxima música da fila")
async def pular(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if not vc or (not vc.is_playing() and not vc.is_paused()):
        return await interaction.response.send_message(
            embed=error_embed("Erro", f"{E.WARN_IC} Não há nenhuma música tocando."), ephemeral=True
        )
    state = _get_music_state(interaction.guild.id)
    state["loop"] = False  # Desativa loop ao pular manualmente
    vc.stop()
    await interaction.response.send_message(
        embed=success_embed("Pulado", f"{E.ARROW} Música pulada! {E.SPARKLE}")
    )


# ── /parar ───────────────────────────────────────────
@bot.tree.command(name="parar", description="Para a música e limpa a fila")
async def parar(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if not vc:
        return await interaction.response.send_message(
            embed=error_embed("Erro", f"{E.WARN_IC} O bot não está em nenhum canal de voz."), ephemeral=True
        )
    state = _get_music_state(interaction.guild.id)
    state["queue"].clear()
    state["current"] = None
    state["loop"]    = False
    vc.stop()
    await interaction.response.send_message(
        embed=success_embed("Parado", f"{E.FLAME_PUR} Música parada e fila limpa.")
    )


# ── /sair ────────────────────────────────────────────
@bot.tree.command(name="sair", description="Desconecta o bot do canal de voz")
async def sair(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if not vc:
        return await interaction.response.send_message(
            embed=error_embed("Erro", f"{E.WARN_IC} O bot não está em nenhum canal de voz."), ephemeral=True
        )
    state = _get_music_state(interaction.guild.id)
    state["queue"].clear()
    state["current"] = None
    await vc.disconnect()
    await interaction.response.send_message(
        embed=success_embed("Saí do canal", f"{E.LEAF} Até logo! {E.HEARTS_S}")
    )


# ── /volume ──────────────────────────────────────────
@bot.tree.command(name="volume", description="Ajusta o volume da música (1–100)")
@app_commands.describe(nivel="Volume de 1 a 100")
async def volume(interaction: discord.Interaction, nivel: app_commands.Range[int, 1, 100]):
    vc = interaction.guild.voice_client
    state = _get_music_state(interaction.guild.id)
    state["volume"] = nivel / 100
    if vc and vc.source:
        vc.source.volume = state["volume"]
    await interaction.response.send_message(
        embed=success_embed("Volume ajustado", f"{E.GEM} Volume definido para `{nivel}%`.")
    )


# ── /repetir ─────────────────────────────────────────
@bot.tree.command(name="repetir", description="Ativa ou desativa a repetição da música atual")
async def repetir(interaction: discord.Interaction):
    state = _get_music_state(interaction.guild.id)
    state["loop"] = not state["loop"]
    status = "Ativado" if state["loop"] else "Desativado"
    await interaction.response.send_message(
        embed=success_embed(f"Repetir {status}", f"{E.RING} Repetição **{status.lower()}**.")
    )


# ── /embaralhar ──────────────────────────────────────
@bot.tree.command(name="embaralhar", description="Embaralha a fila de músicas")
async def embaralhar(interaction: discord.Interaction):
    state = _get_music_state(interaction.guild.id)
    if not state["queue"]:
        return await interaction.response.send_message(
            embed=error_embed("Fila vazia", f"{E.WARN_IC} Não há músicas na fila para embaralhar."), ephemeral=True
        )
    random.shuffle(state["queue"])
    await interaction.response.send_message(
        embed=success_embed("Fila embaralhada", f"{E.SPARKLE} A fila foi embaralhada! `{len(state['queue'])}` músicas.")
    )


# ── /fila ────────────────────────────────────────────
@bot.tree.command(name="fila", description="Mostra a fila de músicas")
async def fila(interaction: discord.Interaction):
    state   = _get_music_state(interaction.guild.id)
    current = state.get("current")
    queue   = state.get("queue", [])

    if not current and not queue:
        return await interaction.response.send_message(
            embed=error_embed("Fila vazia", f"{E.WARN_IC} Não há músicas na fila no momento."), ephemeral=True
        )

    desc_parts = []
    if current:
        emoji = _source_emoji(current["webpage_url"])
        desc_parts.append(
            f"{emoji} **Tocando agora:**\n"
            f"{E.ARROW} [{current['title']}]({current['webpage_url']}) — `{_format_duration(current['duration'])}`\n"
        )

    if queue:
        desc_parts.append(f"{E.STAR} **Próximas ({len(queue)}):**")
        for i, t in enumerate(queue[:10], 1):
            emoji = _source_emoji(t["webpage_url"])
            desc_parts.append(f"`{i}.` {emoji} [{t['title']}]({t['webpage_url']}) — `{_format_duration(t['duration'])}`")
        if len(queue) > 10:
            desc_parts.append(f"\n{E.SYMBOL} *...e mais {len(queue) - 10} música(s)*")

    embed = discord.Embed(
        title=f"{E.GEM_SHINE} Fila de Músicas",
        description="\n".join(desc_parts),
        color=Colors.MAIN,
    )
    embed.set_footer(
        text=f"{interaction.guild.name} • Repetir: {'On' if state['loop'] else 'Off'} • Volume: {int(state['volume']*100)}%"
    )
    embed.timestamp = discord.utils.utcnow()
    await interaction.response.send_message(embed=embed)


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
