import discord
from discord.ext import commands
from discord import option
from utils.embeds import base_embed


HELP_PAGES = {
    "general": {
        "title": "📖 Aide générale",
        "commands": [
            ("/help", "Afficher l'aide"),
            ("/profile", "Voir ton profil et tes stats"),
            ("/rank", "Classement des meilleurs joueurs"),
            ("/classement", "Classement des équipes"),
            ("/matchs", "Matchs en attente"),
            ("/prochain-match", "Prochain match prévu"),
            ("/calendrier", "Calendrier complet"),
        ],
    },
    "equipes": {
        "title": "🏎️ Équipes",
        "commands": [
            ("/team create", "Créer une équipe"),
            ("/team info", "Infos d'une équipe"),
            ("/team invite", "Inviter un joueur"),
            ("/team kick", "Exclure un joueur"),
            ("/team leave", "Quitter son équipe"),
            ("/team disband", "Dissoudre l'équipe"),
            ("/team transfer", "Transférer la capitainerie"),
            ("/team stats", "Stats de l'équipe"),
        ],
    },
    "tournoi": {
        "title": "🏆 Tournois & Brackets",
        "commands": [
            ("/bracket show", "Afficher le bracket"),
            ("/matchs", "Voir les matchs en attente"),
            ("/prochain-match", "Prochain match"),
        ],
    },
    "staff": {
        "title": "🛠️ Commandes Staff",
        "commands": [
            ("/setup", "Assistant de configuration"),
            ("/config show", "Voir la configuration"),
            ("/config staff_role", "Définir le rôle staff"),
            ("/panel", "Panneau d'administration"),
            ("/bracket create", "Créer un tournoi"),
            ("/bracket start", "Démarrer le tournoi"),
            ("/bracket result", "Saisir un résultat"),
            ("/bracket close", "Clôturer le tournoi"),
            ("/annonce send", "Envoyer une annonce"),
            ("/ticket panel", "Afficher le panel tickets"),
            ("/planning add", "Ajouter un événement"),
            ("/stats add", "Ajouter des stats manuellement"),
            ("/welcome set_channel", "Configurer la bienvenue"),
        ],
    },
}


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="help", description="Afficher l'aide du bot RLEC")
    @option("category", description="Catégorie", choices=list(HELP_PAGES.keys()), required=False)
    async def help(self, ctx: discord.ApplicationContext, category: str = None):
        if category and category in HELP_PAGES:
            page = HELP_PAGES[category]
            e = base_embed(title=page["title"])
            lines = [f"`{cmd}` — {desc}" for cmd, desc in page["commands"]]
            e.description = "\n".join(lines)
            await ctx.respond(embed=e, ephemeral=True)
            return

        # Menu principal
        e = base_embed(
            title="🏎️ RLEC — Aide",
            description="Rocket League Esport Championship Bot\n\nChoisis une catégorie :",
        )
        for key, page in HELP_PAGES.items():
            cmd_preview = ", ".join(f"`{c}`" for c, _ in page["commands"][:3])
            e.add_field(name=page["title"], value=f"{cmd_preview}…", inline=False)

        e.add_field(
            name="💡 Astuce",
            value="Utilise `/help [category]` pour les détails d'une catégorie.",
            inline=False,
        )
        view = HelpView()
        await ctx.respond(embed=e, view=view, ephemeral=True)


class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        for key, page in HELP_PAGES.items():
            self.add_item(HelpButton(key, page["title"]))


class HelpButton(discord.ui.Button):
    def __init__(self, key, title):
        super().__init__(label=title, style=discord.ButtonStyle.secondary, custom_id=f"help_{key}")
        self.key = key

    async def callback(self, interaction: discord.Interaction):
        page = HELP_PAGES.get(self.key)
        if not page:
            return
        e = base_embed(title=page["title"])
        lines = [f"`{cmd}` — {desc}" for cmd, desc in page["commands"]]
        e.description = "\n".join(lines)
        await interaction.response.edit_message(embed=e)


def setup(bot):
    bot.add_cog(Help(bot))
