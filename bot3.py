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

# Command to store user data with unique entry ID
@bot.command()
async def store(ctx, title: str, username: str, password: str):
    admin_id = str(ctx.author.id)  # Admin's Discord ID
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    entry_id = f"{admin_id}_{timestamp}"  # Unique entry ID

    try:
        # Insert user data into MongoDB
        user_data = {
            "entry_id": entry_id,
            "admin_id": admin_id,
            "title": title,
            "username": username,
            "password": password,
            "timestamp": timestamp
        }
        users.insert_one(user_data)
        await ctx.send(f"Data stored successfully under title '{title}'!")
    except Exception as e:
        await ctx.send(f"An error occurred while storing data: {str(e)}")

# Command to fetch all entries for an admin
@bot.command()
async def fetch_all(ctx):
    admin_id = str(ctx.author.id)

    try:
        # Fetch all entries for the admin
        entries = list(users.find({"admin_id": admin_id}))
        if entries:
            response = "Your stored entries:\n"
            for entry in entries:
                response += f"**Title:** {entry['title']}, **Username:** {entry['username']}, **Password:** {entry['password']}, **Timestamp:** {entry['timestamp']}\n"
            await ctx.send(response)
        else:
            await ctx.send("No data found for you.")
    except Exception as e:
        await ctx.send(f"An error occurred while fetching data: {str(e)}")

# Command to fetch a specific entry by title
@bot.command()
async def fetch(ctx, title: str):
    admin_id = str(ctx.author.id)

    try:
        # Fetch a specific entry by title with case-sensitive collation
        entry = users.find_one(
            {"admin_id": admin_id, "title": title},
            collation={"locale": "en", "strength": 3}
        )
        if entry:
            await ctx.send(f"**Title:** {entry['title']}, **Username:** {entry['username']}, **Password:** {entry['password']}, **Timestamp:** {entry['timestamp']}")
        else:
            await ctx.send(f"No data found for title '{title}'.")
    except Exception as e:
        await ctx.send(f"An error occurred while fetching data: {str(e)}")

# Command to delete a specific entry by title
@bot.command()
async def delete(ctx, title: str):
    admin_id = str(ctx.author.id)

    try:
        # Delete a specific entry by title with case-sensitive collation
        result = users.delete_one(
            {"admin_id": admin_id, "title": title},
            collation={"locale": "en", "strength": 3}
        )
        if result.deleted_count > 0:
            await ctx.send(f"Data with title '{title}' deleted successfully!")
        else:
            await ctx.send(f"No data found for title '{title}'.")
    except Exception as e:
        await ctx.send(f"An error occurred while deleting data: {str(e)}")

bot.run(DISCORD_TOKEN)
