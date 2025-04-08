import discord
from discord.ext import commands, tasks
import datetime
import json
import os
from dotenv import load_dotenv


load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID")) 

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

BIRTHDAYS = "birthdays.json"

def load_birthdays():
    try:
        with open(BIRTHDAYS, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    
def save_birthdays(bdays):
    with open(BIRTHDAYS, "w") as f:
        json.dump(bdays, f)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    check_birthdays.start()


@bot.command()
async def add_birthday(ctx, user: discord.Member, date: str):
    bdays = load_birthdays()
    bdays[str(user.id)] = date
    save_birthdays(bdays)
    await ctx.send(f"Birthday added for {user.name} on {date}")

@tasks.loop(hours=24)
async def check_birthdays():
    today = datetime.datetime.now().strftime("%m-%d")
    bdays = load_birthdays()
    for user_id, bday in bdays.items():
        if bday == today:
            owner = await bot.fetch_user(OWNER_ID)
            user = await bot.fetch_user(int(user_id))
            await owner.send(f"@everyone It's {user.name}'s birthday today!", allowed_mentions=discord.AllowedMentions(everyone=True))


@check_birthdays.before_loop
async def before_check():

    now = datetime.datetime.now()
    future = datetime.datetime.combine(now + datetime.timedelta(days=1), datetime.time.min)
    await discord.utils.sleep_until(future)

if __name__ == "__main__":
    bot.run(TOKEN)
