import discord
from discord.ext import commands
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from datetime import datetime
import asyncio

# Load environment variables
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Ensure required environment variables are loaded
if not MONGO_URI:
    raise ValueError("MONGO_URI is not set in the environment variables.")
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN is not set in the environment variables.")

# MongoDB Setup
try:
    client = MongoClient(MONGO_URI)
    db = client['raiden']
    users = db['user']
except Exception as e:
    raise ConnectionError(f"Failed to connect to MongoDB: {str(e)}")

# Bot setup
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")

# Decorator to check for role
def has_role(role_name):
    async def predicate(ctx):
        if discord.utils.get(ctx.author.roles, name=role_name):
            return True
        await ctx.send("You do not have the required role to use this bot.")
        return False
    return commands.check(predicate)

# Command to store data (role-protected)
@bot.command()
@has_role("bot access")
async def store(ctx, title: str):
    """Stores data securely via DM, preventing duplicate entries."""
    try:
        # Check if an entry already exists for this user and title in the server
        existing_entry = users.find_one(
            {"server_id": str(ctx.guild.id), "title": title},
            collation={"locale": "en", "strength": 2}  # Case-insensitive match
        )

        if existing_entry:
            await ctx.author.send(f"An entry with the title '{title}' already exists. Please use a different title.")
            await ctx.send(f"@{ctx.author.name}, the title '{title}' is already in use. Please check your DMs.")
            return

        # Send a DM to the user asking for the username and password
        await ctx.author.send(f"To store data for the title '{title}', please provide the username.")

        def check_dm(msg):
            return msg.author == ctx.author and isinstance(msg.channel, discord.DMChannel)

        # Wait for the username in DM
        try:
            username_msg = await bot.wait_for("message", check=check_dm, timeout=30.0)
        except asyncio.TimeoutError:
            await ctx.author.send("You took too long to respond. Please try the command again.")
            await ctx.send(f"@{ctx.author.name}, you took too long to respond. Please try the command again.")
            return

        username = username_msg.content

        # Ask for the password
        await ctx.author.send("Now, please provide the password.")

        try:
            password_msg = await bot.wait_for("message", check=check_dm, timeout=30.0)
        except asyncio.TimeoutError:
            await ctx.author.send("You took too long to respond. Please try the command again.")
            await ctx.send(f"@{ctx.author.name}, you took too long to respond. Please try the command again.")
            return

        password = password_msg.content

        # Prepare the data for storage
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        entry_id = f"{ctx.guild.id}_{ctx.author.id}_{timestamp}"  # Unique entry ID

        user_data = {
            "entry_id": entry_id,
            "server_id": str(ctx.guild.id),
            "author_id": str(ctx.author.id),
            "author": ctx.author.name,
            "title": title,
            "username": username,
            "password": password,
            "timestamp": timestamp
        }

        # Insert the data into MongoDB
        users.insert_one(user_data)

        # Notify the user
        await ctx.author.send(f"Your data for the title '{title}' has been securely stored!")
        await ctx.send(f"@{ctx.author.name}, your data has been securely stored. Check your DMs for confirmation!")

    except discord.errors.Forbidden:
        await ctx.send("I couldn't send you a DM. Please enable DMs and try again.")
    except Exception as e:
        await ctx.send(f"An error occurred while storing data: {str(e)}")


        
#update
@bot.command()
@has_role("bot access")
async def update(ctx, title: str):
    """Allows users to update their stored data securely."""
    try:
        # Check if the entry exists for the user in the current server
        entry = users.find_one({
            "server_id": str(ctx.guild.id),
            "title": title
        }, collation={"locale": "en", "strength": 2})  # Case-insensitive

        if not entry:
            await ctx.send(f"@{ctx.author.name}, no data found for the title '{title}'. Please ensure the title is correct and stored.")
            return

        # Check if the user is the one who stored the data
        if entry["author_id"] != str(ctx.author.id):
            await ctx.send(f"@{ctx.author.name}, only the user who stored the data can update it.")
            return

        # Ask for new username and password via DM
        await ctx.author.send(f"To update data for the title '{title}', please provide the new username.")

        def check_dm(msg):
            return msg.author == ctx.author and isinstance(msg.channel, discord.DMChannel)

        # Wait for the username in DM
        username_msg = await bot.wait_for("message", check=check_dm, timeout=30.0)
        new_username = username_msg.content

        await ctx.author.send("Now, please provide the new password.")
        password_msg = await bot.wait_for("message", check=check_dm, timeout=30.0)
        new_password = password_msg.content

        # Update the entry in MongoDB
        updated_data = {
            "$set": {
                "username": new_username,
                "password": new_password,
                "timestamp": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            }
        }
        users.update_one({"_id": entry["_id"]}, updated_data)

        await ctx.author.send(f"Your data for title '{title}' has been successfully updated!")
        await ctx.send(f"@{ctx.author.name}, your data for '{title}' has been updated. Check your DMs for confirmation.")

    except discord.errors.Forbidden:
        await ctx.send("I couldn't send you a DM. Please enable DMs and try again.")
    except discord.errors.TimeoutError:
        await ctx.author.send("You took too long to respond. Please try the command again.")
    except Exception as e:
        await ctx.send(f"An error occurred while updating data: {str(e)}")








