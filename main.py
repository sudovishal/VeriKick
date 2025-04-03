import discord
from discord.ext import commands
import asyncio
import os
from flask import Flask
from threading import Thread
import threading
import time
import requests
from datetime import datetime, timedelta
import pytz
IST = pytz.timezone('Asia/Kolkata')

app = Flask(__name__)

TOKEN = os.getenv('TOKEN')  # Use environment variable
GUILD_ID = int(os.getenv('GUILD_ID', '762588559072034837'))  # Convert to int
MEMBERS_ROLE_ID = int(os.getenv('MEMBERS_ROLE_ID', '1027036183903080509'))  # Convert to int
NEWCOMMER_ROLE_ID = int(os.getenv('NEWCOMMER_ROLE_ID', '1355549916713193472'))  # Convert to int
LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID', '960241934230749265'))  # Convert to int
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
     # Check for unverified users after bot restart
    await check_unverified_users()

@bot.event
async def on_member_join(member):
    # print(await has_members_role(member))
    # print(await has_new_commer_role(member))
    if await has_members_role(member) and await has_new_commer_role(member):
        await remove_newcomer_role_for_rejoins(member)
    else:
        await kick_if_no_members_role(member)

    
async def kick_if_no_members_role(member):
    """When a new member joins, start a timer for verification."""
    member_id = member.id
    guild_id = member.guild.id
   
     # Get the log channel
    log_channel = member.guild.get_channel(LOG_CHANNEL_ID)
    if not log_channel:
        print(f"Warning: Log channel with ID {LOG_CHANNEL_ID} not found.")
        return
    
    print(f"{member.name} joined. Checking verification in an hour.")
    if log_channel:
        await log_channel.send("Timer started for verification.")

    await asyncio.sleep(3600)  # Wait for an hour

    try:
        guild = bot.get_guild(guild_id)
        if not guild:
            print(f"Could not find guild with ID {guild_id}")
            return
            
        member = await guild.fetch_member(member_id)
        
        if member:
            member_roles = [role.id for role in member.roles]
            if MEMBERS_ROLE_ID not in member_roles:
                print(f"Kicking {member.name} for not verifying within the time limit.")
                await member.kick(reason="Not verified within an hour.")
                print(f"{member.name} was kicked for not verifying.")

                # Send a message to the log channel
                if log_channel:
                    await log_channel.send(f"{member.mention} was kicked for not verifying within the time limit.")
            else:
                print(f"{member.name} verified successfully.")
        else:
            print(f"Member with ID {member_id} no longer in the server.")
    except discord.Forbidden:
        print(f"Bot doesn't have permission to kick {member_id}")
    except discord.NotFound:
        print(f"Member {member_id} not found after waiting period.")
    except Exception as e:
        print(f"Error during verification check: {e}")


async def remove_newcomer_role_for_rejoins(member):
    """Event triggered when a member joins the server"""
    # Wait a moment for Discord to finish processing the join
    await asyncio.sleep(20)
    # Get the log channel
    log_channel = member.guild.get_channel(LOG_CHANNEL_ID)
    if not log_channel:
        print(f"Warning: Log channel with ID {LOG_CHANNEL_ID} not found.")
        return
    
    # Get the role object
    role = member.guild.get_role(NEWCOMMER_ROLE_ID)
    if not role:
        await log_channel.send(f"⚠️ Role with ID {NEWCOMMER_ROLE_ID} not found for member {member.display_name}.")
        return
    
    # Check if they have the role we want to remove
    if role in member.roles:
        # Check if member has MEMBERS_ROLE_ID role
        members_role = member.guild.get_role(MEMBERS_ROLE_ID)
        if members_role in member.roles:
            await log_channel.send(f"🔍 Checking audit logs for recent leave/kick of {member.display_name}...")
            
            # Check recent audit logs for this user leaving
            found_in_audit_logs = False
            
            # Check for kicks
            async for entry in member.guild.audit_logs(limit=100, action=discord.AuditLogAction.kick):
                if entry.target.id == member.id and (discord.utils.utcnow() - entry.created_at).days < 7:
                    # User was kicked and rejoined with the role
                    try:
                        await member.remove_roles(role, reason="Automatic removal of role after rejoin")
                        await log_channel.send(f"✅ Removed role **{role.name}** from **{member.display_name}** after they rejoined. They were kicked on {entry.created_at.strftime('%Y-%m-%d %H:%M UTC')}.")
                        found_in_audit_logs = True
                        break
                    except discord.Forbidden:
                        await log_channel.send(f"❌ Failed to remove role from {member.display_name}. Missing permissions.")
                    except Exception as e:
                        await log_channel.send(f"❌ Error removing role from {member.display_name}: {str(e)}")
            
            # If not found as a kick, check for leaves
            if not found_in_audit_logs:
                await log_channel.send(f"ℹ️ No kick record found for {member.display_name}. Assuming they left voluntarily.")
                try:
                    await member.remove_roles(role, reason="Automatic removal of role after rejoin")
                    await log_channel.send(f"✅ Removed role **{role.name}** from **{member.display_name}** after they voluntarily rejoined.")
                except discord.Forbidden:
                    await log_channel.send(f"❌ Failed to remove role from {member.display_name}. Missing permissions.")
                except Exception as e:
                    await log_channel.send(f"❌ Error removing role from {member.display_name}: {str(e)}")
        else:
            await log_channel.send(f"ℹ️ Member **{member.display_name}** has the newcommer role but not the members role. No action needed.")
    else:
        await log_channel.send(f"ℹ️ Member **{member.display_name}** joined but does not have the role **{role.name}**. No action needed.")


