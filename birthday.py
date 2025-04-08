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
client = discord.Client(intents=discord.Intents.default())

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

def is_valid_date(date_str):
    try:
        datetime.datetime.strptime(date_str, "%m/%d")
        return True
    except ValueError:
        return False

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    check_birthdays.start()

@bot.command(name="list-birthdays")
async def list_birthdays(ctx):
    bdays = load_birthdays()
    
    if not bdays:
        await ctx.send("No birthdays have been added yet.")
        return

    bday_list = "\n".join([f"{name}: {date}" for name, date in bdays.items()])
    
    
    await ctx.send(f"**Birthday List:**\n```{bday_list}```")


@bot.command(name="add-birthday")
async def add_birthday(ctx, name: str, date: str):
    if not is_valid_date(date):
        await ctx.send("Please use the MM/DD date format (e.g., 09/25).")
        return

    bdays = load_birthdays()

    bdays[name] = date
    save_birthdays(bdays)
    await ctx.send(f"Birthday for **{name}** added on {date}")

@bot.command(name="remove-birthday")
async def remove_birthday(ctx, name: str):
    bdays = load_birthdays()
    
    if name.lower() in bdays:
        del bdays[name.lower()]
        save_birthdays(bdays)
        await ctx.send(f"Birthday for **{name}** removed.")
    else:
        await ctx.send(f"No birthday found for **{name}**.")

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
