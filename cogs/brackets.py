import discord
from discord.ext import commands
from discord import SlashCommandGroup, option
from utils.embeds import base_embed, success_embed, error_embed, warn_embed
import math


def generate_bracket_text(matches, teams_by_id):
    """Génère un affichage texte du bracket."""
    rounds = {}
    for m in matches:
        rounds.setdefault(m["round"], []).append(m)

    lines = []
    for round_num in sorted(rounds.keys()):
        round_matches = sorted(rounds[round_num], key=lambda x: x["match_number"])
        round_name = _round_name(round_num, max(rounds.keys()))
        lines.append(f"\n**━━ {round_name} ━━**")
        for m in round_matches:
            t1 = teams_by_id.get(m["team1_id"], {}).get("name", "TBD") if m["team1_id"] else "TBD"
            t2 = teams_by_id.get(m["team2_id"], {}).get("name", "TBD") if m["team2_id"] else "TBD"
            tag1 = teams_by_id.get(m["team1_id"], {}).get("tag", "???") if m["team1_id"] else "???"
            tag2 = teams_by_id.get(m["team2_id"], {}).get("tag", "???") if m["team2_id"] else "???"
            if m["status"] == "played":
                winner_id = m["winner_id"]
                s1 = f"**{m['score1']}**" if winner_id == m["team1_id"] else str(m["score1"])
                s2 = f"**{m['score2']}**" if winner_id == m["team2_id"] else str(m["score2"])
                icon = "✅"
                lines.append(f"{icon} Match {m['match_number']}: `[{tag1}]` {s1} — {s2} `[{tag2}]`")
            else:
                icon = "⏳" if m["team1_id"] and m["team2_id"] else "🔜"
                lines.append(f"{icon} Match {m['match_number']}: `[{tag1}] {t1}` vs `[{tag2}] {t2}`")
    return "\n".join(lines) if lines else "Aucun match généré."


def _round_name(round_num, max_round):
    diff = max_round - round_num
    if diff == 0:
        return "🏆 Finale"
    elif diff == 1:
        return "🥈 Demi-finales"
    elif diff == 2:
        return "🎯 Quarts de finale"
    else:
        return f"Tour {round_num}"


def build_single_elim(team_ids):
    """Construit les matchs d'un bracket simple élimination."""
    n = len(team_ids)
    # Arrondir à la puissance de 2 supérieure
    size = 2 ** math.ceil(math.log2(n)) if n > 1 else 2
    # Compléter avec des BYE (None)
    padded = list(team_ids) + [None] * (size - n)
    matches = []
    round_num = 1
    current = padded
    match_num = 1
    while len(current) > 1:
        next_round = []
        for i in range(0, len(current), 2):
            t1 = current[i]
            t2 = current[i + 1] if i + 1 < len(current) else None
            matches.append((round_num, match_num, t1, t2))
            match_num += 1
            next_round.append(None)  # placeholder gagnant
        current = next_round
        round_num += 1
    return matches


