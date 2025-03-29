import discord
from discord.ext import commands
import asyncio
import os
from flask import Flask
from threading import Thread

app = Flask(__name__)

TOKEN = os.getenv('TOKEN')  # Use environment variable
GUILD_ID = int(os.getenv('GUILD_ID', '762588559072034837'))  # Convert to int
MEMBERS_ROLE_ID = int(os.getenv('MEMBERS_ROLE_ID', '1027036183903080509'))  # Convert to int

intents = discord.Intents.default()
intents.members = True  # Required to track new members
intents.message_content = True  # Required to read message content
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    try:
        await bot.tree.sync()  # Syncs all slash commands
        print("Slash commands synced!")  # Debugging line
    except Exception as e:
        print(f"Error syncing slash commands: {e}")
    
    print(f'Logged in as {bot.user}')


@bot.event
async def on_member_join(member):
    """When a new member joins, start a 30-minute timer for verification."""
    print(f"{member.name} joined. Checking verification in 30 minutes.")

    await asyncio.sleep(1800)  # Wait for 30 minutes (1800 seconds)

    try:
        guild = bot.get_guild(GUILD_ID)
        member = await guild.fetch_member(member.id)  # Use fetch_member instead of get_member
        
        if member and MEMBERS_ROLE_ID not in [role.id for role in member.roles]:
            await member.kick(reason="Not verified within 30 minutes")
            print(f"{member.name} was kicked for not verifying.")
    except discord.NotFound:
        print(f"Member {member.id} not found after waiting period.")
    except Exception as e:
        print(f"Error during verification check: {e}")


@app.route('/')
def home():
    return "Bot is running!"


def run():
    app.run(host='0.0.0.0', port=8080)


def run_bot():
    bot.run(TOKEN)


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


if __name__ == "__main__":
    flask_thread = Thread(target=run)
    flask_thread.daemon = True  # Set thread as daemon so it exits when main thread exits
    flask_thread.start()
    
    run_bot()  # Run the bot in the main thread