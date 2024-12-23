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
    """Stores data securely via DM, checks if user already exists."""
    try:
        # Check if the user already has an entry for the given title in the same server
        existing_entry = users.find_one(
            {"server_id": str(ctx.guild.id), "author_id": str(ctx.author.id), "title": title}
        )

        if existing_entry:
            # If an entry exists, notify the user that the data already exists
            await ctx.send(f"User data with the title '{title}' already exists.")
            return  # Exit the command if the data already exists
        
        # Ask the user for the username and password in a DM
        await ctx.author.send(f"To store data for the title '{title}', please provide the username.")
        
        def check_dm(msg):
            return msg.author == ctx.author and isinstance(msg.channel, discord.DMChannel)
        
        # Wait for the username in DM
        username_msg = await bot.wait_for("message", check=check_dm, timeout=30.0)
        username = username_msg.content

        await ctx.author.send("Now, please provide the password.")
        
        # Wait for the password in DM
        password_msg = await bot.wait_for("message", check=check_dm, timeout=30.0)
        password = password_msg.content

        # Store the data in MongoDB
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
        users.insert_one(user_data)

        await ctx.author.send(f"Your data for title '{title}' has been securely stored!")
        await ctx.send(f"@{ctx.author.name}, your data has been securely stored. Check your DMs for confirmation!")
    except discord.errors.Forbidden:
        await ctx.send("I couldn't send you a DM. Please enable DMs and try again.")
    except Exception as e:
        await ctx.send(f"An error occurred while storing data: {str(e)}")

        
#update

@bot.command()
@has_role("bot access")
async def update(ctx, title: str, username: str = None, password: str = None):
    """Updates user credentials (username or password) if the entry exists."""
    try:
        # Check if the entry with the given title exists
        entry = users.find_one(
            {"server_id": str(ctx.guild.id), "author_id": str(ctx.author.id), "title": title}
        )

        if entry:
            # Update the username or password if provided
            if username:
                users.update_one(
                    {"entry_id": entry['entry_id']},
                    {"$set": {"username": username}}
                )
            if password:
                users.update_one(
                    {"entry_id": entry['entry_id']},
                    {"$set": {"password": password}}
                )

            await ctx.send(f"Credentials for '{title}' have been updated successfully.")
        else:
            await ctx.send(f"No data found for the title '{title}' to update.")

    except Exception as e:
        await ctx.send(f"An error occurred while updating data: {str(e)}")


#Fetch
@bot.command()
@has_role("bot access")
async def fetch(ctx, title: str):
    """Fetches data securely via DM and deletes the message after 1 minute."""
    try:
        # Fetch the entry from MongoDB for the specific server and user
        entry = users.find_one(
            {"server_id": str(ctx.guild.id), "author_id": str(ctx.author.id), "title": title},
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
                f"@{ctx.author.name}, the data for '{title}' has been sent to your DMs. It will be deleted in 5 minute."
            )

            # Wait for 5 minutes (300 seconds) before deleting the DM
            await asyncio.sleep(300)
            await message.delete()  # Delete the DM message

            # Wait for an additional 1 minute (60 seconds)
            await asyncio.sleep(60)

            # Delete the notification message in the public channel after 7 minutes
            await notify_message.delete()

        else:
            await ctx.send(f"No data found for the title '{title}'.")

    except discord.errors.Forbidden:
        await ctx.send("I couldn't send you a DM. Please enable DMs and try again.")
    except Exception as e:
        await ctx.send(f"An error occurred while fetching data: {str(e)}")

# Command to delete a specific entry by title (role-protected)
@bot.command()
@has_role("bot access")
async def delete(ctx, title: str):
    server_id = str(ctx.guild.id)
    author_id = str(ctx.author.id)

    try:
        # Allow only the author or admin to delete the data
        entry = users.find_one({"server_id": server_id, "title": title})
        if entry and (entry['author_id'] == author_id or ctx.author.guild_permissions.administrator):
            result = users.delete_one({"server_id": server_id, "title": title})
            if result.deleted_count > 0:
                await ctx.send(f"Data with title '{title}' deleted successfully!")
            else:
                await ctx.send(f"No data found for title '{title}'.")
        else:
            await ctx.send("You do not have permission to delete this entry.")
    except Exception as e:
        await ctx.send(f"An error occurred while deleting data: {str(e)}")

# Command to fetch all entries for the server (admin-only)
@bot.command()
@commands.has_permissions(administrator=True)
async def fetch_all(ctx):
    server_id = str(ctx.guild.id)

    try:
        # Fetch all entries for the current server
        entries = list(users.find({"server_id": server_id}))
        if entries:
            response = "Stored entries:\n"
            for entry in entries:
                author = entry.get('author', 'Unknown')
                response += f"**Title:** {entry['title']}, **Username:** {entry['username']}, **Password:** {entry['password']}, **Timestamp:** {entry['timestamp']}, **Author:** {author}\n"
            await ctx.send(response)
        else:
            await ctx.send("No data has been stored in this server yet.")
    except Exception as e:
        await ctx.send(f"An error occurred while fetching data: {str(e)}")

# Command to delete all data in the server (admin-only)
@bot.command()
@commands.has_permissions(administrator=True)
async def delete_all(ctx):
    server_id = str(ctx.guild.id)

    try:
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
