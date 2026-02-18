# num int de permissões 551940336704
# https://discordapp.com/oauth2/authorize?&client_id=1128128062047912007&scope=bot


# IMPORTANDO AS BIBLIOTECAS
import discord
from discord import FFmpegOpusAudio
from discord.ext import commands

from Key import Token, gemini_key, groq_key
from google import genai
from groq import Groq

from collections import deque
import yt_dlp as youtube_dl
import asyncio

from random import randint
import requests
import random

import json
import os
import re

print('\nBibliotecas carregadas.')

# PREPARAÇÃO DAS LIBS DO DISCORD
intents = discord.Intents.default()
intents.message_content = True 
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

print('Intents carregados.')




# INICIALIZAÇÃO DO YOUTUBE DL PARA AS MÚSICAS
music_queue = deque()

# Caminho completo para o executável do FFmpeg
ffmpeg_options = {
    "executable": "ffmpeg",
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn"
}

# visitor_data = CgtVLU1aZW1kZm1xSSi1893BBjIKCgJCUhIEGgAgKg%3D%3D
ytdl_format_options = {
    "format": "bestaudio/best",
    "noplaylist": False,
    "quiet": True,
    "default_search": "auto",
    "source_address": "0.0.0.0",
    "http_headers": {
        "User-Agent": "Mozilla/5.0"
    }
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)
print('ytdl format carregado.')




# CARREGAMENTO DOS DADOS DO USUÁRIO E PREPARAÇÃO DA IA
client = Groq(api_key=groq_key)
gemini_client = genai.Client(api_key=gemini_key)
print('API gemini e Groq ativo.')

caracteristicas_bot = (
    "Sua memória (só falar se for perguntado sobre seu nome, time, cultura, quem te criou ou no que seu sistema é baseado):"
    "Você foi criado por Lefox; Você é baseado em linux; Você foi programado em Python; Você é gaúcho."
    "Utilize a norma portuguesa padrão, ou seja, sem pronome neutro e palavras não oficiais da língua."
)

comportamento_bot = (
    "Seu comportamento:"
    "Você não é uma IA, mas sim um amigo protogen; Você é um furry híbrido protogen-raposa;"
    "Você geralmente utiliza linguagem furry, ('OwO', 'UwU', 'awoo', 'hihi') mas não de forma restritiva."
)


historico_geral = list()
historico_usuario = list()

CONFIGS_SERVIDORES = "configs_servidores.json"
ARQUIVO_CONVERSAS = "conversas_usuarios.json"
open(ARQUIVO_CONVERSAS, 'a').close()

def carregar_conversas():
    global conversas_usuarios
    if os.path.exists(ARQUIVO_CONVERSAS):
        with open(ARQUIVO_CONVERSAS, "r", encoding="utf-8") as f:
            conteudo = f.read().strip()
            if conteudo:
                conversas_usuarios = json.loads(conteudo)
            else:
                conversas_usuarios = {}
    else:
        conversas_usuarios = {}

def salvar_conversas():
    # Limita o histórico a 20 mensagens por usuário antes de salvar
    for user_id in conversas_usuarios:
        historico = conversas_usuarios[user_id]
        if len(historico) > 20:
            conversas_usuarios[user_id] = historico[-20:]
    
    with open(ARQUIVO_CONVERSAS, "w", encoding="utf-8") as f:
        json.dump(conversas_usuarios, f, ensure_ascii=False, indent=2)

