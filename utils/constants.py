"""utils/constants.py — Constantes globais do bot."""

import discord
from datetime import datetime, timezone


class Colors:
    MAIN    = 0x590CEA
    SUCCESS = 0x57F287
    ERROR   = 0xED4245
    WARN    = 0xFEE75C
    INFO    = 0x5865F2


class E:
    # ── Emojis originais ──────────────────────────────────────────────────
    HEART      = "<a:1000006091:1475984862140825833>"
    STAR       = "<a:1000006093:1475982082709655714>"
    LOADING    = "<a:1000006103:1475984937835565227>"
    DECO_BOX   = "<a:1000006120:1475985083818053642>"
    ENVELOPE   = "<a:1000006121:1475984619638620221>"
    MASCOT     = "<:1000006124:1475984717751783617>"   # mascote estática original
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

    # ── Novos emojis (adicionados em 16/03/2026) ──────────────────────────
    # Estáticos — ordem da imagem enviada
    GIRL_1     = "<:1000011430:1483272588066029739>"   # personagem anime (cabelo escuro)
    GIRL_2     = "<:1000011429:1483272519522848849>"   # personagem anime (variação)
    GIRL_3     = "<:1000011428:1483272436152668200>"   # personagem anime (variação 2)
    ROBOT      = "<:1000010960:1483264006318985309>"   # robozinho/mascote
    BEAR       = "<:1000011332:1483263779813855243>"   # ursinho/pelúcia
    MAGIC      = "<:1000011389:1483262474529804419>"   # varinha/magia
    TICKET_IC  = "<:1000011407:1483262387329962104>"   # ícone de ticket/notificação

    # Animados — ordem da imagem enviada
    CLOUD_ANIM = "<a:1000011270:1483263576406884363>"  # nuvem animada
    HEART_ANIM = "<a:1000011289:1483263381141061692>"  # coração animado
    NUM_9      = "<a:1000011312:1483263288505536614>"  # número 9 animado
    NUM_8      = "<a:1000011308:1483263242473312379>"  # número 8 animado
    NUM_7      = "<a:1000011307:1483263198600888401>"  # número 7 animado
    NUM_6      = "<a:1000011311:1483263136978178048>"  # número 6 animado
    NUM_5      = "<a:1000011306:1483263090232660058>"  # número 5 animado
    NUM_4      = "<a:1000011309:1483263046024560723>"  # número 4 animado
    NUM_3      = "<a:1000011305:1483263009945026590>"  # número 3 animado
    NUM_2      = "<a:1000011304:1483262967590944948>"  # número 2 animado
    NUM_1      = "<a:1000011310:1483262926914850827>"  # número 1 animado
    GHOST      = "<a:1000011327:1483262845591486617>"  # fantasminha animado
    WAND       = "<a:1000011373:1483262524823703728>"  # varinha animada
    BOT_ANIME  = "<a:1000011410:1483262418715938949>"  # mascote anime animada do bot ⭐
    CHIBI_2    = "<a:1000011285:1483262344460112003>"  # chibi animado

    # ── Aliases ───────────────────────────────────────────────────────────
    INFO_IC      = SYMBOL
    SETTINGS     = SNOWFLAKE
    STAFF        = CALENDAR
    BRANCORE     = ANNOUNCE
    BRANXO       = ANNOUNCE
    ARROW_BLUE   = ARROW
    ARROW_GREEN  = ARROW_W
    ARROW_RED    = WARN_IC
    ARROW_ORANGE = ARROW
    ARROW_YELLOW = ARROW_W
    # Mascote principal = anime animada (mais expressiva)
    BOT_ICON     = BOT_ANIME


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def success_embed(title: str, description: str = "") -> discord.Embed:
    e = discord.Embed(title=f"{E.VERIFY} {title}", description=description, color=Colors.MAIN)
    e.timestamp = _now()
    return e


def error_embed(title: str, description: str = "") -> discord.Embed:
    e = discord.Embed(title=f"{E.WARN_IC} {title}", description=description, color=Colors.ERROR)
    e.timestamp = _now()
    return e


def mod_embed(title: str, description: str = "") -> discord.Embed:
    e = discord.Embed(title=title, description=description, color=Colors.MAIN)
    e.timestamp = _now()
    return e


def info_embed(title: str, description: str = "") -> discord.Embed:
    e = discord.Embed(title=f"{E.SYMBOL} {title}", description=description, color=Colors.INFO)
    e.timestamp = _now()
    return e
