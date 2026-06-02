import discord
from discord.ext import commands
from discord import SlashCommandGroup
from utils.embeds import base_embed, success_embed, error_embed, RLEC_COLOR


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def send_welcome(self, member: discord.Member):
        cfg = await self.bot.db.get_config(member.guild.id)
        ch_id = cfg.get("welcome_channel")
        if not ch_id:
            return
        channel = member.guild.get_channel(int(ch_id))
        if not channel:
            return

        msg = (cfg.get("welcome_message") or "🚗 Bienvenue {mention} sur **RLEC** !").replace(
            "{mention}", member.mention
        ).replace("{name}", member.display_name).replace("{server}", member.guild.name)

        e = base_embed(
            title="🏎️  Bienvenue sur RLEC !",
            description=msg,
        )
        e.set_thumbnail(url=member.display_avatar.url)
        e.add_field(
            name="📋 Premiers pas",
            value="• Consulte le règlement\n• Récupère tes rôles\n• Rejoins ou crée une équipe",
            inline=False,
        )
        e.set_image(url="https://i.imgur.com/rlec_banner.png")

        view = WelcomeView(member.guild)
        try:
            await channel.send(embed=e, view=view)
        except Exception:
            pass

        # Attribution du rôle de bienvenue
        role_id = cfg.get("welcome_role")
        if role_id:
            role = member.guild.get_role(int(role_id))
            if role:
                try:
                    await member.add_roles(role, reason="RLEC bienvenue automatique")
                except Exception:
                    pass

    # ─── Slash Commands ───────────────────────────────────────────────────────
    welcome = SlashCommandGroup("welcome", "Commandes bienvenue (staff)")

    @welcome.command(name="set_channel", description="Définir le salon de bienvenue")
    @commands.has_permissions(manage_guild=True)
    async def set_channel(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        await self.bot.db.set_config(ctx.guild_id, "welcome_channel", channel.id)
        await ctx.respond(embed=success_embed("Salon de bienvenue défini", f"→ {channel.mention}"), ephemeral=True)

    @welcome.command(name="set_role", description="Rôle attribué automatiquement à l'arrivée")
    @commands.has_permissions(manage_guild=True)
    async def set_role(self, ctx: discord.ApplicationContext, role: discord.Role):
        await self.bot.db.set_config(ctx.guild_id, "welcome_role", role.id)
        await ctx.respond(embed=success_embed("Rôle de bienvenue défini", f"→ {role.mention}"), ephemeral=True)

    @welcome.command(name="set_message", description="Message de bienvenue ({mention}, {name}, {server})")
    @commands.has_permissions(manage_guild=True)
    async def set_message(self, ctx: discord.ApplicationContext, message: str):
        await self.bot.db.set_config(ctx.guild_id, "welcome_message", message)
        await ctx.respond(embed=success_embed("Message de bienvenue mis à jour", f"```{message}```"), ephemeral=True)

    @welcome.command(name="test", description="Tester le message de bienvenue")
    @commands.has_permissions(manage_guild=True)
    async def test(self, ctx: discord.ApplicationContext):
        await self.send_welcome(ctx.author)
        await ctx.respond(embed=success_embed("Test envoyé !"), ephemeral=True)


class WelcomeView(discord.ui.View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        self.guild = guild

    @discord.ui.button(label="📋 Règlement", style=discord.ButtonStyle.secondary, custom_id="welcome_rules")
    async def rules_btn(self, button, interaction):
        await interaction.response.send_message(
            "📋 Consulte le salon **#règlement** du serveur !", ephemeral=True
        )

    @discord.ui.button(label="🎟️ Tickets", style=discord.ButtonStyle.secondary, custom_id="welcome_ticket")
    async def ticket_btn(self, button, interaction):
        await interaction.response.send_message(
            "🎟️ Utilise `/ticket` ou rends-toi dans le salon **#support** pour ouvrir un ticket.", ephemeral=True
        )

    @discord.ui.button(label="🏎️ Équipes", style=discord.ButtonStyle.secondary, custom_id="welcome_teams")
    async def teams_btn(self, button, interaction):
        await interaction.response.send_message(
            "🏎️ Utilise `/team create` pour créer une équipe, ou `/team join` pour rejoindre celle d'un ami !", ephemeral=True
        )


def setup(bot):
    bot.add_cog(Welcome(bot))