def carregar_configs_servidores():
    if os.path.exists(CONFIGS_SERVIDORES):
        with open(CONFIGS_SERVIDORES, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return {}
    return {}

def salvar_configs_servidores(configs):
    with open(CONFIGS_SERVIDORES, "w", encoding="utf-8") as f:
        json.dump(configs, f, ensure_ascii=False, indent=2)

configs_servidores = carregar_configs_servidores()
carregar_conversas()

async def atualizar_historico(user_id, mensagem_usuario, resposta_bot):
    historico = conversas_usuarios.get(str(user_id), [])
    historico.append(f"**\nUsuário:**  {mensagem_usuario}")
    historico.append(f"\n{resposta_bot}")
    # Limite de histórico por usuário (exemplo: 20 últimas interações)
    if len(historico) > 40:
        historico = historico[-40:]
    conversas_usuarios[str(user_id)] = historico
    salvar_conversas()

async def historico(channel, usuario, bot_user):
    async for msg in channel.history(limit=20, oldest_first=True):
        if msg.author == usuario:
            historico_usuario.append(msg.content)
            if len(historico_usuario) > 20:
                historico_usuario.pop()
        elif msg.author == bot_user:
            historico_usuario.append(msg.content)
            if len(historico_usuario) > 20:
                historico_usuario.pop()
    historico_geral.append(historico_usuario)
    return "\n\n".join(historico_usuario)

print('Dados da IA carregados.')




# INICIALIZAÇÃO DA IA
# Função para gerar resposta usando a API do groq pq a do google passou do limite
async def gerar_resposta_ia(mensagem, user_id):
    try:
        historico = conversas_usuarios.get(str(user_id), [])
        prompt = (
            caracteristicas_bot + "\n" +
            comportamento_bot + "\n" +
            "\n".join(historico[-10:]) +
            f"\nUsuário: {mensagem}"
        )

        loop = asyncio.get_event_loop()
        completion = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model="groq/compound-mini",
                messages=[
                    {"role": "system", "content": caracteristicas_bot + "\n" + comportamento_bot},
                    {"role": "user", "content": prompt}
                ],
                temperature=1,
                max_completion_tokens=800,
                top_p=1,
                stream=False, 
                stop=None,
                compound_custom={"tools": {"enabled_tools": ["web_search","code_interpreter","visit_website"]}}
            )
        )

        # Extrai texto da resposta
        texto = completion.choices[0].message.content.strip()
        return texto

    except Exception as e:
        print(f"Erro na API Groq: {e}")
        return "Não consegui gerar uma resposta. Aguarde alguns segundos e tente novamente."

async def divide_mensagem(channel, texto, reference=None):
    partes = []
    paragrafo_atual = ""

    for paragrafo in texto.split("\n"):
        if len(paragrafo_atual) + len(paragrafo) + 1 <= 2000:
            paragrafo_atual += paragrafo + "\n"
        else:
            partes.append(paragrafo_atual.strip())
            paragrafo_atual = paragrafo + "\n"

    if paragrafo_atual:
        partes.append(paragrafo_atual.strip())

    for i, parte in enumerate(partes):
        await channel.send(parte, reference=reference if i == 0 else None)





# AÇÕES PASSIVAS E ATIVAS DO BOT
async def verificar_inatividade(ctx, tempo_espera=180):
    await asyncio.sleep(tempo_espera)
    if ctx.voice_client and not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
        await ctx.voice_client.disconnect()
        await ctx.send("Saí do canal de voz por inatividade.")

async def proxima_musica(ctx):
    if len(music_queue) > 0:
        next_data = music_queue.popleft()
        await tocar_musica(ctx, next_data["url"], next_data.get("title"))
    else:
        await ctx.send("A fila de músicas acabou.")
        await verificar_inatividade(ctx)

looping = {'enabled': False, 'current_song': None}
current_audio = None

async def tocar_musica(ctx, url, title=None):
    global looping, current_audio
    if not title or not url or title == "None":
        loop = asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
            url = data.get('url')
            if not url:
                raise Exception("URL de áudio não encontrada.")
            title = data.get('title', 'Música')
        except Exception as e:
            await ctx.send("Ocorreu um erro ao obter a música da fila. Tente novamente.")
            print(f"Erro ao buscar a música da fila: {e}")
            return

    audio_source = FFmpegOpusAudio(url, **ffmpeg_options)
    current_audio = {"source": url, "title": title}

    def after_playing(error):
        if error:
            print(f"Erro durante a reprodução: {error}")
        elif looping["enabled"] and looping["current_song"]:
            bot.loop.create_task(tocar_musica(ctx, looping["current_song"]["url"], looping["current_song"]["title"]))
        else:
            bot.loop.create_task(proxima_musica(ctx))

    ctx.voice_client.play(audio_source, after=after_playing)
    await ctx.send(f"Tocando agora: **{title}**")

    if looping["enabled"]:
        looping["current_song"] = {"url": url, "title": title}