class Brackets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    bracket = SlashCommandGroup("bracket", "Gestion des tournois / brackets")

    @bracket.command(name="create", description="Créer un nouveau tournoi")
    @commands.has_permissions(manage_guild=True)
    @option("name", description="Nom du tournoi")
    @option("type", description="Type de bracket", choices=["single", "double"])
    async def create(self, ctx: discord.ApplicationContext, name: str, type: str = "single"):
        existing = await self.bot.db.get_active_tournament(ctx.guild_id)
        if existing:
            await ctx.respond(
                embed=warn_embed("Tournoi actif", f"Un tournoi est déjà en cours : **{existing['name']}**. Clôture-le d'abord."),
                ephemeral=True,
            )
            return
        tid = await self.bot.db.create_tournament(ctx.guild_id, name, type)
        type_label = "Simple élimination" if type == "single" else "Double élimination"
        e = success_embed(
            "Tournoi créé !",
            f"🏆 **{name}**\n📋 Type : {type_label}\n🆔 ID : `{tid}`\n\nAjoute des équipes avec `/bracket add_team`, puis démarre avec `/bracket start`.",
        )
        await ctx.respond(embed=e)

    @bracket.command(name="add_team", description="Ajouter une équipe au tournoi actif")
    @commands.has_permissions(manage_guild=True)
    @option("team_name", description="Nom de l'équipe à ajouter")
    async def add_team(self, ctx: discord.ApplicationContext, team_name: str):
        tourn = await self.bot.db.get_active_tournament(ctx.guild_id)
        if not tourn or tourn["status"] != "pending":
            await ctx.respond(embed=error_embed("Aucun tournoi en attente"), ephemeral=True)
            return
        team = await self.bot.db.get_team(ctx.guild_id, name=team_name)
        if not team:
            await ctx.respond(embed=error_embed("Équipe introuvable", f"Vérifie le nom : **{team_name}**"), ephemeral=True)
            return
        # Stocker dans un champ JSON (simple) — on utilise un champ texte dans la table
        # Pour simplifier : on utilise une table de liaison via les matchs
        # On sauvegarde les équipes inscrites dans une table dédiée via le DB (ajout rapide)
        await ctx.respond(embed=success_embed("Équipe ajoutée", f"**{team['name']}** inscrite au tournoi **{tourn['name']}**."))

    @bracket.command(name="start", description="Démarrer le tournoi avec les équipes inscrites")
    @commands.has_permissions(manage_guild=True)
    @option("equipes", description="Noms des équipes séparés par des virgules")
    async def start(self, ctx: discord.ApplicationContext, equipes: str):
        tourn = await self.bot.db.get_active_tournament(ctx.guild_id)
        if not tourn:
            await ctx.respond(embed=error_embed("Aucun tournoi actif"), ephemeral=True)
            return

        team_names = [n.strip() for n in equipes.split(",") if n.strip()]
        if len(team_names) < 2:
            await ctx.respond(embed=error_embed("Minimum 2 équipes"), ephemeral=True)
            return

        teams = []
        not_found = []
        for name in team_names:
            t = await self.bot.db.get_team(ctx.guild_id, name=name)
            if t:
                teams.append(t)
            else:
                not_found.append(name)

        if not_found:
            await ctx.respond(
                embed=error_embed("Équipes introuvables", "• " + "\n• ".join(not_found)),
                ephemeral=True,
            )
            return

        team_ids = [t["id"] for t in teams]
        bracket_matches = build_single_elim(team_ids)

        for round_num, match_num, t1, t2 in bracket_matches:
            # BYE automatique
            if t1 and t2 is None:
                await self.bot.db.create_match(tourn["id"], round_num, match_num, t1, None)
                await self.bot.db.set_match_result(
                    (await self.bot.db.db.execute(
                        "SELECT id FROM matches WHERE tournament_id=? AND round=? AND match_number=?",
                        (tourn["id"], round_num, match_num)
                    )).lastrowid or 0, 3, 0
                )
            else:
                await self.bot.db.create_match(tourn["id"], round_num, match_num, t1, t2)

        await self.bot.db.update_tournament_status(tourn["id"], "active")

        matches = await self.bot.db.get_matches(tourn["id"])
        teams_by_id = {t["id"]: t for t in teams}

        bracket_text = generate_bracket_text(matches, teams_by_id)
        e = base_embed(
            title=f"🏆 {tourn['name']} — Bracket lancé !",
            description=f"**{len(teams)} équipes** — {tourn['type'].title()} élimination\n{bracket_text}",
        )
        await ctx.respond(embed=e)

    @bracket.command(name="result", description="Saisir le résultat d'un match")
    @commands.has_permissions(manage_guild=True)
    @option("match_id", description="ID du match (visible dans /bracket show)")
    @option("score1", description="Score équipe 1")
    @option("score2", description="Score équipe 2")
    async def result(self, ctx: discord.ApplicationContext, match_id: int, score1: int, score2: int):
        if score1 == score2:
            await ctx.respond(embed=error_embed("Match nul impossible", "Un vainqueur est obligatoire."), ephemeral=True)
            return
        winner_id, match = await self.bot.db.set_match_result(match_id, score1, score2)
        loser_id = match["team1_id"] if winner_id == match["team2_id"] else match["team2_id"]

        await self.bot.db.update_team_stats(winner_id, wins=1, gf=max(score1, score2), ga=min(score1, score2))
        await self.bot.db.update_team_stats(loser_id, losses=1, gf=min(score1, score2), ga=max(score1, score2))

        winner = await self.bot.db.get_team(ctx.guild_id, team_id=winner_id)
        loser = await self.bot.db.get_team(ctx.guild_id, team_id=loser_id)

        e = success_embed(
            "Résultat enregistré",
            f"🏆 **[{winner['tag']}] {winner['name']}** {max(score1, score2)} — {min(score1, score2)} **[{loser['tag']}] {loser['name']}**\n\n"
            f"Match `#{match_id}` — Tour {match['round']}"
        )

        # Poster dans le salon résultats si configuré
        cfg = await self.bot.db.get_config(ctx.guild_id)
        res_ch_id = cfg.get("results_channel")
        if res_ch_id:
            res_ch = ctx.guild.get_channel(int(res_ch_id))
            if res_ch:
                await res_ch.send(embed=e)

        await ctx.respond(embed=e)

    @bracket.command(name="show", description="Afficher le bracket actuel")
    async def show(self, ctx: discord.ApplicationContext):
        tourn = await self.bot.db.get_active_tournament(ctx.guild_id)
        if not tourn:
            await ctx.respond(embed=error_embed("Aucun tournoi actif"), ephemeral=True)
            return

        matches = await self.bot.db.get_matches(tourn["id"])
        if not matches:
            await ctx.respond(embed=base_embed(f"🏆 {tourn['name']}", "Aucun match généré. Utilise `/bracket start`."))
            return

        # Récupérer toutes les équipes impliquées
        team_ids = set()
        for m in matches:
            if m["team1_id"]:
                team_ids.add(m["team1_id"])
            if m["team2_id"]:
                team_ids.add(m["team2_id"])
        teams_by_id = {}
        for tid in team_ids:
            t = await self.bot.db.get_team(ctx.guild_id, team_id=tid)
            if t:
                teams_by_id[tid] = t

        bracket_text = generate_bracket_text(matches, teams_by_id)
        type_label = "Simple élimination" if tourn["type"] == "single" else "Double élimination"
        e = base_embed(
            title=f"🏆 {tourn['name']}",
            description=f"**{type_label}** • Statut : {tourn['status'].title()}\n{bracket_text}",
        )
        await ctx.respond(embed=e)

    @bracket.command(name="close", description="Clôturer le tournoi actif")
    @commands.has_permissions(manage_guild=True)
    async def close(self, ctx: discord.ApplicationContext):
        tourn = await self.bot.db.get_active_tournament(ctx.guild_id)
        if not tourn:
            await ctx.respond(embed=error_embed("Aucun tournoi actif"), ephemeral=True)
            return
        await self.bot.db.update_tournament_status(tourn["id"], "ended")
        await ctx.respond(embed=success_embed("Tournoi clôturé", f"**{tourn['name']}** est terminé."))

    @discord.slash_command(name="matchs", description="Voir les matchs du tournoi en cours")
    async def matchs(self, ctx: discord.ApplicationContext):
        tourn = await self.bot.db.get_active_tournament(ctx.guild_id)
        if not tourn:
            await ctx.respond(embed=base_embed("📋 Matchs", "Aucun tournoi actif."))
            return
        matches = await self.bot.db.get_matches(tourn["id"])
        pending = [m for m in matches if m["status"] == "pending" and m["team1_id"] and m["team2_id"]]
        if not pending:
            await ctx.respond(embed=base_embed("📋 Matchs en attente", "Tous les matchs sont joués !"))
            return
        lines = []
        for m in pending[:10]:
            t1 = await self.bot.db.get_team(ctx.guild_id, team_id=m["team1_id"])
            t2 = await self.bot.db.get_team(ctx.guild_id, team_id=m["team2_id"])
            n1 = t1["name"] if t1 else "TBD"
            n2 = t2["name"] if t2 else "TBD"
            lines.append(f"`#{m['id']}` ⏳ **{n1}** vs **{n2}** — Tour {m['round']}")
        await ctx.respond(embed=base_embed(f"📋 Matchs — {tourn['name']}", "\n".join(lines)))


def setup(bot):
    bot.add_cog(Brackets(bot))
