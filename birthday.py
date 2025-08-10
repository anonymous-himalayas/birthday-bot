import discord
from discord.ext import commands, tasks
import datetime
import json
import os
from dotenv import load_dotenv
import atexit
import re
from flask import Flask
import threading
import time

# Mini Flask Server
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


# Discord Bot
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID")) 

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
notified = {}

BIRTHDAYS = "birthdays.json"


def load_birthdays():
    try:
        with open(BIRTHDAYS, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_birthdays(bdays):
    with open(BIRTHDAYS, "w") as f:
        json.dump(bdays, f, indent=4)


def get_guild_birthdays(guild_id):
    all_bdays = load_birthdays()
    return all_bdays.get(str(guild_id), {})


def set_guild_birthdays(guild_id, guild_bdays):
    all_bdays = load_birthdays()
    all_bdays[str(guild_id)] = guild_bdays
    save_birthdays(all_bdays)


def is_valid_date(date_str):
    try:
        datetime.datetime.strptime(date_str, "%m/%d")
        return True
    except ValueError:
        return False

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    if not check_birthdays.is_running():
        check_birthdays.start()
    if not reset_notifications.is_running():
        reset_notifications.start()


@bot.command(name="list-birthdays")
async def list_birthdays(ctx):
    bdays = get_guild_birthdays(ctx.guild.id)

    bdays = dict(sorted(bdays.items(), key=lambda item: datetime.datetime.strptime(item[1], "%m/%d"))) 
    if not bdays:
        await ctx.send("No birthdays have been added yet.")
        return

    bday_list = "\n".join([f"{name}: {date}" for name, date in bdays.items()])
    
    
    await ctx.send(f"**Birthday List:**\n```{bday_list}```")


@bot.command(name="add-birthday")
async def add_birthday(ctx, *, args):
    # ?sd2d2 raah
    pattern = r'"(.*?)"\s+(\d{2}/\d{2})'
    matches = re.findall(pattern, args)
    
    if not matches:
        await ctx.send("No valid name/date pairs found. Use: `!add-birthday \"Name\" MM/DD`")
        return

    guild_id = str(ctx.guild.id)
    all_bdays = load_birthdays()
    guild_bdays = all_bdays.get(guild_id, {})

    added = []
    skipped = []

    for name, date in matches:
        if is_valid_date(date):
            guild_bdays[name] = date
            added.append(f"{name}: {date}")
        else:
            skipped.append(f"{name}: Invalid date format")

    all_bdays[guild_id] = guild_bdays
    save_birthdays(all_bdays)

    msg = ""
    if added:
        msg += "**Birthdays added:**\n" + "\n".join(added)
    if skipped:
        msg += "\n**Skipped entries:**\n" + "\n".join(skipped)

    await ctx.send(msg)




@bot.command(name="remove-birthday")
async def remove_birthday(ctx, name: str):
    guild_id = str(ctx.guild.id)
    all_bdays = load_birthdays()
    guild_bdays = all_bdays.get(guild_id, {})
    
    if name in guild_bdays.keys():
        del guild_bdays[name]
        all_bdays[guild_id] = guild_bdays
        save_birthdays(all_bdays)
        notified[guild_id].discard(name)
        await ctx.send(f"Birthday for **{name}** removed.")
    else:
        await ctx.send(f"No birthday found for **{name}**.")



@tasks.loop(minutes=5)
async def check_birthdays():
    today = datetime.datetime.now().strftime("%m/%d")
    all_bdays = load_birthdays()

    for guild in bot.guilds:
        guild_id = str(guild.id)
        guild_bdays = all_bdays.get(guild_id, {})

        # Make sure the guild has a set for tracking reported birthdays
        if guild_id not in notified:
            notified[guild_id] = set()

        already_pinged = notified[guild_id]

        for name, date in guild_bdays.items():
            if date == today and name not in already_pinged:
                channel = discord.utils.get(guild.text_channels, name="announcements")
                if channel:
                    await channel.send(
                        f"@everyone It's **{name.title()}**'s birthday today! 🎉🎉🎉",
                        allowed_mentions=discord.AllowedMentions(everyone=True)
                    )
                    already_pinged.add(name)  # Mark as reported


@tasks.loop(time=datetime.time(0, 0, 0))
async def reset_notifications():
    for guild_id in notified.keys():
        notified[guild_id].clear()




@atexit.register
def cleanup():
    if os.path.exists(BIRTHDAYS):
        with open(BIRTHDAYS, 'w') as file:
            json.dump({}, file)


if __name__ == "__main__":
    if "PORT" in os.environ:  # Running on Render
        threading.Thread(target=run_flask, daemon=True).start()

    time.sleep(2)

    bot.run(TOKEN)