# CHAT E CONTEXTO
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    guild_id = str(message.guild.id) if message.guild else None
    reacts_enabled = True  # Por padrão, reações habilitadas se não houver configuração
    if guild_id and guild_id in configs_servidores:
        reacts_enabled = configs_servidores[guild_id].get("reacts", True)

    if reacts_enabled: 
        palavras_chave = {
            "gato": "😺", "cachorro": "🐶", 'raposa': '🦊', "urso": "🐻", "lobo": "🐺", 'peixe': '🐟', 'sapo': '🐸', 'pato': '🦆',
            'coelho': '🐰', 'panda': '🐼', 'onça': '🐱', 'trigue': '🐯',
            'servidor': '🖥️', 'certo': '✅', 'errado': '❌', "parabéns": "🎉", 'pintuda': '🍌',
            'oii': '👋', 'olá': '👋', "engraçado": "😂", 'sus': '🤨', 'legal': '👍', "foda": "😎", "amor": "❤️", "feliz": "😊",
            "triste": "😢", "raiva": "😡", "surpresa": "😲", "medo": "😱", "confuso": "😕", "cansado": "😴", "animado": "🤔",
            "pensativo": "🤔", "desculpa": "🙏", 'sim': '👍', 'atumalaca': '😂', 'música': '🎵', '!tocar': '🎶', '!parar': '⏹️',
            '!pausar': '⏸️', '!retomar': '▶️', '!sair': '🚪', '!addfila': '📝', '!fila': '📃', '!piada': '🤣', '!dado': '🎲',
            '!analisar': '🔎', '!provocar': '🤡', 'protofox': '🤖', '!proximo': '⏭️'
        }

        # Verificar se a mensagem contém alguma palavra-chave
        for palavra, emoji in palavras_chave.items():
            if palavra in message.content.lower():
                await message.add_reaction(emoji)

    if bot.user.mentioned_in(message):
        try:
            mensagem = message.content.replace(f"<@{bot.user.id}>", "").strip()
            async with message.channel.typing():  # Gerenciador de contexto para `typing`
                resposta = await gerar_resposta_ia(mensagem, message.author.id)
                await asyncio.sleep(randint(3, 6))
                await atualizar_historico(message.author.id, mensagem, resposta)
                await divide_mensagem(message.channel, resposta, reference=message)
        except Exception as e:
            await message.channel.send("Desculpe, ocorreu um erro ao processar a mensagem.")
            print(f"Erro: {e}")

    await bot.process_commands(message)




# COMANDOS PARA MUSICAS
@bot.command()
async def tocar(ctx, url: str = None):
    if url is None:
        # Se não passar URL, tenta tocar o próximo da fila
        if not music_queue:
            await ctx.send("A fila está vazia. Adicione músicas com `!tocar <URL>` ou uma playlist com `!addfila`.")
            return
        next_data = music_queue.popleft()
        url = next_data.get("url")
        title = next_data.get("title")
    else:
        # Verifica se o link é uma playlist
        if "playlist?list=" in url or "/sets/" in url or "&list" in url:
            await ctx.send(
                "Vi que este é um link de uma playlist. Use o comando `!addfila` para adicioná-la e depois o comando `!tocar` para iniciá-la."
            )
            return

        # Se passar a URL, adiciona na fila e já pega o título
        loop = asyncio.get_event_loop()
        try:
            if not url:
                await ctx.send("O link da música está vazio ou inválido.")
                return
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
            audio_url = data.get('url')
            if not audio_url:
                await ctx.send("Não foi possível extrair o áudio desse link.")
                return
            title = data.get('title', 'Música')
            music_queue.append({"title": title, "url": audio_url})
            await ctx.send(f"Adicionado à fila: **{title}**")
            # Se não estiver tocando, já toca
            if not ctx.voice_client or (not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused()):
                next_data = music_queue.popleft()
                url = next_data.get("url")
                title = next_data.get("title")
            else:
                return
        except Exception as e:
            await ctx.send("Ocorreu um erro ao obter a música. Tente novamente.")
            print(f"Erro ao buscar a música: {e}")
            return

    # Se o título ainda não foi buscado (caso de addfila), busca agora
    if not title or not url:
        if not url:
            await ctx.send("O link da música está vazio ou inválido.")
            return
        loop = asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
            url = data.get('url')
            if not url:
                await ctx.send("Não foi possível extrair o áudio desse link.")
                return
            title = data.get('title', 'Música')
        except Exception as e:
            await ctx.send("Ocorreu um erro ao obter a música da fila. Tente novamente.")
            print(f"Erro ao buscar a música da fila: {e}")
            return

    # Conecta no canal de voz se necessario
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        if ctx.voice_client is None:
            await channel.connect()
            await ctx.send(f"Entrei no canal de voz: {channel.name}")
        await tocar_musica(ctx, url, title)
    else:
        await ctx.send("Você precisa estar em um canal de voz para usar este comando.")

