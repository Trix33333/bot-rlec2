import discord
from discord.ext import commands
import os
import asyncio
from utils.database import Database

# ─── Configuration ────────────────────────────────────────────────────────────
TOKEN = os.getenv("DISCORD_TOKEN", "VOTRE_TOKEN_ICI")
PREFIX = "/"

intents = discord.Intents.all()

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None,
)

bot.db = Database("data/rlec.db")

COGS = [
    "cogs.welcome",
    "cogs.tickets",
    "cogs.teams",
    "cogs.brackets",
    "cogs.planning",
    "cogs.stats",
    "cogs.announcements",
    "cogs.admin",
    "cogs.help",
]

# ─── Events ───────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    await bot.db.init()
    print(f"✅  RLEC Bot connecté en tant que {bot.user} ({bot.user.id})")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="🏆 RLEC Championship"
        )
    )
    try:
        synced = await bot.sync_commands()
        print(f"✅  {len(synced)} slash commands synchronisées")
    except Exception as e:
        print(f"❌  Erreur sync commands : {e}")

@bot.event
async def on_member_join(member: discord.Member):
    welcome_cog = bot.cogs.get("Welcome")
    if welcome_cog:
        await welcome_cog.send_welcome(member)

@bot.event
async def on_application_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.respond("❌ Tu n'as pas les permissions nécessaires.", ephemeral=True)
    elif isinstance(error, commands.MissingRole):
        await ctx.respond("❌ Il te manque un rôle pour cette commande.", ephemeral=True)
    else:
        await ctx.respond(f"❌ Erreur : `{error}`", ephemeral=True)
        raise error

# ─── Load Cogs ────────────────────────────────────────────────────────────────
async def main():
    for cog in COGS:
        try:
            bot.load_extension(cog)
            print(f"✅  Cog chargé : {cog}")
        except Exception as e:
            print(f"❌  Erreur chargement {cog} : {e}")
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
