import discord
from discord import app_commands
from discord.ext import tasks
from discord.ext.commands import Bot,Context 
import asyncio, aiofiles
import json
import typing

from discord.channel import TextChannel
from os import environ
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot: Bot = Bot("!", intents=intents)

tree: app_commands.CommandTree = bot.tree

state_file: aiofiles.threadpool.text.AsyncTextIOWrapper 
state: dict[str,typing.Any] = {}

task_attive: dict = {}
message_objects_db: dict = {}



@bot.event
async def on_ready():
    global state_file
    global state
    try:
        await bot.load_extension("jishaku")
    except:
        pass
    state_file = await aiofiles.open("db.json", "r+")
    await state_file.seek(0)
    state = json.loads(await state_file.read())

    for key in state.keys():
        server = discord.Object(int(key))
        tree.copy_global_to(guild=server)
        await tree.sync(guild=server)
        channel1= bot.get_channel(state[key]["problem_channel_id"])
        if not isinstance(channel1,TextChannel):
            raise Exception("INVALID CONF: channel id "+str(state[key]["problem_channel_id"])+" is invalid!")
        prenotazioni_message = await channel1.fetch_message(
            state[key]["problem_message_id"]
        )
        channel2 = bot.get_channel(state[key]["phiquadro_channel_id"])
        if not isinstance(channel2,TextChannel):
            raise Exception("INVALID CONF: channel id "+str(state[key]["phiquadro_channel_id"])+" is invalid!")

        phiquadro_message = await channel2.fetch_message(
            state[key]["phiquadro_message_id"]
        )
        message_objects_db[key] = {
            "problem_message": prenotazioni_message,
            "phiquadro_message": phiquadro_message,
            "voice_channels": bot.get_channel(state[key]["voice_channels_id"])
        }
    print("Ready!")


# prenotazioni_message_template = """
# **Stato problemi**:
# JOLLY: {}
# {},
# {},
# {},
# {},
# {},
# {},
# {},
# {},
# {},
# {},
# {},
# {},
# {},
# {},
# {},
# {},
# {},
# {},
# {},
# {},
# {}
#
# """
prenotazioni_message_template='\n**Stato problemi**:\nJOLLY: {}\n'
prenotazioni_message_template+='{},\n'*20 + '{}\n\n' 

async def aggiorna_stato(guild: str, refresh_list=True):
    await state_file.seek(0)
    await state_file.write(json.dumps(state))
    await state_file.truncate()
    if refresh_list is False:
        return
    state_list = []
    jolly_chosen = False
    if state[guild]["problem_db"]["jolly"] is None:
        state_list.append("Nessun jolly scelto.")
    else:
        state_list.append(str(state[guild]["problem_db"]["jolly"]))
        jolly_chosen = True
    for i in range(1, 22):
        curr = state[guild]["problem_db"][str(i)]
        prefix = str(i) + ": "
        if jolly_chosen and i == state[guild]["problem_db"]["jolly"]:
            prefix = "**" + str(i) + "(JOLLY)**: "
        if curr is None:
            state_list.append(prefix + "libero")
        elif curr == "COMPLETATO":
            state_list.append(prefix + ":white_check_mark: completato")
        else:
            state_list.append(prefix + ":hammer: Ci sta lavorando " + curr)
    await message_objects_db[guild]["problem_message"].edit(
        content=prenotazioni_message_template.format(*state_list)
    )


@bot.hybrid_command(
    name="prenota_problema",
)
async def prenota_problema(ctx: Context, numero: int, prenotatore: str):
    if ctx.guild is None:
        await ctx.send("ERRORE: comando eseguito all'esterno di un server.",ephemeral=True)
        return
    guild_id = str(ctx.guild.id)
    if res := state[guild_id]["problem_db"].get(str(numero)) is not None:
        await ctx.send("Questo problema è già prenotato", ephemeral=True)
        return
    if res == "COMPLETATO":
        await ctx.send("Questo problema è già stato completato", ephemeral=True)

    state[guild_id]["problem_db"][str(numero)] = prenotatore
    await ctx.send("Problema prenotato correttamente", ephemeral=True)
    await aggiorna_stato(guild_id)


@bot.hybrid_command()
async def rinuncia(ctx: Context, numero: int):
    if ctx.guild is None:
        await ctx.send("ERRORE: comando eseguito all'esterno di un server.",ephemeral=True)
        return
    guild_id = str(ctx.guild.id)
    state[guild_id]["problem_db"][str(numero)] = None
    await ctx.send("Rinunciato al problema correttamente", ephemeral=True)
    await aggiorna_stato(guild_id)