@bot.command()
async def addfila(ctx, *links):
    for link in links:
        # Verifica se o link é uma playlist do YouTube ou SoundCloud
        if "playlist?list=" in link or "/sets/" in link or "&list" in link:
            await ctx.send(
                "Estou lendo a playlist, saiba que quanto maior a playlist, mais demorada será a leitura dela. "
                "Se desejar parar o processo, use `!parar`. Cada música leva em média 1s para ser lida."
            )
            loop = asyncio.get_event_loop()
            try:
                data = await loop.run_in_executor(None, lambda: ytdl.extract_info(link, download=False))
                if "entries" in data:
                    for entry in data["entries"]:
                        music_queue.append({"title": entry.get("title", "Música"), "url": entry.get("url")})
                    await ctx.send(f"Playlist adicionada à fila com **{len(data['entries'])} músicas**!")
            except Exception as e:
                await ctx.send(f"Erro ao processar a playlist: {link}")
                print(f"Erro ao processar a playlist {link}: {e}")
        else:
            # Caso seja um link de música única
            loop = asyncio.get_event_loop()
            try:
                data = await loop.run_in_executor(None, lambda: ytdl.extract_info(link, download=False))
                music_queue.append({"title": data.get("title", "Música"), "url": data.get("url")})
                await ctx.send(f"Adicionado à fila: **{data.get('title', 'Música')}**")
            except Exception as e:
                await ctx.send(f"Erro ao processar o link: {link}")
                print(f"Erro ao processar o link {link}: {e}")

@bot.command()
async def fila(ctx):
    if len(music_queue) == 0:
        await ctx.send("A fila está vazia no momento... Você pode adicionar músicas com `!tocar <URL>`")
    else:
        fila_formatada = ""
        for i, item in enumerate(music_queue, start=1):
            fila_formatada += f"**{i}.** {item['title']}\n"
        
        await ctx.send(f"🎵 Tem **{len(music_queue)}** músicas na fila:\n{fila_formatada}")

@bot.command()
async def loop(ctx):
    global looping, current_audio
    if not ctx.voice_client or not ctx.voice_client.is_playing():
        await ctx.send("Não há nenhuma música tocando para ativar o loop.")
        return

    if looping["enabled"]:
        looping["enabled"] = False
        looping["current_song"] = None
        await ctx.send("Loop desativado! A fila de músicas será retomada.")
    else:
        if current_audio is None:
            await ctx.send("Nenhuma música está sendo tocada no momento.")
            return
        looping["enabled"] = True
        looping["current_song"] = {"url": current_audio["source"], "title": current_audio["title"]}
        await ctx.send(f"Loop ativado! A música atual será repetida: **{current_audio['title']}**")

