import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from utils.database import init_db
from apscheduler.schedulers.asyncio import AsyncIOScheduler

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("❌ ERREUR FATALE : La variable d'environnement DISCORD_TOKEN est manquante !")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# On attache le scheduler au bot
bot.scheduler = AsyncIOScheduler()

async def setup():
    """Charge la BDD et tous les cogs"""
    await init_db()
    bot.scheduler.start()
    
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"✅ Chargé : {filename}")
            except Exception as e:
                print(f"❌ Échec du chargement de {filename} : {e}")

@bot.event
async def on_ready():
    print(f"🚀 Connecté en tant que {bot.user.name} (ID: {bot.user.id})")
    synced = await bot.tree.sync()
    print(f"🔄 {len(synced)} commandes slash synchronisées.")

async def main():
    async with bot:
        await setup()
        await bot.start(TOKEN)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