@bot.hybrid_command()
async def completato(ctx: Context, numero: int):
    if ctx.guild is None:
        await ctx.send("ERRORE: comando eseguito all'esterno di un server.",ephemeral=True)
        return
    guild_id = str(ctx.guild.id)
    state[guild_id]["problem_db"][str(numero)] = "COMPLETATO"
    await ctx.send("Problema marcato come completato correttamente", ephemeral=True)

    voice_chats:discord.CategoryChannel= message_objects_db[guild_id]["voice_channels"]

    for channel in voice_chats.channels:
        if channel.name != f"P{numero}": continue
        await channel.delete()

    await aggiorna_stato(guild_id)


@bot.hybrid_command()
async def reset_stato_problemi(ctx: Context):
    if ctx.guild is None:
        await ctx.send("ERRORE: comando eseguito all'esterno di un server.",ephemeral=True)
        return
    guild_id = str(ctx.guild.id)
    state[guild_id]["problem_db"]["jolly"] = None
    for i in range(1, 22):
        state[guild_id]["problem_db"][str(i)] = None
    await ctx.send("Resettato lo stato dei problemi correttamente", ephemeral=True)
    await aggiorna_stato(guild_id)


@bot.hybrid_command()
async def jolly(ctx: Context, numero: int):
    if ctx.guild is None:
        await ctx.send("ERRORE: comando eseguito all'esterno di un server.",ephemeral=True)
        return
    guild_id = str(ctx.guild.id)
    state[guild_id]["problem_db"]["jolly"] = numero
    await ctx.send("Scelto il jolly correttamente", ephemeral=True)
    await aggiorna_stato(guild_id)


@bot.hybrid_command()
async def registra_risposta_inviata(ctx: Context, prob_num: int, risposta: int):
    if ctx.guild is None:
        await ctx.send("ERRORE: comando eseguito all'esterno di un server.",ephemeral=True)
        return
    guild_id = str(ctx.guild.id)
    state[guild_id]["risposte_db"][str(prob_num)].append(risposta)
    await ctx.send("Registrata risposta inviata correttamente", ephemeral=True)
    if state[guild_id]["consegnatore_id"] is not None:
        user= bot.get_user(state[guild_id]["consegnatore_id"])
        if user is None:
            await ctx.send("ERRORE: l'id del consegnatore attuale non è valido. Rieseguire la configurazione",ephemeral=True)
            return
        ch = await user.create_dm()
        await ch.send(
            f"<@{state[guild_id]["consegnatore_id"]}> NUOVA RISPOSTA PER IL PROBLEMA **{prob_num}**: **{risposta}**"
        )
    await aggiorna_stato(guild_id, False)


@bot.hybrid_command()
async def risposte_inviate(ctx: Context, prob_num: int, ephemeral: bool = True):
    if ctx.guild is None:
        await ctx.send("ERRORE: comando eseguito all'esterno di un server.",ephemeral=True)
        return
    guild_id = str(ctx.guild.id)
    if len(state[guild_id]["risposte_db"][str(prob_num)]) == 0:
        await ctx.send(
            f"Il problema {prob_num} non ha risposte precedentemente inviate",
            ephemeral=True,
        )
    else:
        string = f"Risposte inviate nel problema {prob_num}:\n"
        for i in range(len(state[guild_id]["risposte_db"][str(prob_num)])):
            string += f"- {i+1}: {state[guild_id]["risposte_db"][str(prob_num)][i]}\n"
        await ctx.send(string, ephemeral=ephemeral)


@bot.hybrid_command()
async def reset_stato_risposte(ctx: Context):
    if ctx.guild is None:
        await ctx.send("ERRORE: comando eseguito all'esterno di un server.",ephemeral=True)
        return
    guild_id = str(ctx.guild.id)
    for i in range(1, 22):
        state[guild_id]["risposte_db"][str(i)] = []
    await aggiorna_stato(guild_id, False)
    await ctx.send("Resettato lo stato delle risposte correttamente", ephemeral=True)


@bot.hybrid_command()
async def rimuovi_jolly(ctx: Context):
    if ctx.guild is None:
        await ctx.send("ERRORE: comando eseguito all'esterno di un server.",ephemeral=True)
        return
    guild_id = str(ctx.guild.id)
    state[guild_id]["problem_db"]["jolly"] = None
    await aggiorna_stato(guild_id)
    await ctx.send("Jolly rimosso correttamente", ephemeral=True)


