import discord
from discord.ext import commands, tasks
from discord import app_commands
import datetime
import json
import os
from dotenv import load_dotenv
import atexit


# Discord Bot
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

OWNER_ID = os.getenv("OWNER_ID")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

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
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"Error syncing commands: {e}")

    if not check_birthdays.is_running():
        check_birthdays.start()
    if not reset_notifications.is_running():
        reset_notifications.start()


@bot.tree.command(name="list-birthdays", description="Show all saved birthdays in this server")
async def list_birthdays(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    bdays = get_guild_birthdays(guild_id)

    if not bdays:
        await interaction.response.send_message("No birthdays have been added yet.")
        return

    bdays = dict(sorted(bdays.items(), key=lambda item: datetime.datetime.strptime(item[1], "%m/%d")))
    bday_list = "\n".join([f"{name}: {date}" for name, date in bdays.items()])
    await interaction.response.send_message(f"**Birthday List:**\n```{bday_list}```")


@bot.tree.command(name="add-birthday", description="Add a birthday for someone")
@app_commands.describe(name="Person's name", date="Birthday in MM/DD format")
async def add_birthday(interaction: discord.Interaction, name: str, date: str):
    guild_id = str(interaction.guild.id)
    all_bdays = load_birthdays()
    guild_bdays = all_bdays.get(guild_id, {})

    if is_valid_date(date):
        guild_bdays[name] = date
        all_bdays[guild_id] = guild_bdays
        save_birthdays(all_bdays)
        await interaction.response.send_message(f"Added birthday for **{name}** on {date}")
    else:
        await interaction.response.send_message("Invalid date format. Use MM/DD (e.g., 09/05)")


@bot.tree.command(name="remove-birthday", description="Remove a saved birthday")
@app_commands.describe(name="Person's name")
async def remove_birthday(interaction: discord.Interaction, name: str):
    guild_id = str(interaction.guild.id)
    all_bdays = load_birthdays()
    guild_bdays = all_bdays.get(guild_id, {})

    if name in guild_bdays:
        del guild_bdays[name]
        all_bdays[guild_id] = guild_bdays
        save_birthdays(all_bdays)
        notified.setdefault(guild_id, set()).discard(name)
        await interaction.response.send_message(f"Removed birthday for **{name}**")
    else:
        await interaction.response.send_message(f"No birthday found for **{name}**")


@tasks.loop(minutes=15)
async def check_birthdays():
    today = datetime.datetime.now().strftime("%m/%d")
    all_bdays = load_birthdays()

    for guild in bot.guilds:
        guild_id = str(guild.id)
        guild_bdays = all_bdays.get(guild_id, {})

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
                    already_pinged.add(name)


@tasks.loop(time=datetime.time(0, 0, 0))
async def reset_notifications():
    for guild_id in notified:
        notified[guild_id].clear()



@atexit.register
def cleanup():
    if os.path.exists(BIRTHDAYS):
        with open(BIRTHDAYS, 'w') as file:
            json.dump({}, file)


if __name__ == "__main__":
    # if "PORT" in os.environ:  # Running on Render
    #     threading.Thread(target=run_flask, daemon=True).start()

    # time.sleep(2)

    bot.run(TOKEN)
