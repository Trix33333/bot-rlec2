import discord
from discord.ext import commands
from discord import SlashCommandGroup, option
from utils.embeds import base_embed, success_embed, error_embed, RLEC_COLOR

ANNOUNCE_TYPES = {
    "saison":        ("🚀", "Début de saison",       0xe2231a),
    "match":         ("⚽", "Match à venir",         0x3498db),
    "resultats":     ("🏆", "Résultats",             0x2ecc71),
    "recrutement":   ("👥", "Recrutement",           0xf39c12),
    "info":          ("📢", "Information importante", 0x9b59b6),
    "maintenance":   ("🔧", "Maintenance",           0x95a5a6),
}


class Announcements(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    ann = SlashCommandGroup("annonce", "Gestion des annonces (staff)")

    @ann.command(name="send", description="Envoyer une annonce officielle")
    @commands.has_permissions(manage_guild=True)
    @option("type", description="Type d'annonce", choices=list(ANNOUNCE_TYPES.keys()))
    @option("title", description="Titre de l'annonce")
    @option("message", description="Contenu de l'annonce")
    @option("ping_role", description="Rôle à mentionner (optionnel)", required=False)
    @option("channel", description="Salon cible (vide = salon d'annonces configuré)", required=False)
    async def send(
        self,
        ctx: discord.ApplicationContext,
        type: str,
        title: str,
        message: str,
        ping_role: discord.Role = None,
        channel: discord.TextChannel = None,
    ):
        emoji, label, color = ANNOUNCE_TYPES[type]

        # Déterminer le salon cible
        target = channel
        if not target:
            cfg = await self.bot.db.get_config(ctx.guild_id)
            ch_id = cfg.get("announce_channel")
            if ch_id:
                target = ctx.guild.get_channel(int(ch_id))
        if not target:
            target = ctx.channel

        e = discord.Embed(
            title=f"{emoji}  {title}",
            description=message,
            color=color,
        )
        e.set_author(name="RLEC — Annonce officielle", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        e.set_footer(text=f"RLEC • {label}")
        import datetime
        e.timestamp = datetime.datetime.utcnow()

        mention = ping_role.mention if ping_role else ""
        await target.send(content=mention if mention else None, embed=e)
        await ctx.respond(embed=success_embed("Annonce envoyée", f"→ {target.mention}"), ephemeral=True)

    @ann.command(name="embed", description="Créer un embed personnalisé")
    @commands.has_permissions(manage_guild=True)
    @option("title", description="Titre")
    @option("description", description="Description")
    @option("color_hex", description="Couleur hex (ex: e2231a)", required=False)
    @option("channel", description="Salon cible", required=False)
    async def custom_embed(
        self,
        ctx: discord.ApplicationContext,
        title: str,
        description: str,
        color_hex: str = "e2231a",
        channel: discord.TextChannel = None,
    ):
        target = channel or ctx.channel
        try:
            color = int(color_hex.strip("#"), 16)
        except ValueError:
            color = RLEC_COLOR

        e = discord.Embed(title=title, description=description, color=color)
        import datetime
        e.set_footer(text="RLEC • Rocket League Esport Championship")
        e.timestamp = datetime.datetime.utcnow()
        await target.send(embed=e)
        await ctx.respond(embed=success_embed("Embed envoyé", f"→ {target.mention}"), ephemeral=True)

    @ann.command(name="set_channel", description="Définir le salon d'annonces")
    @commands.has_permissions(manage_guild=True)
    async def set_channel(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        await self.bot.db.set_config(ctx.guild_id, "announce_channel", channel.id)
        await ctx.respond(embed=success_embed("Salon d'annonces défini", f"→ {channel.mention}"), ephemeral=True)

    @ann.command(name="results_channel", description="Définir le salon des résultats de matchs")
    @commands.has_permissions(manage_guild=True)
    async def results_channel(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        await self.bot.db.set_config(ctx.guild_id, "results_channel", channel.id)
        await ctx.respond(embed=success_embed("Salon résultats défini", f"→ {channel.mention}"), ephemeral=True)


def setup(bot):
    bot.add_cog(Announcements(bot))
