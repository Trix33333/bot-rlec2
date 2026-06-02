import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("❌ ERREUR : DISCORD_TOKEN manquant !")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
bot.scheduler = AsyncIOScheduler()

async def setup():
    await init_db()
    bot.scheduler.start()
    
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"✅ Chargé : {filename}")
            except Exception as e:
                print(f"❌ Échec : {filename} - {e}")

@bot.event
async def on_ready():
    print(f"🚀 Connecté : {bot.user.name}")
    synced = await bot.tree.sync()
    print(f"🔄 {len(synced)} commandes synchronisées.")

async def main():
    async with bot:
        await setup()
        await bot.start(TOKEN)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