#Fetch
@bot.command()
@has_role("bot access")
async def fetch(ctx, title: str):
    """Fetches data securely via DM for users with the 'bot access' role."""
    try:
        # Fetch the entry from MongoDB for the specific server and title
        entry = users.find_one(
            {"server_id": str(ctx.guild.id), "title": title},
            collation={"locale": "en", "strength": 2}  # Case-insensitive
        )

        if entry:
            # Send the credentials in DM to the user
            dm_channel = await ctx.author.create_dm()  # Ensure DM channel exists
            message = await dm_channel.send(
                f"**Title:** {entry['title']}\n"
                f"**Username:** {entry['username']}\n"
                f"**Password:** {entry['password']}\n"
                f"**Timestamp:** {entry['timestamp']}"
            )

            # Notify the user in the public channel
            notify_message = await ctx.send(
                f"@{ctx.author.name}, the data for '{title}' has been sent to your DMs. It will be deleted in 5 minutes."
            )

            # Wait for 1 minute (60 seconds) before deleting the DM
            await asyncio.sleep(300)
            await message.delete()  # Delete the DM message
            await notify_message.delete()  # Delete the notification message in the public channel
        else:
            await ctx.send(f"No data found for the title '{title}'. Please ensure the title is correct and stored.")
    except discord.errors.Forbidden:
        await ctx.send("I couldn't send you a DM. Please enable DMs and try again.")
    except Exception as e:
        await ctx.send(f"An error occurred while fetching data: {str(e)}")



# Command to fetch all entries for the server (admin-only)
@bot.command()
async def fetch_all(ctx):
    """Fetches all stored entries for the current server, restricted to admins, and sends them via DM."""
    server_id = str(ctx.guild.id)

    # Check if the user has administrator permissions
    if not ctx.author.guild_permissions.administrator:
        await ctx.send(f"@{ctx.author.name}, you do not have the required permissions to use this command.")
        return

    try:
        # Fetch all entries for the current server
        entries = list(users.find({"server_id": server_id}))
        if entries:
            response = "Stored entries:\n"
            for entry in entries:
                author = entry.get('author', 'Unknown')
                response += (
                    f"**Title:** {entry['title']}\n"
                    f"**Username:** {entry['username']}\n"
                    f"**Password:** {entry['password']}\n"
                    f"**Timestamp:** {entry['timestamp']}\n"
                    f"**Author:** {author}\n\n"
                )
            
            # Send the response in DM
            dm_channel = await ctx.author.create_dm()
            await dm_channel.send(response)
            await ctx.send(f"@{ctx.author.name}, the stored entries have been sent to your DMs.")
        else:
            await ctx.send("No data has been stored in this server yet.")

    except discord.errors.Forbidden:
        await ctx.send("I couldn't send you a DM. Please enable DMs and try again.")
    except Exception as e:
        await ctx.send(f"An error occurred while fetching data: {str(e)}")




# Command to delete all data in the server (admin-only)
@bot.command()
async def delete_all(ctx):
    """Deletes all stored entries for the current server, restricted to admins."""
    # Check if the user has administrator permissions
    if not ctx.author.guild_permissions.administrator:
        await ctx.send(f"@{ctx.author.name}, you do not have the required permissions to use this command.")
        return

    server_id = str(ctx.guild.id)

    try:
        # Delete all entries for the current server
        result = users.delete_many({"server_id": server_id})
        await ctx.send(f"All data in this server has been deleted. Total entries deleted: {result.deleted_count}")
    except Exception as e:
        await ctx.send(f"An error occurred while deleting all data: {str(e)}")

#PURGE
@bot.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx, limit: int = 100):
    """
    Purges messages starting from the message the user replied to.
    :param ctx: Context of the command.
    :param limit: The number of messages to delete (default: 100).
    """
    try:
        # Check if the user replied to a message
        if not ctx.message.reference:
            await ctx.send("Please reply to the message you want to start purging from.")
            return

        # Fetch the message that was replied to
        target_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        
        # Purge messages starting from the target message
        deleted = await ctx.channel.purge(
            limit=limit,
            after=target_message,
            check=lambda m: m.created_at > target_message.created_at
        )

        await ctx.send(f"✅ Successfully deleted {len(deleted)} messages.", delete_after=5)
    except discord.NotFound:
        await ctx.send("The specified message was not found.")
    except discord.Forbidden:
        await ctx.send("I do not have permission to manage messages in this channel.")
    except discord.HTTPException as e:
        await ctx.send(f"An error occurred while trying to purge messages: {str(e)}")       

bot.run(DISCORD_TOKEN)
