"""
cogs/musica.py — Sistema de música via yt-dlp + FFmpegPCMAudio.
FFmpeg é instalado via nixpacks.toml — disponível em /usr/bin/ffmpeg no Railway.
"""

import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import random
import logging
import shutil

from utils.constants import Colors, E, success_embed, error_embed, _now

log = logging.getLogger("multibot.musica")

# ── Verifica disponibilidade ──────────────────────────────────────────────────
try:
    import yt_dlp
    _YTDLP = True
except ImportError:
    _YTDLP = False
    log.warning("[MÚSICA] yt-dlp não instalado.")

# FFmpeg: procura em locais comuns no Railway/Nix
_FFMPEG_PATH = (
    shutil.which("ffmpeg")
    or "/usr/bin/ffmpeg"
    or "/run/current-system/sw/bin/ffmpeg"
)
_FFMPEG = bool(shutil.which("ffmpeg") or _FFMPEG_PATH)

FFMPEG_OPTIONS = {
    "executable": _FFMPEG_PATH or "ffmpeg",
    "before_options": (
        "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 "
        "-reconnect_at_eof 1 "
        "-loglevel error"
    ),
    "options": "-vn -bufsize 512k -ar 48000 -ac 2",
}

YDL_BASE = {
    "quiet": True,
    "no_warnings": True,
    "source_address": "0.0.0.0",
    "socket_timeout": 20,
    "ignoreerrors": True,
    # Bypass bloqueio do YouTube em servidores cloud (Railway, etc.)
    "http_headers": {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    },
    "extractor_args": {"youtube": {"player_client": ["ios", "web"]}},
    "age_limit": None,
}


def _unavailable_embed() -> discord.Embed:
    if not _YTDLP:
        return error_embed("yt-dlp não instalado",
            "Execute `pip install yt-dlp` e reinicie o bot.")
    return error_embed("FFmpeg não encontrado",
        f"FFmpeg não está disponível.\nCaminho testado: `{_FFMPEG_PATH}`\n"
        "Verifique o `nixpacks.toml` e faça redeploy.")


# ── Estado por servidor (em memória — fila não precisa persistir) ─────────────
_state: dict[int, dict] = {}


def _get(guild_id: int) -> dict:
    if guild_id not in _state:
        _state[guild_id] = {"queue": [], "loop": False, "volume": 0.5, "current": None}
    return _state[guild_id]


def _fmt(seconds: int | float) -> str:
    s = int(seconds or 0)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _src_emoji(url: str) -> str:
    return E.SPOTIFY if "spotify.com" in url else E.YOUTUBE


async def _fetch(query: str) -> dict | None:
    """Busca uma faixa e retorna URL de stream de áudio."""
    if not _YTDLP:
        return None

    # Spotify: converte link para busca no YouTube
    if "spotify.com/track" in query:
        slug  = query.rstrip("/").split("/")[-1].split("?")[0]
        query = slug.replace("-", " ")

    opts = {
        **YDL_BASE,
        "format": "bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio/best",
        "noplaylist": True,
        "extract_flat": False,
        # Força uso do cliente iOS que tem menos restrições de região
        "extractor_args": {"youtube": {"player_client": ["ios", "web"]}},
    }

    loop = asyncio.get_running_loop()

    def _run():
        with yt_dlp.YoutubeDL(opts) as ydl:
            search = query if query.startswith("http") else f"ytsearch1:{query}"
            info   = ydl.extract_info(search, download=False)
            if not info:
                return None
            if "entries" in info:
                entries = [e for e in info["entries"] if e]
                info = entries[0] if entries else None
            if not info:
                return None
            url = info.get("url", "")
            if not url:
                for fmt in reversed(info.get("formats", [])):
                    if fmt.get("url") and fmt.get("acodec") != "none":
                        url = fmt["url"]
                        break
            if not url:
                return None
            return {
                "url":         url,
                "title":       info.get("title", "Desconhecido"),
                "duration":    info.get("duration", 0),
                "thumbnail":   info.get("thumbnail"),
                "webpage_url": info.get("webpage_url", query),
                "uploader":    info.get("uploader", ""),
            }

    try:
        return await asyncio.wait_for(loop.run_in_executor(None, _run), timeout=35.0)
    except asyncio.TimeoutError:
        log.warning(f"[MÚSICA] Timeout ao buscar: {query}")
        return None
    except Exception as exc:
        log.warning(f"[MÚSICA] Erro ao buscar '{query}': {exc}")
        return None