@tasks.loop(seconds=30)
async def phiquadro(guild_id: str):
    print("loop")

    id_gara = state[guild_id]["phiquadro_gara_id"]
    if id_gara==0: return 
    cmd1 = f"curl 'https://www.phiquadro.it/gara_a_squadre/script/crea_tabella.php' --compressed -X POST -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0' -H 'Accept: */*' -H 'Accept-Language: en-US,en;q=0.5' -H 'Accept-Encoding: gzip, deflate, br, zstd' -H 'Content-Type: application/x-www-form-urlencoded; charset=UTF-8' -H 'X-Requested-With: XMLHttpRequest' -H 'Origin: https://www.phiquadro.it' -H 'Connection: keep-alive' -H 'Referer: https://www.phiquadro.it/gara_a_squadre/classifica.php' -H 'Cookie: PHPSESSID=vmh0hdh2edr51edmisdt9tchag' -H 'Sec-Fetch-Dest: empty' -H 'Sec-Fetch-Mode: cors' -H 'Sec-Fetch-Site: same-origin' -H 'TE: trailers' --data-raw 'id_gara={id_gara}&id_sess=1&s=1000&e=0&lg=0&mostra_da=1&mostra_a=1000' --output out.html"
    proc1 = await asyncio.create_subprocess_shell(
        cmd1, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc1.communicate()
    if proc1.returncode != 0:
        raise Exception("Something bad happened running cmd1: STDERR" + str(stderr))

    cmd2 = "wkhtmltoimage --enable-local-file-access out.html out.jpg"
    proc2 = await asyncio.create_subprocess_shell(
        cmd2, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc2.communicate()
    if proc2.returncode != 0:
        raise Exception("Something bad happened running cmd2: STDERR" + str(stderr))

    await message_objects_db[guild_id]["phiquadro_message"].edit(
        content="", attachments=[discord.File("out.jpg")]
    )


@bot.hybrid_command()
async def setup_server(
    ctx: Context,
    problem_channel: discord.TextChannel,
    phiquadro_channel: discord.TextChannel,
    voice_channels: discord.CategoryChannel
):
    if ctx.guild is None:
        await ctx.send("ERRORE: comando eseguito all'esterno di un server.",ephemeral=True)
        return
    guild_id = str(ctx.guild.id)
    problem_message = await problem_channel.send("test123")
    phiquadro_message = await phiquadro_channel.send("test123")

    state[guild_id] = {
        "problem_db": {"jolly": None},
        "risposte_db": {},
        "problem_channel_id": problem_channel.id,
        "problem_message_id": problem_message.id,
        "phiquadro_channel_id": phiquadro_channel.id,
        "phiquadro_message_id": phiquadro_message.id,
        "phiquadro_gara_id": 0,
        "consegnatore_id": None,
        "voice_channels_id": voice_channels.id
    }
    for i in range(1, 22):
        state[guild_id]["problem_db"][str(i)] = None
        state[guild_id]["risposte_db"][str(i)] = []

    message_objects_db[guild_id] = {
        "problem_message": problem_message,
        "phiquadro_message": phiquadro_message,
    }
    await aggiorna_stato(guild_id)
    await ctx.send("Registrato server correttamente", ephemeral=True)


@bot.hybrid_command()
async def imposta_dati_gas(
    ctx: Context, id: int, consegnatore: typing.Optional[discord.Member] = None
):
    if ctx.guild is None:
        await ctx.send("ERRORE: comando eseguito all'esterno di un server.",ephemeral=True)
        return
    guild_id = str(ctx.guild.id)
    state[guild_id]["phiquadro_gara_id"] = id
    if consegnatore is not None:
        state[guild_id]["consegnatore_id"] = consegnatore.id
    else:
        state[guild_id]["consegnatore_id"] = None
    await aggiorna_stato(guild_id, False)
    await ctx.send("Impostato id della gas correttamente", ephemeral=True)


@bot.hybrid_command()
async def inizia_gas(ctx: Context):
    if ctx.guild is None:
        await ctx.send("ERRORE: comando eseguito all'esterno di un server.",ephemeral=True)
        return
    guild_id = str(ctx.guild.id)
    task = phiquadro.start(guild_id)
    task_attive[guild_id] = task
    
    voice_chats:discord.CategoryChannel= message_objects_db[guild_id]["voice_channels"]
    await ctx.send("Monitoraggio gas iniziato", ephemeral=True)

    for i in range(1,22):
        await voice_chats.create_voice_channel(f"P{i}")

    

@bot.hybrid_command()
async def fine_gas(ctx: Context):
    if ctx.guild is None:
        await ctx.send("ERRORE: comando eseguito all'esterno di un server.",ephemeral=True)
        return
    guild_id = str(ctx.guild.id)
    task = task_attive[guild_id].cancel()
    
    voice_chats:discord.CategoryChannel= message_objects_db[guild_id]["voice_channels"]

    await ctx.send("Monitoraggio gas terminato", ephemeral=True)
    for channel in voice_chats.channels:
        if not channel.name.startswith("P"): continue
        await channel.delete()

bot.run(environ.get("TOKEN",""))