async def has_members_role(member):
    members_role = await member.guild.fetch_role(MEMBERS_ROLE_ID)
    # print(member.roles)
    return members_role is not None and members_role in member.roles

async def has_new_commer_role(member):
    newcommer_role = await member.guild.fetch_role(NEWCOMMER_ROLE_ID)
    return newcommer_role is not None and newcommer_role in member.roles


async def check_unverified_users():
    """Check for any unverified users after bot restart"""
    print("Checking for unverified users after bot restart...")
    
    # Get the guild
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        print(f"Could not find guild with ID {GUILD_ID}")
        return
    
    # Get the log channel
    log_channel = guild.get_channel(LOG_CHANNEL_ID)
    if not log_channel:
        print(f"Warning: Log channel with ID {LOG_CHANNEL_ID} not found.")
    else:
        await log_channel.send("🔍 Checking for unverified users after bot restart...")
    
    # Get current time
    current_time = datetime.now(IST)
    
    # Track how many users were processed
    checked_count = 0
    kicked_count = 0
    
    try:
        # Iterate through all members
        async for member in guild.fetch_members():
            checked_count += 1
            
            # Skip bots
            if member.bot:
                continue
                
            # Check if the member doesn't have the MEMBERS_ROLE_ID
            member_roles = [role.id for role in member.roles]
            if MEMBERS_ROLE_ID not in member_roles and NEWCOMMER_ROLE_ID in member_roles:
                # Check join time
                join_time = member.joined_at.astimezone(IST) if member.joined_at else None
                
                if join_time and (current_time - join_time) > timedelta(hours=1):
                    # Member has been in server for more than an hour without verifying
                    print(f"Kicking {member.name} for not verifying within time limit (joined {join_time.strftime('%Y-%m-%d %H:%M %Z')}).")
                    
                    try:
                        await member.kick(reason="Not verified within the time limit (detected after bot restart)")
                        kicked_count += 1
                        print(f"{member.name} was kicked for not verifying.")
                        
                        # Log the action
                        if log_channel:
                            time_diff = current_time - join_time
                            hours = int(time_diff.total_seconds() // 3600)
                            await log_channel.send(f"⏰ {member.name} was kicked for not verifying. They joined {hours}+ hours ago.")
                    except discord.Forbidden:
                        print(f"Bot doesn't have permission to kick {member.id}")
                        if log_channel:
                            await log_channel.send(f"⚠️ Failed to kick {member.mention}: Missing permissions")
                    except Exception as e:
                        print(f"Error kicking member {member.id}: {e}")
                        if log_channel:
                            await log_channel.send(f"⚠️ Error kicking {member.mention}: {str(e)}")
        
        # Send summary
        if log_channel:
            await log_channel.send(f"✅ Unverified user check complete. Checked {checked_count} members, kicked {kicked_count} unverified members.")
        print(f"Unverified user check complete. Checked {checked_count} members, kicked {kicked_count} unverified members.")
            
    except Exception as e:
        print(f"Error during unverified user check: {e}")
        if log_channel:
            await log_channel.send(f"❌ Error during unverified user check: {str(e)}")


@app.route('/health')
def health_check():
    return 'Bot is online!', 200

def ping_self():
    app_url = os.getenv('PROD_APP_URL')

    while True:
        try:
            response = requests.get(app_url)
            print(f"Self-ping: {response.status_code}")
        except Exception as e:
            print(f"Self-ping failed: {e}")
            
        # Sleep for 10 minutes before pinging again
        time.sleep(1200)

# Start the self-pinging in a background thread
def start_ping_thread():
    ping_thread = threading.Thread(target=ping_self, daemon=True)
    ping_thread.start()
    print("Self-ping mechanism started")


start_ping_thread()

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


@bot.command()
async def test_log(ctx):
    """Test command to check if log channel is working"""
    log_channel = ctx.guild.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        await log_channel.send("✅ Log channel is working correctly.")
        await ctx.send("Message sent to log channel successfully.")
    else:
        await ctx.send(f"❌ Could not find log channel with ID {LOG_CHANNEL_ID}.")


@bot.command()
@commands.has_permissions(kick_members=True)
async def check_unverified(ctx):
    """Manually check for and kick unverified users"""
    await ctx.send("Starting check for unverified users...")
    await check_unverified_users()
    await ctx.send("Check completed. See logs for details.")

if __name__ == "__main__":
    flask_thread = Thread(target=run)
    flask_thread.daemon = True  # Set thread as daemon so it exits when main thread exits
    flask_thread.start()
    
    run_bot()  # Run the bot in the main thread