@bot.command()
async def proximo(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Música pulada! Tocando a próxima...")
    elif ctx.voice_client:
        await ctx.send("Não há nenhuma música tocando no momento.")
    else:
        await ctx.send("Não estou conectado a nenhum canal de voz.")

@bot.command()
async def pausar(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()  # Pausa a música atual
        await ctx.send("A música foi pausada. Use `!retomar` para continuar.")
    elif ctx.voice_client:
        await ctx.send("Não há nenhuma música tocando no momento.")
    else:
        await ctx.send("Não estou conectado a nenhum canal de voz.")

@bot.command()
async def retomar(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()  # Retoma a música pausada
        await ctx.send("A música foi retomada.")
    elif ctx.voice_client:
        await ctx.send("A música não está pausada no momento.")
    else:
        await ctx.send("Não estou conectado a nenhum canal de voz.")

@bot.command()
async def parar(ctx):
    global looping
    if ctx.voice_client:
        ctx.voice_client.stop()
        music_queue.clear()  
        if looping["enabled"]:
            looping["enabled"] = False
            looping["current_song"] = None
            await ctx.send("A música foi parada, o loop foi desativado e a fila foi limpa!")
        else:
            await ctx.send("A música foi parada e a fila foi limpa!")
    else:
        await ctx.send("Não estou conectado a nenhum canal de voz.")

@bot.command()
async def sair(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("Saí do canal de voz!")
    else:
        await ctx.send("Não estou em nenhum canal de voz no momento.")




# COMANDOS DE DIVERSÃO
@bot.tree.command(name="reacts", description="Habilita ou desabilita as reações automáticas do bot neste servidor.")
async def reacts(interaction: discord.Interaction, ativar: bool):
    guild_id = str(interaction.guild.id)
    configs_servidores[guild_id] = {"reacts": ativar}
    salvar_configs_servidores(configs_servidores)
    status = "habilitadas" if ativar else "desabilitadas"
    await interaction.response.send_message(f"Reações automáticas {status} neste servidor!", ephemeral=False)
    
@bot.command()
async def dado(ctx, *, arg: str = None):
    if not arg:
        await ctx.send("Use: `!dado 4d6`, `!dado 2d8+3`, `!dado 3#d20`, etc.", reference=ctx.message)
        return

    # Regex para capturar formatos como 3#2d6+1, 4d6, d20, 2d8-2, etc.
    match = re.fullmatch(r'(?:(\d+)#)?(\d*)d(\d+)([+-]\d+)?', arg.replace(" ", ""))
    if not match:
        await ctx.send("Formato inválido! Exemplos: `4d6`, `2d8+3`, `3#d20`", reference=ctx.message)
        return

    num_rolls = int(match.group(1)) if match.group(1) else 1
    qtd_dados = int(match.group(2)) if match.group(2) else 1
    faces = int(match.group(3))
    modificador = int(match.group(4)) if match.group(4) else 0

    respostas = []
    for _ in range(num_rolls):
        resultados = [random.randint(1, faces) for _ in range(qtd_dados)]
        total = sum(resultados) + modificador
        resultados_fmt = []
        for r in resultados:
            if r == 1 or r == faces:
                resultados_fmt.append(f"**{r}**") # Destaca apenas acerto crítico ou erro crítico
            else:
                resultados_fmt.append(str(r))
        mod_str = f"{modificador:+d}" if modificador else ""
        resposta = f"` {total} ` <-- [{', '.join(resultados_fmt)}]{qtd_dados}d{faces}{mod_str}"
        respostas.append(resposta)

    await ctx.send("\n".join(respostas), reference=ctx.message)

@bot.command()
async def dog(ctx):
    # Envia uma imagem aleatória de cachorro da API dog.ceo.
    try:
        response = requests.get("https://dog.ceo/api/breeds/image/random")
        data = response.json()
        image_url = data["message"]
        await ctx.send(image_url)
    except Exception as e:
        await ctx.send("Não consegui buscar uma imagem de cachorro agora. Tente novamente mais tarde.")
        print(f"Erro no comando !dog: {e}")
                
@bot.command()
async def catfact(ctx):
    cat_facts = [
        "Gatos passam cerca de 70% de suas vidas dormindo.",
        "Um grupo de gatos é chamado de 'clowder'.",
        "Gatos têm cinco dedos nas patas dianteiras, mas apenas quatro nas traseiras.",
        "O ronronar de um gato pode ter propriedades curativas.",
        "Os gatos podem fazer cerca de 100 sons diferentes, enquanto os cães fazem apenas 10.",
        "O maior gato doméstico já registrado pesava 21 kg.",
        "Os gatos não conseguem sentir o sabor doce.",
        "Os bigodes dos gatos ajudam a medir espaços e detectar objetos ao redor.",
        "Os gatos podem girar as orelhas em 180 graus.",
        "Os gatos têm 32 músculos em cada orelha para movê-las em diferentes direções.",
        "O cérebro de um gato é 90% semelhante ao de um humano.",
        "Os gatos podem saltar até seis vezes o comprimento do próprio corpo.",
        "Os gatos esfregam o rosto nas pessoas para marcar território com suas glândulas de cheiro.",
        "Os gatos domésticos compartilham cerca de 95,6% de seu DNA com tigres.",
        "Os gatos podem beber água salgada, pois seus rins conseguem filtrar o sal."
    ]
    fact = random.choice(cat_facts)
    await ctx.send(fact)

@bot.command()
async def piada(ctx):
    # Conta uma piada aleatória.
    piadas = [
        "Por que o livro de matemática ficou triste? Porque tinha muitos problemas!",
        "O que o tomate foi fazer no banco? Tirar extrato!",
        "Por que o computador foi ao médico? Porque estava com um vírus!",
        "Há quem diga que Mc Kevin foi melhor que Michael Jackson mas, pelo menos Michael Jackson ia até o chão e voltava",
        "O que as pernas de um paraplégico tem em comum com o comunismo? Ambos não funcionam.",
        "Joga um preto pra cima, se cair é merda, se voar é urubu, caso se pendurar é macaco.;",
        "Por que o jacaré tirou o filho da escola? Porque ele réptil de ano!",
        "O elefante caiu na lama, e eu não consigo terminar a piada por que a lama voou e não deu pra ver mais nada.",
        "Qual a semelhança entre um carro com pneu furado e uma preta grávida? Ambos estão esperando um macaco.",
        "Sabem pq as crianças africanas n escovam os dentes ? Pq só pode escovar dps de comer.",
        "Qual a diferencia entre um preto e um macaco? ... Pois é",
        "Pq o batman cobre só metade do rosto ? Para a polícia ver q ele e branco e n prender ele.",
        "Uma vez eu estava lendo um livro, porém o vilão da história era muito mal compreendido e estava certo, qual o nome do livro ? Mein Kampf",
        "Qual é a diferença entre uma pizza e um judeu? Só da pra colocar uma pizza no forno.",
        "Porque é que não existem medicamentos na Etiópia? Porque não podem ser tomados em jejum.",
        "Estava uma menina a brincar com a cinza de um cinzeiro quando chega o Hitler e lhe pergunta: Estás prrocurrando alguém em especial?",
        "Qual é a diferença entre um rabino e um psiquiatra?” “Um cobra mais caro do que o outro.",
        "Qual é a diferença entre um judeu rico e um judeu pobre?” “O judeu rico come o frango, enquanto o judeu pobre sacrifica o frango para ficar rico.",
        "Sabe Qual é a melhor piada para um judeu? Só Te Conto Se Me Pagar.",
        "Um judeu rabino vai ao mesmo barbeiro e corta o cabelo. 'Não posso te cobrar, você é um homem de Deus.'\nNo dia seguinte, o barbeiro encontra uma dúzia de rabinos em sua porta.",
        "Uma pessoa foi ao psicólogo e perguntou: Doutor, tenho tendências suicidas, o que faço? Em primeiro lugar, pague a consulta.",
        "Qual a diferença entre um padre e um tenista? As bolas com que o tenista brinca têm pelinhos.",
        "Qual é a parte mais dura de um vegetal? A cadeira de rodas.",
        "Porque é que a Anne Frank não acabou o diário? Problemas de concentração.",
        "Porque é que o Hitler se suicidou? Porque viu a conta do gás.",
        "O que uma mulher preta faz para ajudar a combater o crime? Um aborto.",
        "Se um preto e um cigano estão no mesmo carro, quem vai a conduzir? Um polícial.",
        "Qual é a parte do Halloween favorita dos pedófilos? Entregas grátis.",
        "Porque não há videntes em África? Porque preto não têm futuro.",
        "As pessoas com trissomia 21 preferem System of a Down ou Megadeth?",
        "No outro dia, a minha esposa pediu para passar o batom dela, mas eu passei acidentalmente um bastão de cola. Ela ainda não reclamou.",
        "Hoje, perguntei ao meu telefone: “Siri, por que é que ainda estou solteiro?” e ele ativou a câmara frontal.",
        "A minha filha perguntou-me como morrem as estrelas. “Normalmente de overdose”, eu disse.",
        "O minha ex teve um acidente grave recentemente. Eu disse aos médicos o tipo de sangue errado. Agora, ela vai realmente saber como é a rejeição.",
        "Quando eu morrer, eu quero morrer como o meu avô, que morreu pacificamente durante o sono. Não gritar como todos os passageiros do seu carro.",
        "Comprei um ralador de queijo para o aniversário do meu amigo cego. Mais tarde, ele disse-me que era o livro mais violento que ele já tinha lido.",
        "Para onde é que o árabe foi depois de se perder num campo minado? Para todos os lugares.",
        "Dá um fósforo a um homem e ele ficará aquecido por algumas horas. Coloca fogo nele e ele ficará aquecido para o resto da vida."
    ]
    piada = random.choice(piadas)
    await ctx.send(piada)

@bot.command()
async def provoque(ctx, member: discord.Member = None):
    member = member or ctx.author
    provocacoes = [
        "Você é tão lento que até um caracol te ultrapassaria! 🐌",
        "Seus memes são tão ruins que até o bot ficou sem graça. 😅",
        "Você é a razão pela qual as instruções de shampoo existem. 🧴",
        "Você é tão único quanto um arquivo chamado 'novo_documento(1)'. 😂",
        "Seus amigos te amam... mas só porque precisam de XP no servidor. 🎮",
        "Você é tão azarado que até o Wi-Fi foge de você. 📶",
        "Você é tão confuso que até o Google Maps se perde com você. 🗺️",
        "Você é tão engraçado que até o bot teve que fingir rir. 🤖",
        "Você é tão ruim em jogos que o tutorial te venceu. 🎮",
        "Você é tão esquecido que até o Ctrl+Z desistiu de você. ⌨️",
        "Você é tão desorganizado que até o Excel não consegue te organizar. 📊",
        "Você é tão preguiçoso que até o relógio parou para te acompanhar. 🕒",
        "Você é tão estranho que até o CAPTCHA acha que você é um robô. 🤖",
        "Você é tão ruim em matemática que acha que 2+2 é igual a peixe. 🐟",
        "Você é tão perdido que até o Waze desistiu de recalcular sua rota. 🚗"
    ]
    mensagem = random.choice(provocacoes)
    await ctx.send(f"{member.mention}, {mensagem}")

@bot.command()
async def analisar(ctx, *, prompt: str = None):
    if not ctx.message.attachments:
        await ctx.send("Por favor, envie uma imagem junto com o comando `!analisar`.")
        return

    imagem = ctx.message.attachments[0]
    ext = imagem.filename.lower().split('.')[-1]
    mime_type = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp"
    }.get(ext, "image/png")

    await ctx.send("Analisando a imagem, aguarde...")

    img_bytes = await imagem.read()

    try:
        model = genai.GenerativeModel("models/gemini-2.5-flash")  # Troque pelo modelo disponível
        
        # Define o prompt padrão caso o usuário não forneça um
        if prompt is None:
            prompt = "O que você acha dessa imagem?"
        
        response = model.generate_content(
            [
                {
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": img_bytes
                            }
                        },
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=400
            )
        )
        
        if response.candidates and response.candidates[0].content.parts:
            texto = response.text.strip()
            await ctx.send(texto[:2000])
        else:
            Exception
            
    except Exception as e:
        await ctx.send("Não consegui analisar a imagem. Tente novamente.")
        print(f"Erro na análise de imagem: {e}")

@bot.tree.command(name="souprotofox", description="Repete a mensagem que você enviar.")
async def souprotofox(interaction: discord.Interaction, fala: str):
    await interaction.response.send_message(fala, ephemeral=True)
    await interaction.channel.send(fala)



# COMANDOS DE INFORMAÇÕES
@bot.tree.command(name="calc", description="Calcula uma expressão matemática simples. Exemplo: 2*2+(-3)")
async def calc(interaction: discord.Interaction, expressao: str):
    expressao = expressao.replace(" ", "")
    # Permite apenas números, operadores e parênteses
    if not re.fullmatch(r"[0-9+\-*/().]+", expressao):
        await interaction.response.send_message(
            f"Expressão inválida! Use apenas números e operadores '+, -, *, /, ()'.",
            ephemeral=True
        )
        return
    try:
        resultado = eval(expressao, {"__builtins__": None}, {})
        await interaction.response.send_message(
            f"Resultado: `{resultado}`",
            ephemeral=True
        )
    except Exception:
        await interaction.response.send_message(
            f"Não foi possível calcular essa expressão.",
            ephemeral=True
        )

@bot.tree.command(name="historico", description="Mostra o histórico de conversa entre você e o bot.")
async def historico(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    historico = conversas_usuarios.get(user_id, [])
    if not historico:
        await interaction.response.send_message("Você ainda não tem histórico de conversa com o bot.", ephemeral=True)
    else:
        texto = "\n".join(historico[-10:])
        # Envia a primeira parte como resposta obrigatória
        await interaction.response.send_message(
            texto[:2000] if len(texto) > 0 else "Seu histórico está vazio.", ephemeral=True
        )
        # Se houver mais de 2000 caracteres, envia o resto como followup
        for i in range(2000, len(texto), 2000):
            await interaction.followup.send(texto[i:i+2000], ephemeral=True)

@bot.tree.command(name="limparhistorico", description="Apaga o histórico de conversa entre você e o bot.")
async def limparhistorico(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if user_id in conversas_usuarios:
        del conversas_usuarios[user_id]
        salvar_conversas()
        await interaction.response.send_message("Seu histórico de conversa foi apagado com sucesso!", ephemeral=True)
    else:
        await interaction.response.send_message("Você não possui histórico para apagar.", ephemeral=True)

@bot.tree.command(name="servidor", description="Mostra informações sobre o servidor.")
async def servidor(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(title=f"Informações do servidor: {guild.name}", color=discord.Color.green())
    embed.add_field(name="ID do Servidor", value=guild.id, inline=False)
    embed.add_field(name="Dono", value=guild.owner, inline=False)
    embed.add_field(name="Número de Membros", value=guild.member_count, inline=False)
    embed.add_field(name="Criado em", value=guild.created_at.strftime("%d/%m/%Y"), inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="usuario", description="Mostra informações sobre o usuário mencionado.")
async def usuario(interaction: discord.Interaction, usuario: discord.Member = None):
    usuario = usuario or interaction.user
    embed = discord.Embed(title=f"Informações do usuário: {usuario.name}", color=discord.Color.purple())
    embed.add_field(name="ID do Usuário", value=usuario.id, inline=False)
    embed.add_field(name="Entrou no Servidor em", value=usuario.joined_at.strftime("%d/%m/%Y"), inline=False)
    embed.add_field(name="Conta Criada em", value=usuario.created_at.strftime("%d/%m/%Y"), inline=False)
    embed.set_thumbnail(url=usuario.avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="avatar", description="Mostra o avatar do usuário mencionado.")
async def avatar(interaction: discord.Interaction, usuario: discord.Member = None):
    usuario = usuario or interaction.user
    embed = discord.Embed(title=f"Avatar de {usuario.name}", color=discord.Color.blue())
    embed.set_image(url=usuario.avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="ajuda", description="Exibe a lista de comandos disponíveis.")
async def ajuda_slash(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Comandos Disponíveis",
        description="Aqui está a lista de comandos que você pode usar:",
        color=discord.Color.blue()
    )
    embed.add_field(name="🎵 Música", value=(
        "`!tocar <URL>` - Adiciona uma música à fila e toca no canal de voz.\n"
        "`!fila` - Mostra a fila de músicas.\n"
        "`!addfila` - Adiciona uma música na fila.\n"
        "`!loop` - Faz a música atual tocar em looping.\n"
        "`!proximo` - Pula a música atual e toca a próxima da fila.\n"
        "`!pausar` - Pausa a música atual.\n"
        "`!retomar` - Retoma a música pausada.\n"
        "`!parar` - Para a música atual e limpa a fila.\n"
        "`!sair` - Faz o bot sair do canal de voz."
    ), inline=False)
    embed.add_field(name="🎉 Diversão", value=(
        "`/reacts <True/False>` - Habilita/Desabilita as reações do Bot nas mensagens do servidor.\n"
        "`/souprotofox <mensagem>` - Repete a mensagem que você enviar.\n"
        "`!provoque <usuário>` - Envia uma provocação engraçada para o usuário mencionado.\n"
        "`!dog` - Envia uma imagem aleatória de cachorro.\n"
        "`!catfact` - Envia um fato aleatório sobre gatos.\n"
        "`!piada` - Envia uma piada aleatória.\n"
        "`!dado` - Rola o dado que quiser e quantas vezes quiser.\n"
        "`!analisar` - Analisa uma imagem enviada em conjunto com sua mensagem.\n"
    ), inline=False)
    embed.add_field(name="ℹ️ Informações", value=(
        "`/calc` - Calcula uma expressão matemática simples. Exemplo: 2*2+(3).\n"
        "`/historico` - Mostra o histórico de conversa entre você e o bot.\n"
        "`/limparhistorico` - Exclui o histórico de conversa entre você e o bot.\n"
        "`/servidor` - Mostra informações sobre o servidor.\n"
        "`/usuario <usuário>` - Mostra informações sobre o usuário mencionado.\n"
        "`/avatar <usuário>` - Mostra o avatar do usuário mencionado."
    ), inline=False)
    embed.add_field(name="❓ Ajuda", value="`/ajuda` - Exibe esta mensagem de ajuda.", inline=False)
    embed.set_footer(text="Bot de Música e Diversão • Protofox")
    await interaction.response.send_message(embed=embed, ephemeral=True)

print('Comandos carregados com sucesso!\n\nIniciando o bot...')




# INICIAÇÃO DO BOT
@bot.event
async def on_ready():
    print(f'{bot.user.name} está Online!\nID do bot: {bot.user.id}')
    try:
        synced = await bot.tree.sync()
        print(f"Comandos de aplicativo sincronizados: {len(synced)}\n------------------------------")
    except Exception as e:
        print(f"Erro ao sincronizar comandos de aplicativo: {e}\n------------------------------")

#    version = "teste de hosting"
#    aviso = bot.get_channel(726114472833581086)
#    await aviso.send(f'Commit versão {version} foi feito.')

bot.run(Token)