async def _fetch_playlist(url: str) -> list[dict]:
    if not _YTDLP:
        return []
    opts = {**YDL_BASE, "noplaylist": False, "extract_flat": True}
    loop = asyncio.get_running_loop()

    def _run():
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

    try:
        info = await asyncio.wait_for(loop.run_in_executor(None, _run), timeout=45.0)
        if not info:
            return []
        entries = info.get("entries", [info])
        return [
            {
                "url":         e.get("url") or e.get("webpage_url", ""),
                "title":       e.get("title", "Desconhecido"),
                "duration":    e.get("duration", 0),
                "thumbnail":   e.get("thumbnail"),
                "webpage_url": e.get("webpage_url") or e.get("url", ""),
                "uploader":    e.get("uploader", ""),
            }
            for e in entries if e
        ]
    except Exception:
        return []


def _play_next(guild_id: int, vc: discord.VoiceClient):
    """Callback após fim de faixa — agenda próxima no event loop."""
    async def _next():
        st = _get(guild_id)
        if st["loop"] and st["current"]:
            track = st["current"]
        elif st["queue"]:
            track = st["queue"].pop(0)
            st["current"] = track
        else:
            st["current"] = None
            return

        # Faixas de playlist podem não ter URL de stream ainda
        if not (track.get("url") or "").startswith("http"):
            fetched = await _fetch(track.get("webpage_url") or track.get("url", ""))
            if not fetched:
                st["current"] = None
                if st["queue"]:
                    _play_next(guild_id, vc)
                return
            track = fetched
            st["current"] = track

        try:
            source = discord.PCMVolumeTransformer(
                discord.FFmpegPCMAudio(track["url"], **FFMPEG_OPTIONS),
                volume=st["volume"],
            )
            vc.play(source, after=lambda e: _play_next(guild_id, vc) if not e else None)
        except Exception as exc:
            log.warning(f"[MÚSICA] Erro ao iniciar faixa: {exc}")

    try:
        loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(_next(), loop)
    except Exception as exc:
        log.warning(f"[MÚSICA] _play_next erro: {exc}")


