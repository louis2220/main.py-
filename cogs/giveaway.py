"""
cogs/giveaway.py — Sistema de sorteios estilo Loritta.
Interface com botões: Aparência · Geral · Cargos · Entradas Extras · Iniciar
"""

import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import random
import logging
from datetime import datetime, timezone, timedelta
from db.database import get_pool
from utils.constants import Colors, E, success_embed, error_embed, _now

log = logging.getLogger("multibot.giveaway")

GIVEAWAY_EMOJI = "🎉"

# Números animados para contagem regressiva visual
_NUMS = {
    1: E.NUM_1, 2: E.NUM_2, 3: E.NUM_3, 4: E.NUM_4,
    5: E.NUM_5, 6: E.NUM_6, 7: E.NUM_7, 8: E.NUM_8, 9: E.NUM_9,
}


async def _ensure_table():
    async with get_pool().acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS giveaways (
                id              SERIAL PRIMARY KEY,
                guild_id        BIGINT NOT NULL,
                channel_id      BIGINT NOT NULL,
                message_id      BIGINT,
                host_id         BIGINT NOT NULL,
                premio          TEXT NOT NULL,
                descricao       TEXT,
                imagem          TEXT,
                thumbnail       TEXT,
                cor             INT DEFAULT 2728702,
                vencedores      INT DEFAULT 1,
                encerra_em      TIMESTAMPTZ NOT NULL,
                encerrado       BOOLEAN DEFAULT FALSE,
                roles_permitidos BIGINT[],
                roles_bloqueados BIGINT[],
                bonus_entries    JSONB DEFAULT '{}',
                created_at      TIMESTAMPTZ DEFAULT NOW()
            );
        """)


def _fmt_tempo(seconds: int) -> str:
    if seconds <= 0:
        return "Encerrado"
    d, r = divmod(seconds, 86400)
    h, r = divmod(r, 3600)
    m, s = divmod(r, 60)
    parts = []
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    if not parts: parts.append(f"{s}s")
    return " ".join(parts)


def _giveaway_embed(gw: dict, guild: discord.Guild = None) -> discord.Embed:
    agora    = datetime.now(tz=timezone.utc)
    restante = int((gw["encerra_em"] - agora).total_seconds())
    cor      = gw.get("cor", 0x29a6fe)
    encerrado = gw.get("encerrado", False)

    desc_parts = []
    if gw.get("descricao"):
        desc_parts.append(f"{gw['descricao']}\n")

    desc_parts.append(
        f"{E.HEART_ANIM} **Clique no botão abaixo para participar!**\n\n"
        f"{E.LOADING} **Encerra:** {discord.utils.format_dt(gw['encerra_em'], 'R')}\n"
        f"{E.CROWN_PINK} **Ganhadores:** `{gw['vencedores']}`\n"
        f"{E.STAFF} **Sorteado por:** <@{gw['host_id']}>"
    )

    if gw.get("roles_permitidos") and guild:
        roles = [guild.get_role(rid) for rid in gw["roles_permitidos"] if guild.get_role(rid)]
        if roles:
            desc_parts.append(f"\n{E.TICKET_IC} **Requerido:** {' '.join(r.mention for r in roles)}")

    if gw.get("bonus_entries") and guild:
        bonus = gw["bonus_entries"]
        if bonus:
            linhas = []
            for rid, mult in bonus.items():
                r = guild.get_role(int(rid))
                if r:
                    linhas.append(f"{r.mention} → `{mult}x`")
            if linhas:
                desc_parts.append(f"\n{E.MAGIC} **Entradas extras:**\n" + "\n".join(linhas))

    emb = discord.Embed(
        title=f"{E.BOT_ANIME}  {gw['premio']}",
        description="\n".join(desc_parts),
        color=cor if not encerrado else 0x99AAB5,
    )
    if gw.get("thumbnail"):
        emb.set_thumbnail(url=gw["thumbnail"])
    if gw.get("imagem"):
        emb.set_image(url=gw["imagem"])
    emb.set_footer(text=f"{'Encerrado' if encerrado else _fmt_tempo(restante)} • ID: {gw.get('id', '?')}")
    emb.timestamp = gw["encerra_em"]
    return emb


# ── View de participação ──────────────────────────────────────────────────────

class GiveawayJoinView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Participar",
        style=discord.ButtonStyle.success,
        emoji=GIVEAWAY_EMOJI,
        custom_id="giveaway:participar",
    )
    async def participar(self, inter: discord.Interaction, _):
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM giveaways WHERE message_id=$1 AND encerrado=FALSE",
                inter.message.id,
            )
        if not row:
            return await inter.response.send_message(
                embed=error_embed("Sorteio encerrado", "Este sorteio já foi encerrado."),
                ephemeral=True,
            )
        gw = dict(row)

        # Verifica cargo requerido
        if gw.get("roles_permitidos"):
            member_roles = {r.id for r in inter.user.roles}
            if not member_roles & set(gw["roles_permitidos"]):
                needed = [inter.guild.get_role(r) for r in gw["roles_permitidos"]]
                needed = [r for r in needed if r]
                return await inter.response.send_message(
                    embed=error_embed("Acesso restrito",
                        f"{E.TICKET_IC} Você precisa ter um destes cargos para participar:\n"
                        + " ".join(r.mention for r in needed)
                    ),
                    ephemeral=True,
                )

        # Verifica cargo bloqueado
        if gw.get("roles_bloqueados"):
            member_roles = {r.id for r in inter.user.roles}
            if member_roles & set(gw["roles_bloqueados"]):
                return await inter.response.send_message(
                    embed=error_embed("Participação bloqueada",
                        f"{E.WARN_IC} Você possui um cargo que impede sua participação."
                    ),
                    ephemeral=True,
                )

        # Conta entradas (bonus por cargo)
        entradas = 1
        if gw.get("bonus_entries"):
            for rid, mult in gw["bonus_entries"].items():
                r = inter.guild.get_role(int(rid))
                if r and r in inter.user.roles:
                    entradas = max(entradas, int(mult))

        try:
            await inter.message.add_reaction(GIVEAWAY_EMOJI)
        except Exception:
            pass

        await inter.response.send_message(
            embed=discord.Embed(
                description=(
                    f"{E.HEART_ANIM} Você está participando do sorteio de **{gw['premio']}**!\n"
                    + (f"{E.MAGIC} Suas entradas: **{entradas}x**\n" if entradas > 1 else "")
                    + f"{E.LOADING} Boa sorte! {E.BOT_ANIME}"
                ),
                color=Colors.SUCCESS,
            ),
            ephemeral=True,
        )


# ── Builder de sorteio (estilo Loritta) ───────────────────────────────────────

class GiveawayBuilder:
    """Estado do sorteio sendo configurado antes de iniciar."""
    def __init__(self, host: discord.Member):
        self.host            = host
        self.premio          = "Prêmio do Sorteio"
        self.descricao       = None
        self.imagem          = None
        self.thumbnail       = None
        self.cor             = 0x29a6fe
        self.vencedores      = 1
        self.duracao_secs    = 3600        # 1h padrão
        self.roles_permitidos: list[int] = []
        self.roles_bloqueados: list[int] = []
        self.bonus_entries: dict[str, int] = {}

    def to_dict(self) -> dict:
        return {
            "host_id":         self.host.id,
            "premio":          self.premio,
            "descricao":       self.descricao,
            "imagem":          self.imagem,
            "thumbnail":       self.thumbnail,
            "cor":             self.cor,
            "vencedores":      self.vencedores,
            "encerra_em":      datetime.now(tz=timezone.utc) + timedelta(seconds=self.duracao_secs),
            "roles_permitidos": self.roles_permitidos or None,
            "roles_bloqueados": self.roles_bloqueados or None,
            "bonus_entries":   self.bonus_entries,
            "encerrado":       False,
        }

    def preview_embed(self, guild: discord.Guild) -> discord.Embed:
        d = self.to_dict()
        d["id"] = "preview"
        return _giveaway_embed(d, guild)


# Modals de edição
class AparenciaModal(discord.ui.Modal, title="Aparência do Sorteio"):
    nome_f  = discord.ui.TextInput(label="Nome do Sorteio",       max_length=100)
    desc_f  = discord.ui.TextInput(label="Descrição (opcional)",  required=False,
                                    style=discord.TextStyle.paragraph, max_length=500)
    img_f   = discord.ui.TextInput(label="URL da Imagem (opcional)", required=False, max_length=500)
    thumb_f = discord.ui.TextInput(label="URL da Thumbnail (opcional)", required=False, max_length=500)
    cor_f   = discord.ui.TextInput(label="Cor hex (ex: #29a6fe)", required=False,
                                    default="#29a6fe", max_length=9)

    def __init__(self, builder: GiveawayBuilder):
        super().__init__()
        self.builder        = builder
        self.nome_f.default  = builder.premio
        self.desc_f.default  = builder.descricao or ""
        self.img_f.default   = builder.imagem or ""
        self.thumb_f.default = builder.thumbnail or ""
        self.cor_f.default   = f"#{builder.cor:06X}"

    async def on_submit(self, inter: discord.Interaction):
        self.builder.premio    = self.nome_f.value.strip()
        self.builder.descricao = self.desc_f.value.strip() or None
        self.builder.imagem    = self.img_f.value.strip() or None
        self.builder.thumbnail = self.thumb_f.value.strip() or None
        try:
            self.builder.cor = int(self.cor_f.value.strip().lstrip("#"), 16)
        except ValueError:
            pass
        await inter.response.send_message(
            embed=success_embed("Aparência atualizada!",
                f"{E.GIRL_1} Preview atualizado. Clique em **Iniciar Sorteio** quando estiver pronto."
            ),
            ephemeral=True,
        )


class GeralModal(discord.ui.Modal, title="Configurações Gerais"):
    duracao_f   = discord.ui.TextInput(label="Duração (ex: 30m, 2h, 1d, 1w)",
                                        default="1h", max_length=10)
    vencedores_f = discord.ui.TextInput(label="Número de vencedores", default="1", max_length=3)

    def __init__(self, builder: GiveawayBuilder):
        super().__init__()
        self.builder = builder

    async def on_submit(self, inter: discord.Interaction):
        unidades = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
        try:
            v = self.duracao_f.value.strip()
            secs = int(v[:-1]) * unidades[v[-1].lower()]
            if secs < 60:
                raise ValueError
            self.builder.duracao_secs = secs
        except (ValueError, KeyError, IndexError):
            return await inter.response.send_message(
                embed=error_embed("Duração inválida", "Use: `30m`, `2h`, `1d`, `1w`. Mínimo: 1 minuto."),
                ephemeral=True,
            )
        try:
            n = int(self.vencedores_f.value.strip())
            if 1 <= n <= 20:
                self.builder.vencedores = n
        except ValueError:
            pass
        await inter.response.send_message(
            embed=success_embed("Configurações salvas!",
                f"{E.CALENDAR} Duração: `{self.duracao_f.value}`\n"
                f"{E.CROWN_PINK} Vencedores: `{self.builder.vencedores}`"
            ),
            ephemeral=True,
        )


# ── View principal do builder ─────────────────────────────────────────────────

class GiveawayBuilderView(discord.ui.View):
    def __init__(self, builder: GiveawayBuilder, canal: discord.TextChannel):
        super().__init__(timeout=300)
        self.builder = builder
        self.canal   = canal

    async def interaction_check(self, inter: discord.Interaction) -> bool:
        if inter.user.id != self.builder.host.id:
            await inter.response.send_message(
                f"{E.WARN_IC} Apenas quem criou o sorteio pode configurá-lo.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="🎨 Aparência", style=discord.ButtonStyle.primary, row=0)
    async def aparencia(self, inter: discord.Interaction, _):
        await inter.response.send_modal(AparenciaModal(self.builder))

    @discord.ui.button(label="⚙️ Geral", style=discord.ButtonStyle.primary, row=0)
    async def geral(self, inter: discord.Interaction, _):
        await inter.response.send_modal(GeralModal(self.builder))

    @discord.ui.button(label="🛡️ Cargos", style=discord.ButtonStyle.secondary, row=1)
    async def cargos(self, inter: discord.Interaction, _):
        await inter.response.send_message(
            embed=discord.Embed(
                title=f"{E.TICKET_IC} Cargos Permitidos/Bloqueados",
                description=(
                    f"Use os subcomandos para configurar restrições:\n\n"
                    f"{E.ARROW_BLUE} `/giveaway cargo-permitir @cargo` — só este cargo participa\n"
                    f"{E.ARROW_RED} `/giveaway cargo-bloquear @cargo` — este cargo não participa\n\n"
                    f"*Esta funcionalidade será aplicada ao próximo sorteio que você iniciar.*"
                ),
                color=Colors.MAIN,
            ),
            ephemeral=True,
        )

    @discord.ui.button(label="✨ Entradas Extras", style=discord.ButtonStyle.secondary, row=1)
    async def extras(self, inter: discord.Interaction, _):
        await inter.response.send_message(
            embed=discord.Embed(
                title=f"{E.MAGIC} Entradas Extras",
                description=(
                    f"Use `/giveaway bonus-entrada @cargo multiplicador` para dar mais chances a um cargo.\n\n"
                    f"{E.SPARKLE} Exemplo: `@VIP 3x` → membros VIP têm 3 entradas no sorteio."
                ),
                color=Colors.MAIN,
            ),
            ephemeral=True,
        )

    @discord.ui.button(label="👁️ Preview", style=discord.ButtonStyle.secondary, row=2)
    async def preview(self, inter: discord.Interaction, _):
        emb = self.builder.preview_embed(inter.guild)
        await inter.response.send_message(
            content=f"{E.GHOST} **Preview do sorteio:**",
            embed=emb, ephemeral=True,
        )

    @discord.ui.button(label="🎉 Iniciar Sorteio", style=discord.ButtonStyle.success, row=2)
    async def iniciar(self, inter: discord.Interaction, _):
        await inter.response.defer(ephemeral=True)
        cog = inter.client.cogs.get("Giveaway")
        if cog:
            await cog._publicar_sorteio(inter, self.builder, self.canal)
        self.stop()


# ── Cog principal ─────────────────────────────────────────────────────────────

class Giveaway(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot    = bot
        self._tasks: dict[int, asyncio.Task] = {}

    async def cog_load(self):
        await _ensure_table()
        await self._restore_giveaways()

    async def _restore_giveaways(self):
        agora = datetime.now(tz=timezone.utc)
        async with get_pool().acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM giveaways WHERE encerrado=FALSE AND encerra_em > $1", agora
            )
        self.bot.add_view(GiveawayJoinView())
        for row in rows:
            gw = dict(row)
            if isinstance(gw.get("bonus_entries"), str):
                import json
                gw["bonus_entries"] = json.loads(gw["bonus_entries"])
            self._tasks[gw["id"]] = asyncio.create_task(
                self._aguardar(gw)
            )
        log.info(f"[GIVEAWAY] {len(rows)} sorteio(s) restaurado(s).")

    async def _aguardar(self, gw: dict):
        agora    = datetime.now(tz=timezone.utc)
        restante = (gw["encerra_em"] - agora).total_seconds()
        if restante > 0:
            await asyncio.sleep(restante)
        await self._encerrar(gw["id"])

    async def _publicar_sorteio(self, inter: discord.Interaction,
                                  builder: GiveawayBuilder, canal: discord.TextChannel):
        gw_dict  = builder.to_dict()
        guild    = inter.guild

        # Salva no banco
        import json
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO giveaways
                  (guild_id, channel_id, host_id, premio, descricao, imagem, thumbnail,
                   cor, vencedores, encerra_em, roles_permitidos, roles_bloqueados, bonus_entries)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
                RETURNING id
            """,
                guild.id, canal.id, builder.host.id, builder.premio,
                builder.descricao, builder.imagem, builder.thumbnail,
                builder.cor, builder.vencedores, gw_dict["encerra_em"],
                builder.roles_permitidos or None,
                builder.roles_bloqueados or None,
                json.dumps({str(k): v for k, v in builder.bonus_entries.items()}),
            )
        gid = row["id"]
        gw_dict["id"] = gid

        emb  = _giveaway_embed(gw_dict, guild)
        view = GiveawayJoinView()
        msg  = await canal.send(embed=emb, view=view)
        try:
            await msg.add_reaction(GIVEAWAY_EMOJI)
        except Exception:
            pass

        async with get_pool().acquire() as conn:
            await conn.execute("UPDATE giveaways SET message_id=$1 WHERE id=$2", msg.id, gid)
        gw_dict["message_id"] = msg.id

        self._tasks[gid] = asyncio.create_task(self._aguardar(gw_dict))

        await inter.followup.send(
            embed=success_embed("Sorteio iniciado!",
                f"{E.BOT_ANIME} Sorteio de **{builder.premio}** publicado em {canal.mention}!\n"
                f"{E.LOADING} Encerra {discord.utils.format_dt(gw_dict['encerra_em'], 'R')}\n"
                f"{E.CROWN_PINK} Vencedores: `{builder.vencedores}`\n"
                f"{E.SYMBOL} ID: `{gid}`"
            ),
            ephemeral=True,
        )

    async def _encerrar(self, giveaway_id: int):
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM giveaways WHERE id=$1", giveaway_id)
            if not row or row["encerrado"]:
                return
            await conn.execute("UPDATE giveaways SET encerrado=TRUE WHERE id=$1", giveaway_id)

        import json
        gw      = dict(row)
        if isinstance(gw.get("bonus_entries"), str):
            gw["bonus_entries"] = json.loads(gw["bonus_entries"])

        guild   = self.bot.get_guild(gw["guild_id"])
        if not guild:
            return
        channel = guild.get_channel(gw["channel_id"])
        if not isinstance(channel, discord.TextChannel):
            return

        try:
            msg = await channel.fetch_message(gw["message_id"])
        except discord.HTTPException:
            return

        # Coleta participantes via reação
        participantes = []
        for reaction in msg.reactions:
            if str(reaction.emoji) == GIVEAWAY_EMOJI:
                async for user in reaction.users():
                    if user.bot or user.id == gw["host_id"]:
                        continue
                    # Aplica entradas extras
                    entradas = 1
                    member = guild.get_member(user.id)
                    if member and gw.get("bonus_entries"):
                        for rid, mult in gw["bonus_entries"].items():
                            r = guild.get_role(int(rid))
                            if r and r in member.roles:
                                entradas = max(entradas, int(mult))
                    for _ in range(entradas):
                        participantes.append(user)
                break

        n = gw["vencedores"]
        if participantes:
            # Remove duplicatas mantendo peso
            vencedores = random.sample(list(set(participantes)), min(n, len(set(participantes))))
            mencoes    = " ".join(v.mention for v in vencedores)
            desc = (
                f"{E.HEART_ANIM} **Parabéns aos vencedores!**\n{mencoes}\n\n"
                f"{E.STAR} **Prêmio:** {gw['premio']}\n"
                f"{E.STAFF} **Sorteado por:** <@{gw['host_id']}>"
            )
        else:
            mencoes = None
            desc = (
                f"{E.GHOST} Nenhum participante elegível.\n\n"
                f"{E.STAR} **Prêmio:** {gw['premio']}"
            )

        gw["encerrado"] = True
        emb_final = discord.Embed(
            title=f"{E.BOT_ANIME}  SORTEIO ENCERRADO — {gw['premio']}",
            description=desc,
            color=0x99AAB5,
        )
        if gw.get("thumbnail"):
            emb_final.set_thumbnail(url=gw["thumbnail"])
        emb_final.set_footer(text=f"Encerrado • ID: {giveaway_id}")
        emb_final.timestamp = _now()

        try:
            await msg.edit(embed=emb_final, view=None)
            if mencoes:
                await channel.send(
                    content=f"{GIVEAWAY_EMOJI} {mencoes} **ganharam {gw['premio']}!**"
                )
        except discord.HTTPException:
            pass

    # ── Slash commands ─────────────────────────────────────────────────────

    gv_group = app_commands.Group(
        name="giveaway",
        description="Sistema de sorteios",
        default_permissions=discord.Permissions(manage_guild=True),
    )

    @gv_group.command(name="criar", description="Abre o painel de configuração do sorteio (estilo Loritta)")
    @app_commands.describe(
        canal="Canal onde o sorteio será publicado",
        premio="Prêmio do sorteio",
    )
    async def gv_criar(self, inter: discord.Interaction,
                        canal: discord.TextChannel,
                        premio: str):
        builder         = GiveawayBuilder(inter.user)
        builder.premio  = premio
        view            = GiveawayBuilderView(builder, canal)

        emb = discord.Embed(
            title=f"{E.BOT_ANIME} Configurar Sorteio",
            description=(
                f"{E.HEART_ANIM} Configure seu sorteio antes de publicar!\n\n"
                f"{E.ARROW_BLUE} **🎨 Aparência** — nome, descrição, imagem, cor\n"
                f"{E.ARROW_BLUE} **⚙️ Geral** — duração e número de vencedores\n"
                f"{E.ARROW_BLUE} **🛡️ Cargos** — restringir quem pode participar\n"
                f"{E.ARROW_BLUE} **✨ Entradas Extras** — dar mais chances a cargos VIP\n"
                f"{E.ARROW_BLUE} **👁️ Preview** — veja como ficará antes de publicar\n\n"
                f"{E.MAGIC} Canal selecionado: {canal.mention}\n"
                f"{E.STAR} Prêmio: **{premio}**"
            ),
            color=0x29a6fe,
        )
        emb.set_thumbnail(url=inter.user.display_avatar.url)
        emb.set_footer(text="Clique em 🎉 Iniciar Sorteio quando estiver pronto!")
        emb.timestamp = _now()
        await inter.response.send_message(embed=emb, view=view, ephemeral=True)

    @gv_group.command(name="encerrar", description="Encerra um sorteio antecipadamente")
    @app_commands.describe(giveaway_id="ID do sorteio")
    async def gv_encerrar(self, inter: discord.Interaction, giveaway_id: int):
        await inter.response.defer(ephemeral=True)
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM giveaways WHERE id=$1 AND guild_id=$2 AND encerrado=FALSE",
                giveaway_id, inter.guild.id,
            )
        if not row:
            return await inter.followup.send(
                embed=error_embed("Não encontrado", f"Sorteio `{giveaway_id}` não existe ou já encerrou."),
                ephemeral=True,
            )
        task = self._tasks.pop(giveaway_id, None)
        if task:
            task.cancel()
        await self._encerrar(giveaway_id)
        await inter.followup.send(
            embed=success_embed("Encerrado!", f"{E.BOT_ANIME} Sorteio `{giveaway_id}` encerrado."),
            ephemeral=True,
        )

    @gv_group.command(name="resorteio", description="Resorteia vencedores de um sorteio encerrado")
    @app_commands.describe(giveaway_id="ID do sorteio")
    async def gv_resorteio(self, inter: discord.Interaction, giveaway_id: int):
        await inter.response.defer()
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM giveaways WHERE id=$1 AND guild_id=$2 AND encerrado=TRUE",
                giveaway_id, inter.guild.id,
            )
        if not row:
            return await inter.followup.send(
                embed=error_embed("Não encontrado", "Sorteio não encontrado ou ainda ativo."), ephemeral=True
            )

        channel = inter.guild.get_channel(row["channel_id"])
        if not isinstance(channel, discord.TextChannel):
            return await inter.followup.send(embed=error_embed("Canal não encontrado", ""), ephemeral=True)

        try:
            msg = await channel.fetch_message(row["message_id"])
        except discord.HTTPException:
            return await inter.followup.send(embed=error_embed("Mensagem não encontrada", ""), ephemeral=True)

        participantes = []
        for reaction in msg.reactions:
            if str(reaction.emoji) == GIVEAWAY_EMOJI:
                async for user in reaction.users():
                    if not user.bot and user.id != row["host_id"]:
                        participantes.append(user)
                break

        if not participantes:
            return await inter.followup.send(
                embed=error_embed("Sem participantes", "Nenhum participante elegível."), ephemeral=True
            )

        n          = row["vencedores"]
        vencedores = random.sample(participantes, min(n, len(participantes)))
        mencoes    = " ".join(v.mention for v in vencedores)

        emb = discord.Embed(
            title=f"{E.BOT_ANIME} RESORTEIO — {row['premio']}",
            description=(
                f"{E.HEART_ANIM} **Novos vencedores:**\n{mencoes}\n\n"
                f"{E.STAR} **Prêmio:** {row['premio']}\n"
                f"{E.GHOST} Resorteado por {inter.user.mention}"
            ),
            color=Colors.SUCCESS,
        )
        if row.get("thumbnail"):
            emb.set_thumbnail(url=row["thumbnail"])
        emb.set_footer(text=f"Resorteio • ID: {giveaway_id}")
        emb.timestamp = _now()
        await inter.followup.send(content=mencoes, embed=emb)

    @gv_group.command(name="lista", description="Lista todos os sorteios ativos")
    async def gv_lista(self, inter: discord.Interaction):
        async with get_pool().acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM giveaways WHERE guild_id=$1 AND encerrado=FALSE ORDER BY encerra_em",
                inter.guild.id,
            )
        if not rows:
            return await inter.response.send_message(
                embed=error_embed("Sem sorteios", f"{E.GHOST} Nenhum sorteio ativo."), ephemeral=True
            )
        emb = discord.Embed(
            title=f"{E.BOT_ANIME} Sorteios Ativos",
            color=0x29a6fe,
        )
        for row in rows:
            ch = inter.guild.get_channel(row["channel_id"])
            emb.add_field(
                name=f"`#{row['id']}` {row['premio']}",
                value=(
                    f"{E.ARROW_BLUE} Canal: {ch.mention if ch else '?'}\n"
                    f"{E.LOADING} Encerra: {discord.utils.format_dt(row['encerra_em'], 'R')}\n"
                    f"{E.CROWN_PINK} Vencedores: `{row['vencedores']}`"
                ),
                inline=False,
            )
        emb.timestamp = _now()
        await inter.response.send_message(embed=emb, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Giveaway(bot))
