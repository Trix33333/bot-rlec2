import discord
from discord.ext import commands
from discord import SlashCommandGroup, option
from utils.embeds import base_embed, success_embed, error_embed


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    config = SlashCommandGroup("config", "Configuration du bot RLEC (admin)")

    @config.command(name="staff_role", description="Définir le rôle staff")
    @commands.has_permissions(administrator=True)
    async def staff_role(self, ctx: discord.ApplicationContext, role: discord.Role):
        await self.bot.db.set_config(ctx.guild_id, "staff_role", role.id)
        await ctx.respond(embed=success_embed("Rôle staff défini", f"→ {role.mention}"), ephemeral=True)

    @config.command(name="show", description="Voir la configuration actuelle")
    @commands.has_permissions(manage_guild=True)
    async def show_config(self, ctx: discord.ApplicationContext):
        cfg = await self.bot.db.get_config(ctx.guild_id)

        def ch(val):
            if not val:
                return "❌ Non défini"
            c = ctx.guild.get_channel(int(val))
            return c.mention if c else f"❌ Salon supprimé (`{val}`)"

        def role(val):
            if not val:
                return "❌ Non défini"
            r = ctx.guild.get_role(int(val))
            return r.mention if r else f"❌ Rôle supprimé (`{val}`)"

        e = base_embed(title="⚙️ Configuration RLEC")
        e.add_field(name="👋 Bienvenue", value=f"Salon : {ch(cfg.get('welcome_channel'))}\nRôle : {role(cfg.get('welcome_role'))}", inline=False)
        e.add_field(name="🎫 Tickets", value=f"Catégorie : {ch(cfg.get('ticket_category'))}\nLogs : {ch(cfg.get('ticket_log_channel'))}", inline=False)
        e.add_field(name="📢 Annonces", value=f"Annonces : {ch(cfg.get('announce_channel'))}\nRésultats : {ch(cfg.get('results_channel'))}", inline=False)
        e.add_field(name="📅 Planning", value=f"Salon : {ch(cfg.get('planning_channel'))}", inline=False)
        e.add_field(name="👥 Staff", value=f"Rôle : {role(cfg.get('staff_role'))}", inline=False)
        await ctx.respond(embed=e, ephemeral=True)

    @config.command(name="reset", description="Réinitialiser la configuration (irréversible)")
    @commands.has_permissions(administrator=True)
    async def reset_config(self, ctx: discord.ApplicationContext):
        view = ConfirmResetView(self.bot, ctx.guild_id)
        e = base_embed(
            title="⚠️ Réinitialisation",
            description="Es-tu sûr de vouloir réinitialiser **toute la configuration** du bot ? Cette action est irréversible.",
        )
        await ctx.respond(embed=e, view=view, ephemeral=True)

    @discord.slash_command(name="setup", description="Assistant de configuration rapide RLEC")
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx: discord.ApplicationContext):
        e = base_embed(
            title="🔧 Setup RLEC",
            description=(
                "Bienvenue dans l'assistant de configuration !\n\n"
                "Utilise les commandes suivantes pour configurer chaque module :\n\n"
                "**👋 Bienvenue**\n"
                "`/welcome set_channel` · `/welcome set_role` · `/welcome set_message`\n\n"
                "**🎫 Tickets**\n"
                "`/ticket set_category` · `/ticket set_log` · `/ticket panel`\n\n"
                "**📢 Annonces**\n"
                "`/annonce set_channel` · `/annonce results_channel`\n\n"
                "**📅 Planning**\n"
                "`/planning set_channel`\n\n"
                "**👥 Staff**\n"
                "`/config staff_role`\n\n"
                "**✅ Voir la config**\n"
                "`/config show`"
            ),
        )
        await ctx.respond(embed=e, ephemeral=True)

    @discord.slash_command(name="panel", description="Panneau d'administration RLEC")
    @commands.has_permissions(manage_guild=True)
    async def panel(self, ctx: discord.ApplicationContext):
        e = base_embed(title="🛠️ Panneau d'administration RLEC")
        e.add_field(
            name="🏆 Tournois",
            value="`/bracket create` · `/bracket start` · `/bracket result` · `/bracket close`",
            inline=False,
        )
        e.add_field(
            name="📢 Annonces",
            value="`/annonce send` · `/annonce embed`",
            inline=False,
        )
        e.add_field(
            name="📅 Planning",
            value="`/planning add` · `/planning list` · `/planning delete`",
            inline=False,
        )
        e.add_field(
            name="🎫 Tickets",
            value="`/ticket panel` · `/ticket list`",
            inline=False,
        )
        e.add_field(
            name="📊 Stats",
            value="`/stats add` · `/stats reset`",
            inline=False,
        )
        e.add_field(
            name="⚙️ Config",
            value="`/config show` · `/config staff_role` · `/setup`",
            inline=False,
        )
        await ctx.respond(embed=e, ephemeral=True)


class ConfirmResetView(discord.ui.View):
    def __init__(self, bot, guild_id):
        super().__init__(timeout=30)
        self.bot = bot
        self.guild_id = guild_id

    @discord.ui.button(label="🗑️ Confirmer la réinitialisation", style=discord.ButtonStyle.danger)
    async def confirm(self, button, interaction):
        await self.bot.db.db.execute("DELETE FROM config WHERE guild_id=?", (self.guild_id,))
        await self.bot.db.db.commit()
        from utils.embeds import success_embed
        await interaction.response.edit_message(embed=success_embed("Configuration réinitialisée"), view=None)

    @discord.ui.button(label="Annuler", style=discord.ButtonStyle.secondary)
    async def cancel(self, button, interaction):
        from utils.embeds import base_embed
        await interaction.response.edit_message(embed=base_embed("❎ Annulé"), view=None)


def setup(bot):
    bot.add_cog(Admin(bot))