class Musica(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _vc_check(self, inter: discord.Interaction) -> discord.VoiceClient | None:
        return inter.guild.voice_client

    musica_group = app_commands.Group(
        name="musica",
        description="Sistema de música",
    )

    @musica_group.command(name="tocar", description="Toca uma música ou playlist (YouTube/Spotify)")
    @app_commands.describe(musica="Nome, link do YouTube ou link do Spotify")
    async def tocar(self, inter: discord.Interaction, musica: str):
        if not _YTDLP or not _FFMPEG:
            return await inter.response.send_message(embed=_unavailable_embed(), ephemeral=True)

        if not inter.user.voice or not inter.user.voice.channel:
            return await inter.response.send_message(
                embed=error_embed("Sem canal de voz", "Você precisa estar em um canal de voz!"),
                ephemeral=True,
            )

        await inter.response.defer()

        vc = inter.guild.voice_client
        if not vc:
            try:
                vc = await inter.user.voice.channel.connect()
            except Exception as exc:
                return await inter.followup.send(
                    embed=error_embed("Erro de conexão", str(exc)), ephemeral=True
                )
        elif vc.channel != inter.user.voice.channel:
            await vc.move_to(inter.user.voice.channel)

        st = _get(inter.guild.id)

        is_playlist = any(x in musica for x in [
            "youtube.com/playlist", "list=", "spotify.com/playlist", "spotify.com/album"
        ])

        if is_playlist:
            tracks = await _fetch_playlist(musica)
            if not tracks:
                return await inter.followup.send(
                    embed=error_embed("Playlist não encontrada", "Verifique o link e tente novamente."),
                    ephemeral=True,
                )
            st["queue"].extend(tracks)
            emb = discord.Embed(
                title=f"{_src_emoji(musica)} Playlist adicionada!",
                description=(
                    f"{E.SPARKLE} **{len(tracks)}** faixas adicionadas à fila.\n"
                    f"{E.ARROW_BLUE} Use `/musica fila` para ver todas."
                ),
                color=Colors.MAIN,
            )
            emb.timestamp = _now()
            await inter.followup.send(embed=emb)

            # Inicia se não estiver tocando
            if not vc.is_playing() and not vc.is_paused() and st["queue"]:
                track = st["queue"].pop(0)
                fetched = await _fetch(track.get("webpage_url") or track.get("url", ""))
                if fetched:
                    st["current"] = fetched
                    source = discord.PCMVolumeTransformer(
                        discord.FFmpegPCMAudio(fetched["url"], **FFMPEG_OPTIONS),
                        volume=st["volume"],
                    )
                    vc.play(source, after=lambda e: _play_next(inter.guild.id, vc) if not e else None)
            return

        # Faixa única
        track = await _fetch(musica)
        if not track:
            return await inter.followup.send(
                embed=error_embed("Não encontrado",
                    f"Não encontrei `{musica}`.\n"
                    "Verifique o link ou tente outro nome."
                ),
                ephemeral=True,
            )

        if vc.is_playing() or vc.is_paused():
            st["queue"].append(track)
            emb = discord.Embed(
                title=f"{_src_emoji(track['webpage_url'])} Adicionado à fila",
                description=(
                    f"{E.ARROW_BLUE} **[{track['title']}]({track['webpage_url']})**\n"
                    f"{E.STAR} Duração: `{_fmt(track['duration'])}`\n"
                    f"{E.SYMBOL} Posição: `#{len(st['queue'])}`"
                ),
                color=Colors.MAIN,
            )
            if track["thumbnail"]:
                emb.set_thumbnail(url=track["thumbnail"])
            emb.timestamp = _now()
            return await inter.followup.send(embed=emb)

        st["current"] = track
        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(track["url"], **FFMPEG_OPTIONS),
            volume=st["volume"],
        )
        vc.play(source, after=lambda e: _play_next(inter.guild.id, vc) if not e else None)

        emb = discord.Embed(
            title=f"{_src_emoji(track['webpage_url'])} Tocando agora",
            description=(
                f"{E.ARROW_BLUE} **[{track['title']}]({track['webpage_url']})**\n"
                f"{E.STAR} Duração: `{_fmt(track['duration'])}`\n"
                f"{E.MASCOT} Canal: `{track['uploader']}`\n"
                f"{E.GEM} Volume: `{int(st['volume'] * 100)}%`"
            ),
            color=Colors.MAIN,
        )
        if track["thumbnail"]:
            emb.set_image(url=track["thumbnail"])
        emb.set_footer(text=f"{inter.guild.name} • Música")
        emb.timestamp = _now()
        await inter.followup.send(embed=emb)

    @musica_group.command(name="pausar", description="Pausa a música atual")
    async def pausar(self, inter: discord.Interaction):
        vc = self._vc_check(inter)
        if not vc or not vc.is_playing():
            return await inter.response.send_message(
                embed=error_embed("Erro", "Nenhuma música tocando."), ephemeral=True
            )
        vc.pause()
        await inter.response.send_message(embed=success_embed("Pausado", f"{E.LOADING} Use `/musica retomar`."))

    @musica_group.command(name="retomar", description="Retoma a música pausada")
    async def retomar(self, inter: discord.Interaction):
        vc = self._vc_check(inter)
        if not vc or not vc.is_paused():
            return await inter.response.send_message(
                embed=error_embed("Erro", "Nenhuma música pausada."), ephemeral=True
            )
        vc.resume()
        await inter.response.send_message(embed=success_embed("Retomado", f"{E.SPARKLE} Música retomada!"))

    @musica_group.command(name="pular", description="Pula para a próxima música da fila")
    async def pular(self, inter: discord.Interaction):
        vc = self._vc_check(inter)
        if not vc or (not vc.is_playing() and not vc.is_paused()):
            return await inter.response.send_message(
                embed=error_embed("Erro", "Nenhuma música tocando."), ephemeral=True
            )
        _get(inter.guild.id)["loop"] = False
        vc.stop()
        await inter.response.send_message(embed=success_embed("Pulado", f"{E.ARROW_BLUE} Próxima música!"))

    @musica_group.command(name="parar", description="Para a música e limpa a fila")
    async def parar(self, inter: discord.Interaction):
        vc = self._vc_check(inter)
        if not vc:
            return await inter.response.send_message(
                embed=error_embed("Erro", "Bot não está em nenhum canal."), ephemeral=True
            )
        st = _get(inter.guild.id)
        st["queue"].clear()
        st["current"] = None
        st["loop"]    = False
        vc.stop()
        await inter.response.send_message(embed=success_embed("Parado", f"{E.FLAME_PUR} Fila limpa."))

    @musica_group.command(name="sair", description="Desconecta o bot do canal de voz")
    async def sair(self, inter: discord.Interaction):
        vc = self._vc_check(inter)
        if not vc:
            return await inter.response.send_message(
                embed=error_embed("Erro", "Bot não está em nenhum canal."), ephemeral=True
            )
        st = _get(inter.guild.id)
        st["queue"].clear()
        st["current"] = None
        await vc.disconnect()
        await inter.response.send_message(embed=success_embed("Saí do canal", f"{E.LEAF} Até logo! {E.HEARTS_S}"))

    @musica_group.command(name="volume", description="Ajusta o volume (1–100)")
    @app_commands.describe(nivel="Volume de 1 a 100")
    async def volume(self, inter: discord.Interaction, nivel: app_commands.Range[int, 1, 100]):
        vc = self._vc_check(inter)
        st = _get(inter.guild.id)
        st["volume"] = nivel / 100
        if vc and vc.source:
            vc.source.volume = st["volume"]
        await inter.response.send_message(
            embed=success_embed("Volume", f"{E.GEM} Volume: `{nivel}%`.")
        )

    @musica_group.command(name="repetir", description="Ativa/desativa repetição da música atual")
    async def repetir(self, inter: discord.Interaction):
        st = _get(inter.guild.id)
        st["loop"] = not st["loop"]
        status = "Ativada" if st["loop"] else "Desativada"
        await inter.response.send_message(
            embed=success_embed(f"Repetição {status}", f"{E.RING} Repetição **{status.lower()}**.")
        )

    @musica_group.command(name="embaralhar", description="Embaralha a fila de músicas")
    async def embaralhar(self, inter: discord.Interaction):
        st = _get(inter.guild.id)
        if not st["queue"]:
            return await inter.response.send_message(
                embed=error_embed("Fila vazia", "Sem músicas para embaralhar."), ephemeral=True
            )
        random.shuffle(st["queue"])
        await inter.response.send_message(
            embed=success_embed("Embaralhado", f"{E.SPARKLE} `{len(st['queue'])}` músicas embaralhadas!")
        )

    @musica_group.command(name="fila", description="Mostra a fila de músicas")
    async def fila(self, inter: discord.Interaction):
        st      = _get(inter.guild.id)
        current = st.get("current")
        queue   = st.get("queue", [])
        if not current and not queue:
            return await inter.response.send_message(
                embed=error_embed("Fila vazia", "Nenhuma música na fila."), ephemeral=True
            )
        parts = []
        if current:
            emoji = _src_emoji(current["webpage_url"])
            parts.append(
                f"{emoji} **Tocando agora:**\n"
                f"{E.ARROW_BLUE} [{current['title']}]({current['webpage_url']}) — `{_fmt(current['duration'])}`\n"
            )
        if queue:
            parts.append(f"{E.STAR} **Próximas ({len(queue)}):**")
            for i, t in enumerate(queue[:10], 1):
                parts.append(f"`{i}.` {_src_emoji(t['webpage_url'])} [{t['title']}]({t['webpage_url']}) — `{_fmt(t['duration'])}`")
            if len(queue) > 10:
                parts.append(f"\n{E.SYMBOL} *...e mais {len(queue)-10} música(s)*")
        emb = discord.Embed(title=f"{E.GEM_SHINE} Fila", description="\n".join(parts), color=Colors.MAIN)
        emb.set_footer(text=f"Repetir: {'On' if st['loop'] else 'Off'} • Volume: {int(st['volume']*100)}%")
        emb.timestamp = _now()
        await inter.response.send_message(embed=emb)

    @musica_group.command(name="tocando", description="Mostra a música tocando agora")
    async def tocando(self, inter: discord.Interaction):
        vc = self._vc_check(inter)
        if not vc or not vc.is_playing():
            return await inter.response.send_message(
                embed=error_embed("Nada tocando", "Nenhuma música está tocando."), ephemeral=True
            )
        st      = _get(inter.guild.id)
        current = st.get("current")
        if not current:
            return await inter.response.send_message(
                embed=error_embed("Nada tocando", "Nenhuma música está tocando."), ephemeral=True
            )
        emb = discord.Embed(
            title=f"{_src_emoji(current['webpage_url'])} Tocando agora",
            description=(
                f"{E.ARROW_BLUE} **[{current['title']}]({current['webpage_url']})**\n"
                f"{E.STAR} Duração: `{_fmt(current['duration'])}`\n"
                f"{E.MASCOT} Canal: `{current['uploader']}`\n"
                f"{E.GEM} Volume: `{int(st['volume'] * 100)}%`\n"
                f"{E.RING} Repetir: `{'Ativado' if st['loop'] else 'Desativado'}`\n"
                f"{E.SYMBOL} Fila: `{len(st['queue'])}` música(s)"
            ),
            color=Colors.MAIN,
        )
        if current["thumbnail"]:
            emb.set_image(url=current["thumbnail"])
        emb.set_footer(text=f"{inter.guild.name} • Música")
        emb.timestamp = _now()
        await inter.response.send_message(embed=emb)


async def setup(bot: commands.Bot):
    await bot.add_cog(Musica(bot))
