import discord
from discord.ext import commands
from discord import SlashCommandGroup
from utils.embeds import base_embed, success_embed, error_embed, RLEC_COLOR
from datetime import datetime

TICKET_TYPES = {
    "support":      ("🛠️", "Support Général",    discord.ButtonStyle.secondary),
    "inscription":  ("📝", "Inscription Tournoi", discord.ButtonStyle.primary),
    "signalement":  ("🚨", "Signalement",         discord.ButtonStyle.danger),
    "reclamation":  ("⚖️", "Réclamation Match",   discord.ButtonStyle.danger),
    "staff":        ("👥", "Demande Staff",        discord.ButtonStyle.success),
    "partenariat":  ("🤝", "Partenariat",         discord.ButtonStyle.secondary),
}


class TicketOpenView(discord.ui.View):
    """Panel d'ouverture de ticket avec un bouton par type."""
    def __init__(self):
        super().__init__(timeout=None)
        for key, (emoji, label, style) in TICKET_TYPES.items():
            self.add_item(TicketButton(key, emoji, label, style))


class TicketButton(discord.ui.Button):
    def __init__(self, key, emoji, label, style):
        super().__init__(label=f"{emoji} {label}", style=style, custom_id=f"ticket_open_{key}")
        self.key = key

    async def callback(self, interaction: discord.Interaction):
        cog: Tickets = interaction.client.cogs.get("Tickets")
        if cog:
            await cog.open_ticket(interaction, self.key)


