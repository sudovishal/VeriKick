import discord
from discord.ext import commands, tasks
import asyncio
from flask import Flask
from threading import Thread
app = Flask(__name__)

TOKEN = "MTM1NDcxOTE5MDAxOTM0MjQzNw.GmjVvR.JMcUr2GWqriwB02MpEgbMZ6gpySJJfYKLMfWvE"
GUILD_ID = 762588559072034837  # Replace with your server ID
MEMBERS_ROLE_ID = 1027036183903080509  # Replace with the 'Members' role ID

intents = discord.Intents.default()
intents.members = True  # Required to track new members
intents.message_content = True  # Required to read message content
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    await bot.tree.sync()  # Syncs all slash commands
    print("Slash commands synced!")  # Debugging line
    print(f'Logged in as {bot.user}')


@bot.event
async def on_member_join(member):
    """When a new member joins, start a 30-minute timer for verification."""
    print(f"{member.name} joined. Checking verification in 30 minutes.")

    await asyncio.sleep(1800)  # Wait for 30 minutes (1800 seconds)

    guild = bot.get_guild(GUILD_ID)
    member = guild.get_member(member.id)  # Fetch latest member info

    if member and MEMBERS_ROLE_ID not in [role.id for role in member.roles]:
        await member.kick(reason="Not verified within 30 minutes")
        print(f"{member.name} was kicked for not verifying.")




@app.route('/')
def home():
    return "Bot is running!"


def run():
    app.run(host='0.0.0.0', port=8080)


Thread(target=run).start()


@bot.command()
@commands.has_permissions(kick_members=True)  # Restrict command to mods/admins
async def keek(ctx, member: discord.Member, *, reason="No reason provided"):
    """Kicks a user manually with a reason."""
    if ctx.author.top_role <= member.top_role:
        await ctx.send("❌ You can't kick someone with a higher or equal role.")
        return

    try:
        await member.kick(reason=reason)
        await ctx.send(f"✅ {member.mention} has been kicked. Reason: {reason}")
        print(f"{member} was kicked by {ctx.author} for {reason}")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to kick this user.")
    except discord.HTTPException:
        await ctx.send("❌ An error occurred while trying to kick the user.")


# ✅ Error Handling for !keek Command
@keek.error
async def keek_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Usage: `!keek @user [reason]`")

bot.run(TOKEN)
