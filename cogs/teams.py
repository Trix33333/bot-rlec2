import discord
from discord.ext import commands
from discord import SlashCommandGroup, option
from utils.embeds import base_embed, success_embed, error_embed, warn_embed, RLEC_COLOR


class Teams(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    team = SlashCommandGroup("team", "Gestion des équipes")

    # ─── Création ─────────────────────────────────────────────────────────────
    @team.command(name="create", description="Créer une nouvelle équipe")
    @option("name", description="Nom de l'équipe")
    @option("tag", description="Tag court (ex: RLEC) — max 5 caractères")
    async def create(self, ctx: discord.ApplicationContext, name: str, tag: str):
        tag = tag.upper()[:5]
        if len(name) > 30:
            await ctx.respond(embed=error_embed("Nom trop long", "Max 30 caractères."), ephemeral=True)
            return

        existing = await self.bot.db.get_team_by_user(ctx.guild_id, ctx.author.id)
        if existing:
            await ctx.respond(
                embed=error_embed("Déjà dans une équipe", f"Tu fais déjà partie de **{existing['name']}**."),
                ephemeral=True,
            )
            return

        existing_name = await self.bot.db.get_team(ctx.guild_id, name=name)
        if existing_name:
            await ctx.respond(embed=error_embed("Nom déjà pris", f"Une équipe nommée **{name}** existe déjà."), ephemeral=True)
            return

        team_id = await self.bot.db.create_team(ctx.guild_id, name, tag, ctx.author.id)
        e = success_embed(
            "Équipe créée !",
            f"🏎️ **[{tag}] {name}**\n\nCapitaine : {ctx.author.mention}\nUtilise `/team invite` pour inviter des coéquipiers.",
        )
        await ctx.respond(embed=e)

    # ─── Info ─────────────────────────────────────────────────────────────────
    @team.command(name="info", description="Voir les infos d'une équipe")
    @option("name", description="Nom de l'équipe (laisser vide = ton équipe)", required=False)
    async def info(self, ctx: discord.ApplicationContext, name: str = None):
        if name:
            t = await self.bot.db.get_team(ctx.guild_id, name=name)
        else:
            t = await self.bot.db.get_team_by_user(ctx.guild_id, ctx.author.id)

        if not t:
            await ctx.respond(embed=error_embed("Équipe introuvable"), ephemeral=True)
            return

        members = await self.bot.db.get_team_members(t["id"])
        member_lines = []
        for m in members:
            user = ctx.guild.get_member(m["user_id"])
            name_str = user.mention if user else f"<@{m['user_id']}>"
            role_icon = "👑" if m["role"] == "captain" else ("🔄" if m["role"] == "substitute" else "🎮")
            member_lines.append(f"{role_icon} {name_str}")

        total = t["wins"] + t["losses"]
        ratio = f"{t['wins']/total*100:.0f}%" if total else "N/A"

        e = base_embed(title=f"🏎️ [{t['tag']}] {t['name']}")
        e.add_field(name="👥 Roster", value="\n".join(member_lines) if member_lines else "Vide", inline=True)
        e.add_field(
            name="📊 Bilan",
            value=f"**V:** {t['wins']}  **D:** {t['losses']}\n**Ratio:** {ratio}\n**Buts:** {t['goals_for']} / {t['goals_against']}",
            inline=True,
        )
        await ctx.respond(embed=e)

    # ─── Roster ───────────────────────────────────────────────────────────────
    @team.command(name="invite", description="Inviter un joueur dans ton équipe")
    @option("member", description="Joueur à inviter")
    async def invite(self, ctx: discord.ApplicationContext, member: discord.Member):
        t = await self.bot.db.get_team_by_user(ctx.guild_id, ctx.author.id)
        if not t:
            await ctx.respond(embed=error_embed("Tu n'as pas d'équipe"), ephemeral=True)
            return
        if t["captain_id"] != ctx.author.id:
            await ctx.respond(embed=error_embed("Seul le capitaine peut inviter"), ephemeral=True)
            return
        existing = await self.bot.db.get_team_by_user(ctx.guild_id, member.id)
        if existing:
            await ctx.respond(embed=error_embed("Joueur déjà dans une équipe"), ephemeral=True)
            return

        view = InviteView(self.bot, t, member)
        e = base_embed(
            title="📨 Invitation",
            description=f"{member.mention}, tu es invité(e) à rejoindre **[{t['tag']}] {t['name']}** !\n\nAcceptes-tu ?",
        )
        await ctx.respond(embed=e, view=view)

    @team.command(name="kick", description="Exclure un joueur de ton équipe")
    @option("member", description="Joueur à exclure")
    async def kick(self, ctx: discord.ApplicationContext, member: discord.Member):
        t = await self.bot.db.get_team_by_user(ctx.guild_id, ctx.author.id)
        if not t or t["captain_id"] != ctx.author.id:
            await ctx.respond(embed=error_embed("Capitaine uniquement"), ephemeral=True)
            return
        if member.id == ctx.author.id:
            await ctx.respond(embed=error_embed("Tu ne peux pas t'exclure toi-même"), ephemeral=True)
            return
        await self.bot.db.remove_team_member(t["id"], member.id)
        await ctx.respond(embed=success_embed("Joueur exclu", f"{member.mention} a été retiré de l'équipe."))

    @team.command(name="leave", description="Quitter ton équipe")
    async def leave(self, ctx: discord.ApplicationContext):
        t = await self.bot.db.get_team_by_user(ctx.guild_id, ctx.author.id)
        if not t:
            await ctx.respond(embed=error_embed("Tu n'es dans aucune équipe"), ephemeral=True)
            return
        if t["captain_id"] == ctx.author.id:
            await ctx.respond(
                embed=warn_embed("Capitaine", "Tu es capitaine, utilise `/team disband` pour dissoudre l'équipe."),
                ephemeral=True,
            )
            return
        await self.bot.db.remove_team_member(t["id"], ctx.author.id)
        await ctx.respond(embed=success_embed("Équipe quittée", f"Tu as quitté **{t['name']}**."))

    @team.command(name="disband", description="Dissoudre ton équipe (capitaine)")
    async def disband(self, ctx: discord.ApplicationContext):
        t = await self.bot.db.get_team_by_user(ctx.guild_id, ctx.author.id)
        if not t or t["captain_id"] != ctx.author.id:
            await ctx.respond(embed=error_embed("Capitaine uniquement"), ephemeral=True)
            return
        view = ConfirmDisbandView(self.bot, t)
        await ctx.respond(
            embed=warn_embed("Confirmation", f"Es-tu sûr de vouloir dissoudre **{t['name']}** ? Cette action est irréversible."),
            view=view,
        )

    @team.command(name="transfer", description="Transférer la capitainerie")
    @option("member", description="Nouveau capitaine")
    async def transfer(self, ctx: discord.ApplicationContext, member: discord.Member):
        t = await self.bot.db.get_team_by_user(ctx.guild_id, ctx.author.id)
        if not t or t["captain_id"] != ctx.author.id:
            await ctx.respond(embed=error_embed("Capitaine uniquement"), ephemeral=True)
            return
        member_t = await self.bot.db.get_team_by_user(ctx.guild_id, member.id)
        if not member_t or member_t["id"] != t["id"]:
            await ctx.respond(embed=error_embed("Ce joueur n'est pas dans ton équipe"), ephemeral=True)
            return
        await self.bot.db.add_team_member(t["id"], ctx.author.id, "player")
        await self.bot.db.add_team_member(t["id"], member.id, "captain")
        async with self.bot.db.db.execute(
            "UPDATE teams SET captain_id=? WHERE id=?", (member.id, t["id"])
        ):
            await self.bot.db.db.commit()
        await ctx.respond(embed=success_embed("Capitainerie transférée", f"{member.mention} est maintenant capitaine de **{t['name']}**."))

    # ─── Stats & Classement ───────────────────────────────────────────────────
    @team.command(name="stats", description="Statistiques d'une équipe")
    @option("name", description="Nom de l'équipe (vide = la tienne)", required=False)
    async def stats(self, ctx: discord.ApplicationContext, name: str = None):
        if name:
            t = await self.bot.db.get_team(ctx.guild_id, name=name)
        else:
            t = await self.bot.db.get_team_by_user(ctx.guild_id, ctx.author.id)
        if not t:
            await ctx.respond(embed=error_embed("Équipe introuvable"), ephemeral=True)
            return
        total = t["wins"] + t["losses"]
        ratio = f"{t['wins']/total*100:.1f}%" if total else "0%"
        diff = t["goals_for"] - t["goals_against"]
        diff_str = f"+{diff}" if diff >= 0 else str(diff)
        e = base_embed(title=f"📊 Stats — [{t['tag']}] {t['name']}")
        e.add_field(name="🏆 Victoires", value=str(t["wins"]), inline=True)
        e.add_field(name="💀 Défaites", value=str(t["losses"]), inline=True)
        e.add_field(name="📈 Win Rate", value=ratio, inline=True)
        e.add_field(name="⚽ Buts marqués", value=str(t["goals_for"]), inline=True)
        e.add_field(name="🥅 Buts encaissés", value=str(t["goals_against"]), inline=True)
        e.add_field(name="📉 Différentiel", value=diff_str, inline=True)
        await ctx.respond(embed=e)

    @discord.slash_command(name="classement", description="Classement des équipes")
    async def classement(self, ctx: discord.ApplicationContext):
        teams = await self.bot.db.get_all_teams(ctx.guild_id)
        if not teams:
            await ctx.respond(embed=base_embed("🏆 Classement", "Aucune équipe enregistrée."))
            return
        lines = []
        medals = ["🥇", "🥈", "🥉"]
        for i, t in enumerate(teams[:10]):
            prefix = medals[i] if i < 3 else f"`{i+1}.`"
            total = t["wins"] + t["losses"]
            ratio = f"{t['wins']/total*100:.0f}%" if total else "0%"
            lines.append(f"{prefix} **[{t['tag']}] {t['name']}** — V:{t['wins']} D:{t['losses']} ({ratio})")
        e = base_embed("🏆 Classement RLEC", "\n".join(lines))
        await ctx.respond(embed=e)


class InviteView(discord.ui.View):
    def __init__(self, bot, team, target):
        super().__init__(timeout=60)
        self.bot = bot
        self.team = team
        self.target = target

    @discord.ui.button(label="✅ Accepter", style=discord.ButtonStyle.success)
    async def accept(self, button, interaction):
        if interaction.user.id != self.target.id:
            await interaction.response.send_message("❌ Ce n'est pas ton invitation.", ephemeral=True)
            return
        await self.bot.db.add_team_member(self.team["id"], self.target.id, "player")
        await interaction.response.edit_message(
            embed=success_embed("Invitation acceptée !", f"{self.target.mention} a rejoint **{self.team['name']}** !"),
            view=None,
        )

    @discord.ui.button(label="❌ Refuser", style=discord.ButtonStyle.danger)
    async def decline(self, button, interaction):
        if interaction.user.id != self.target.id:
            await interaction.response.send_message("❌ Ce n'est pas ton invitation.", ephemeral=True)
            return
        await interaction.response.edit_message(
            embed=error_embed("Invitation refusée", f"{self.target.mention} a refusé l'invitation."),
            view=None,
        )


class ConfirmDisbandView(discord.ui.View):
    def __init__(self, bot, team):
        super().__init__(timeout=30)
        self.bot = bot
        self.team = team

    @discord.ui.button(label="🗑️ Confirmer", style=discord.ButtonStyle.danger)
    async def confirm(self, button, interaction):
        await self.bot.db.delete_team(self.team["id"])
        await interaction.response.edit_message(
            embed=success_embed("Équipe dissoute", f"**{self.team['name']}** a été supprimée."), view=None
        )

    @discord.ui.button(label="Annuler", style=discord.ButtonStyle.secondary)
    async def cancel(self, button, interaction):
        await interaction.response.edit_message(embed=base_embed("❎ Annulé"), view=None)


def setup(bot):
    bot.add_cog(Teams(bot))