class TicketActionView(discord.ui.View):
    """Boutons dans le salon ticket ouvert."""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Fermer le ticket", style=discord.ButtonStyle.danger, custom_id="ticket_close")
    async def close_btn(self, button, interaction):
        cog: Tickets = interaction.client.cogs.get("Tickets")
        if cog:
            await cog.close_ticket_channel(interaction)

    @discord.ui.button(label="📋 Transcrire", style=discord.ButtonStyle.secondary, custom_id="ticket_transcript")
    async def transcript_btn(self, button, interaction):
        cog: Tickets = interaction.client.cogs.get("Tickets")
        if cog:
            await cog.transcript_ticket(interaction)


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def open_ticket(self, interaction: discord.Interaction, ticket_type: str):
        guild = interaction.guild
        cfg = await self.bot.db.get_config(guild.id)

        # Vérifier si l'utilisateur a déjà un ticket ouvert
        open_tickets = await self.bot.db.get_open_tickets(guild.id)
        for t in open_tickets:
            if t["user_id"] == interaction.user.id and t["type"] == ticket_type:
                ch = guild.get_channel(t["channel_id"])
                if ch:
                    await interaction.response.send_message(
                        f"❌ Tu as déjà un ticket **{ticket_type}** ouvert : {ch.mention}",
                        ephemeral=True,
                    )
                    return

        emoji, label, _ = TICKET_TYPES[ticket_type]
        ticket_name = f"ticket-{ticket_type}-{interaction.user.name}".lower()[:50]

        # Créer la catégorie si définie
        category = None
        cat_id = cfg.get("ticket_category")
        if cat_id:
            category = guild.get_channel(int(cat_id))

        # Permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(
                read_messages=True, send_messages=True, attach_files=True
            ),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }
        staff_role_id = cfg.get("staff_role")
        if staff_role_id:
            staff_role = guild.get_role(int(staff_role_id))
            if staff_role:
                overwrites[staff_role] = discord.PermissionOverwrite(
                    read_messages=True, send_messages=True, manage_messages=True
                )

        channel = await guild.create_text_channel(
            ticket_name, category=category, overwrites=overwrites,
            topic=f"Ticket {label} de {interaction.user} | {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC"
        )

        await self.bot.db.create_ticket(guild.id, channel.id, interaction.user.id, ticket_type)

        e = base_embed(
            title=f"{emoji}  Ticket — {label}",
            description=(
                f"Bienvenue {interaction.user.mention} !\n\n"
                f"Un membre du staff va te répondre dès que possible.\n"
                f"Décris ton problème / ta demande ci-dessous.\n\n"
                f"**Type :** {label}\n"
                f"**Ouvert le :** <t:{int(datetime.utcnow().timestamp())}:F>"
            ),
        )
        e.set_thumbnail(url=interaction.user.display_avatar.url)

        view = TicketActionView()
        msg = await channel.send(embed=e, view=view)
        await msg.pin()

        await interaction.response.send_message(
            f"✅ Ticket ouvert : {channel.mention}", ephemeral=True
        )

        # Log
        log_id = cfg.get("ticket_log_channel")
        if log_id:
            log_ch = guild.get_channel(int(log_id))
            if log_ch:
                log_e = base_embed(
                    title="🎫 Nouveau Ticket",
                    description=f"**Utilisateur :** {interaction.user.mention}\n**Type :** {label}\n**Salon :** {channel.mention}",
                    color=0x3498db,
                )
                await log_ch.send(embed=log_e)

    async def close_ticket_channel(self, interaction: discord.Interaction):
        ticket = await self.bot.db.get_ticket(interaction.channel_id)
        if not ticket:
            await interaction.response.send_message("❌ Ce n'est pas un ticket.", ephemeral=True)
            return

        cfg = await self.bot.db.get_config(interaction.guild_id)
        staff_role_id = cfg.get("staff_role")
        is_staff = False
        if staff_role_id:
            staff_role = interaction.guild.get_role(int(staff_role_id))
            is_staff = staff_role and staff_role in interaction.user.roles

        if interaction.user.id != ticket["user_id"] and not is_staff and not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ Permission refusée.", ephemeral=True)
            return

        await interaction.response.send_message(
            embed=base_embed("🔒 Fermeture du ticket...", "Le salon sera supprimé dans 5 secondes."),
        )
        await self.bot.db.close_ticket(interaction.channel_id)

        import asyncio
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason=f"Ticket fermé par {interaction.user}")
        except Exception:
            pass

    async def transcript_ticket(self, interaction: discord.Interaction):
        ticket = await self.bot.db.get_ticket(interaction.channel_id)
        if not ticket:
            await interaction.response.send_message("❌ Ce n'est pas un ticket.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        messages = []
        async for msg in interaction.channel.history(limit=200, oldest_first=True):
            if not msg.author.bot:
                ts = msg.created_at.strftime("%Y-%m-%d %H:%M")
                messages.append(f"[{ts}] {msg.author.display_name}: {msg.content}")

        if not messages:
            await interaction.followup.send("Aucun message à transcrire.", ephemeral=True)
            return

        content = "\n".join(messages)
        import io
        file = discord.File(io.BytesIO(content.encode()), filename=f"transcript-{interaction.channel.name}.txt")
        await interaction.followup.send(
            embed=success_embed("Transcription générée", f"{len(messages)} messages exportés."),
            file=file,
            ephemeral=True,
        )

    # ─── Slash Commands ───────────────────────────────────────────────────────
    ticket_cmd = SlashCommandGroup("ticket", "Gestion des tickets")

    @ticket_cmd.command(name="panel", description="Afficher le panel de création de tickets")
    @commands.has_permissions(manage_guild=True)
    async def panel(self, ctx: discord.ApplicationContext):
        e = base_embed(
            title="🎫  Support RLEC",
            description=(
                "Clique sur le bouton correspondant à ta demande pour ouvrir un ticket.\n\n"
                "🛠️ **Support Général** — Questions générales\n"
                "📝 **Inscription Tournoi** — S'inscrire à un tournoi\n"
                "🚨 **Signalement** — Signaler un comportement\n"
                "⚖️ **Réclamation Match** — Contester un résultat\n"
                "👥 **Demande Staff** — Rejoindre l'équipe\n"
                "🤝 **Partenariat** — Proposer un partenariat"
            ),
        )
        view = TicketOpenView()
        await ctx.channel.send(embed=e, view=view)
        await ctx.respond("✅ Panel envoyé !", ephemeral=True)

    @ticket_cmd.command(name="set_category", description="Catégorie pour les tickets")
    @commands.has_permissions(manage_guild=True)
    async def set_category(self, ctx: discord.ApplicationContext, category: discord.CategoryChannel):
        await self.bot.db.set_config(ctx.guild_id, "ticket_category", category.id)
        await ctx.respond(embed=success_embed("Catégorie définie", f"→ **{category.name}**"), ephemeral=True)

    @ticket_cmd.command(name="set_log", description="Salon de logs pour les tickets")
    @commands.has_permissions(manage_guild=True)
    async def set_log(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        await self.bot.db.set_config(ctx.guild_id, "ticket_log_channel", channel.id)
        await ctx.respond(embed=success_embed("Salon de logs défini", f"→ {channel.mention}"), ephemeral=True)

    @ticket_cmd.command(name="list", description="Voir les tickets ouverts")
    @commands.has_permissions(manage_guild=True)
    async def list_tickets(self, ctx: discord.ApplicationContext):
        tickets = await self.bot.db.get_open_tickets(ctx.guild_id)
        if not tickets:
            await ctx.respond(embed=base_embed("🎫 Tickets ouverts", "Aucun ticket en cours."), ephemeral=True)
            return
        lines = []
        for t in tickets:
            ch = ctx.guild.get_channel(t["channel_id"])
            lines.append(f"• {ch.mention if ch else f'#supprimé'} — **{t['type']}** — <@{t['user_id']}>")
        e = base_embed("🎫 Tickets ouverts", "\n".join(lines))
        await ctx.respond(embed=e, ephemeral=True)


def setup(bot):
    bot.add_cog(Tickets(bot))
