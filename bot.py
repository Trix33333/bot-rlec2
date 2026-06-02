import asyncio
import logging
import os

import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from discord.ext import commands
from dotenv import load_dotenv

from utils.database import init_db

# ==========================================================
# CONFIGURATION DES LOGS (Idéal pour Railway)
# ==========================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-7s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# ==========================================================
# CHARGEMENT DES VARIABLES
# ==========================================================
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    logger.critical(" ERREUR FATALE : La variable DISCORD_TOKEN est manquante !")
    exit(1)

# ==========================================================
# INITIALISATION DU BOT
# ==========================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix="!", 
    intents=intents, 
    help_command=None,
    activity=discord.Activity(type=discord.ActivityType.watching, name="RLEC Esport")
)

# Attachement du planificateur de tâches au bot
bot.scheduler = AsyncIOScheduler()

# ==========================================================
# FONCTIONS DE DÉMARRAGE
# ==========================================================
async def load_cogs():
    """Charge dynamiquement tous les cogs du dossier ./cogs"""
    cog_dir = "./cogs"
    if not os.path.exists(cog_dir):
        logger.warning(f"⚠️ Le dossier {cog_dir} est introuvable.")
        return

    for filename in os.listdir(cog_dir):
        # Ignore les fichiers système comme __init__.py
        if filename.endswith(".py") and not filename.startswith("__"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                logger.info(f"✅ Cog chargé : {filename}")
            except Exception as e:
                logger.error(f" Échec du chargement de {filename} : {e}")

async def setup():
    """Initialise la base de données, le scheduler et les cogs"""
    logger.info("🔧 Initialisation de la base de données SQLite...")
    await init_db()
    
    logger.info("⏰ Démarrage du planificateur de tâches...")
    bot.scheduler.start()
    
    logger.info(" Chargement des extensions (cogs)...")
    await load_cogs()

# ==========================================================
# ÉVÉNEMENTS DISCORD
# ==========================================================
@bot.event
async def on_ready():
    """Déclenché quand le bot est connecté et prêt"""
    logger.info(f" Bot connecté en tant que : {bot.user} (ID: {bot.user.id})")
    
    # Synchronisation des commandes slash (/)
    try:
        synced = await bot.tree.sync()
        logger.info(f"🔄 {len(synced)} commandes slash synchronisées avec succès.")
    except Exception as e:
        logger.error(f" Erreur de synchronisation des commandes : {e}")

# ==========================================================
# POINT D'ENTRÉE PRINCIPAL
# ==========================================================
async def main():
    """Lance le bot de manière asynchrone"""
    async with bot:
        await setup()
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
