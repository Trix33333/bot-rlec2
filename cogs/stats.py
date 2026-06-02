import discord
from discord.ext import commands
from discord import SlashCommandGroup, option
from utils.embeds import base_embed, success_embed, error_embed


STAT_LABELS = {
    "goals":           ("⚽", "Buts"),
    "assists":         ("🎯", "Passes décisives"),
    "saves":           ("🧤", "Arrêts"),
    "shots":           ("🔫", "Tirs"),
    "mvp_count":       ("🌟", "MVP"),
    "matches_played":  ("🎮", "Matchs joués"),
}


class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    stats_cmd = SlashCommandGroup("stats", "Statistiques joueurs")

    @stats_cmd.command(name="profile", description="Voir tes statistiques (ou celles d'un joueur)")
    @option("member", description="Joueur (vide = toi)", required=False)
    async def profile(self, ctx: discord.ApplicationContext, member: discord.Member = None):
        target = member or ctx.author
        s = await self.bot.db.get_player_stats(target.id, ctx.guild_id)
        team = await self.bot.db.get_team_by_user(ctx.guild_id, target.id)

        e = base_embed(title=f"📊 {target.display_name}")
        e.set_thumbnail(url=target.display_avatar.url)

        for key, (icon, label) in STAT_LABELS.items():
            e.add_field(name=f"{icon} {label}", value=str(s.get(key, 0)), inline=True)

        if team:
            e.add_field(name="🏎️ Équipe", value=f"[{team['tag']}] {team['name']}", inline=False)

        total = s.get("matches_played", 0)
        if total > 0:
            avg_goals = s.get("goals", 0) / total
            e.add_field(name="📈 Moy. buts/match", value=f"{avg_goals:.2f}", inline=True)

        await ctx.respond(embed=e)

    @discord.slash_command(name="profile", description="Voir ton profil RLEC")
    @option("member", description="Joueur (vide = toi)", required=False)
    async def profile_shortcut(self, ctx: discord.ApplicationContext, member: discord.Member = None):
        await self.profile.callback(self, ctx, member)

    @stats_cmd.command(name="add", description="Ajouter des stats manuellement (staff)")
    @commands.has_permissions(manage_guild=True)
    @option("member", description="Joueur")
    @option("goals", description="Buts", required=False, default=0)
    @option("assists", description="Passes décisives", required=False, default=0)
    @option("saves", description="Arrêts", required=False, default=0)
    @option("shots", description="Tirs", required=False, default=0)
    @option("mvp", description="MVP (0 ou 1)", required=False, default=0)
    async def add_stats(
        self,
        ctx: discord.ApplicationContext,
        member: discord.Member,
        goals: int = 0,
        assists: int = 0,
        saves: int = 0,
        shots: int = 0,
        mvp: int = 0,
    ):
        await self.bot.db.update_player_stats(
            member.id, ctx.guild_id,
            goals=goals, assists=assists, saves=saves,
            shots=shots, mvp_count=mvp, matches_played=1,
        )
        lines = []
        if goals:   lines.append(f"⚽ +{goals} buts")
        if assists: lines.append(f"🎯 +{assists} passes")
        if saves:   lines.append(f"🧤 +{saves} arrêts")
        if shots:   lines.append(f"🔫 +{shots} tirs")
        if mvp:     lines.append(f"🌟 +{mvp} MVP")
        await ctx.respond(
            embed=success_embed(f"Stats mises à jour — {member.display_name}", "\n".join(lines) or "Aucune stat modifiée."),
            ephemeral=True,
        )

    @stats_cmd.command(name="reset", description="Remettre à zéro les stats d'un joueur (staff)")
    @commands.has_permissions(manage_guild=True)
    @option("member", description="Joueur")
    async def reset_stats(self, ctx: discord.ApplicationContext, member: discord.Member):
        async with self.bot.db.db.execute(
            "DELETE FROM player_stats WHERE user_id=? AND guild_id=?", (member.id, ctx.guild_id)
        ):
            await self.bot.db.db.commit()
        await ctx.respond(embed=success_embed("Stats réinitialisées", f"Stats de {member.mention} remises à zéro."), ephemeral=True)

    @discord.slash_command(name="rank", description="Classement des meilleurs joueurs")
    @option("stat", description="Statistique", choices=list(STAT_LABELS.keys()), required=False)
    async def rank(self, ctx: discord.ApplicationContext, stat: str = "goals"):
        lb = await self.bot.db.get_leaderboard(ctx.guild_id, stat=stat, limit=10)
        if not lb:
            await ctx.respond(embed=base_embed("🏅 Classement", "Aucune statistique enregistrée."))
            return

        icon, label = STAT_LABELS.get(stat, ("📊", stat))
        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for i, row in enumerate(lb):
            user = ctx.guild.get_member(row["user_id"])
            name = user.display_name if user else f"<@{row['user_id']}>"
            prefix = medals[i] if i < 3 else f"`{i+1}.`"
            lines.append(f"{prefix} **{name}** — {icon} {row[stat]}")

        e = base_embed(f"🏅 Top {label}", "\n".join(lines))
        await ctx.respond(embed=e)


def setup(bot):
    bot.add_cog(Stats(bot))
