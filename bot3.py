import discord
from discord.ext import commands
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from datetime import datetime

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

# Command to store data globally
@bot.command()
async def store(ctx, title: str, username: str, password: str):
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    entry_id = f"{ctx.author.id}_{timestamp}"  # Unique entry ID

    try:
        # Insert data into MongoDB
        user_data = {
            "entry_id": entry_id,
            "author": ctx.author.name,
            "title": title,
            "username": username,
            "password": password,
            "timestamp": timestamp
        }
        users.insert_one(user_data)
        await ctx.send(f"Data stored successfully under title '{title}'!")
    except Exception as e:
        await ctx.send(f"An error occurred while storing data: {str(e)}")

# Command to fetch all entries globally
@bot.command()
async def fetch_all(ctx):
    # Check if the user is an admin
    if ctx.author.guild_permissions.administrator:  # Admin check
        try:
            # Fetch all entries in the database
            entries = list(users.find())
            if entries:
                response = "Stored entries:\n"
                for entry in entries:
                    # Use 'Unknown' if fields are missing
                    title = entry.get('title', 'Unknown')
                    username = entry.get('username', 'Unknown')
                    password = entry.get('password', 'Unknown')
                    timestamp = entry.get('timestamp', 'Unknown')
                    author = entry.get('author', 'Unknown')
                    response += f"**Title:** {title}, **Username:** {username}, **Password:** {password}, **Timestamp:** {timestamp}, **Author:** {author}\n"
                await ctx.send(response)
            else:
                await ctx.send("No data has been stored yet.")
        except Exception as e:
            await ctx.send(f"An error occurred while fetching data: {str(e)}")
    else:
        await ctx.send("You do not have permission to use this command.")


# Command to fetch a specific entry by title globally
@bot.command()
async def fetch(ctx, title: str):
    try:
        # Fetch a specific entry by title with case-sensitive collation
        entry = users.find_one(
            {"title": title},
            collation={"locale": "en", "strength": 3}
        )
        if entry:
            # Use 'Unknown' if 'author' field is missing
            author = entry.get('author', 'Unknown')
            await ctx.send(f"**Title:** {entry['title']}, **Username:** {entry['username']}, **Password:** {entry['password']}, **Timestamp:** {entry['timestamp']}, **Author:** {author}")
        else:
            await ctx.send(f"No data found for title '{title}'.")
    except Exception as e:
        await ctx.send(f"An error occurred while fetching data: {str(e)}")

# Command to delete a specific entry by title globally
@bot.command()
async def delete(ctx, title: str):
    try:
        # Check if the user is the author or an admin
        entry = users.find_one({"title": title})
        if entry:
            # Check if the user is the author of the entry or an admin
            if entry["author"] == ctx.author.name or ctx.author.guild_permissions.administrator:
                # Delete the specific entry by title
                result = users.delete_one({"title": title})
                if result.deleted_count > 0:
                    await ctx.send(f"Data with title '{title}' deleted successfully!")
                else:
                    await ctx.send(f"No data found for title '{title}'.")
            else:
                await ctx.send("You do not have permission to delete this entry.")
        else:
            await ctx.send(f"No data found for title '{title}'.")
    except Exception as e:
        await ctx.send(f"An error occurred while deleting data: {str(e)}")

#delete_all for admin only
@bot.command()
async def delete_all(ctx):
    # Check if the user is an admin
    if ctx.author.guild_permissions.administrator:  # Admin check
        try:
            # Delete all entries from the 'user' collection
            result = users.delete_many({})
            if result.deleted_count > 0:
                await ctx.send(f"All data has been deleted successfully! ({result.deleted_count} entries)")
            else:
                await ctx.send("No data to delete.")
        except Exception as e:
            await ctx.send(f"An error occurred while deleting data: {str(e)}")
    else:
        await ctx.send("You do not have permission to use this command.")

bot.run(DISCORD_TOKEN)
