import discord
from discord.ext import commands, tasks
from discord import SlashCommandGroup, option
from utils.embeds import base_embed, success_embed, error_embed
from datetime import datetime, timedelta


def parse_datetime(s: str) -> datetime | None:
    """Parse JJ/MM/AAAA HH:MM or AAAA-MM-JJ HH:MM"""
    formats = ["%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M", "%d/%m/%Y", "%Y-%m-%d"]
    for fmt in formats:
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    return None


class Planning(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reminder_loop.start()

    def cog_unload(self):
        self.reminder_loop.cancel()

    @tasks.loop(minutes=5)
    async def reminder_loop(self):
        """Vérifie toutes les 5 min les événements à rappeler dans 30 min."""
        try:
            await self.bot.wait_until_ready()
            now = datetime.utcnow()
            soon = now + timedelta(minutes=30)

            for guild in self.bot.guilds:
                cfg = await self.bot.db.get_config(guild.id)
                ch_id = cfg.get("planning_channel")
                if not ch_id:
                    continue
                channel = guild.get_channel(int(ch_id))
                if not channel:
                    continue

                events = await self.bot.db.get_all_events(guild.id)
                for ev in events:
                    try:
                        ev_time = datetime.strptime(ev["scheduled_at"], "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        continue
                    if ev["reminder_sent"]:
                        continue
                    if now < ev_time <= soon:
                        e = base_embed(
                            title="⏰ Rappel — Événement dans 30 minutes !",
                            description=f"**{ev['title']}**\n{ev.get('description', '')}\n\n🕐 <t:{int(ev_time.timestamp())}:F>",
                        )
                        await channel.send(embed=e)
                        await self.bot.db.db.execute(
                            "UPDATE events SET reminder_sent=1 WHERE id=?", (ev["id"],)
                        )
                        await self.bot.db.db.commit()
        except Exception as e:
            print(f"Reminder loop error: {e}")

    planning = SlashCommandGroup("planning", "Gestion du calendrier compétitif")

    @planning.command(name="add", description="Ajouter un événement au calendrier")
    @commands.has_permissions(manage_guild=True)
    @option("title", description="Titre de l'événement")
    @option("date", description="Date et heure — format : JJ/MM/AAAA HH:MM")
    @option("description", description="Description (optionnel)", required=False)
    async def add(self, ctx: discord.ApplicationContext, title: str, date: str, description: str = ""):
        dt = parse_datetime(date)
        if not dt:
            await ctx.respond(
                embed=error_embed("Format de date invalide", "Utilise : `JJ/MM/AAAA HH:MM` ex: `15/06/2025 20:00`"),
                ephemeral=True,
            )
            return
        if dt < datetime.utcnow():
            await ctx.respond(embed=error_embed("Date dans le passé"), ephemeral=True)
            return

        await self.bot.db.create_event(
            ctx.guild_id, title, description, dt.strftime("%Y-%m-%d %H:%M:%S"), ctx.author.id
        )
        e = success_embed(
            "Événement ajouté",
            f"📅 **{title}**\n🕐 <t:{int(dt.timestamp())}:F>\n{description or ''}",
        )
        await ctx.respond(embed=e)

        # Poster dans le salon planning si configuré
        cfg = await self.bot.db.get_config(ctx.guild_id)
        ch_id = cfg.get("planning_channel")
        if ch_id:
            ch = ctx.guild.get_channel(int(ch_id))
            if ch and ch.id != ctx.channel_id:
                ann = base_embed(
                    title=f"📅 Nouvel événement — {title}",
                    description=f"🕐 <t:{int(dt.timestamp())}:F>\n{description or ''}",
                )
                await ch.send(embed=ann)

    @planning.command(name="list", description="Voir les prochains événements")
    async def list_events(self, ctx: discord.ApplicationContext):
        events = await self.bot.db.get_upcoming_events(ctx.guild_id, limit=10)
        if not events:
            await ctx.respond(embed=base_embed("📅 Calendrier", "Aucun événement à venir."))
            return
        lines = []
        for ev in events:
            try:
                dt = datetime.strptime(ev["scheduled_at"], "%Y-%m-%d %H:%M:%S")
                ts = f"<t:{int(dt.timestamp())}:F>"
            except Exception:
                ts = ev["scheduled_at"]
            lines.append(f"**`#{ev['id']}`** {ev['title']}\n└ 🕐 {ts}")
        e = base_embed("📅 Prochains événements", "\n\n".join(lines))
        await ctx.respond(embed=e)

    @planning.command(name="delete", description="Supprimer un événement")
    @commands.has_permissions(manage_guild=True)
    @option("event_id", description="ID de l'événement (voir /planning list)")
    async def delete(self, ctx: discord.ApplicationContext, event_id: int):
        await self.bot.db.delete_event(event_id)
        await ctx.respond(embed=success_embed("Événement supprimé", f"Événement `#{event_id}` retiré."), ephemeral=True)

    @planning.command(name="set_channel", description="Définir le salon du planning")
    @commands.has_permissions(manage_guild=True)
    async def set_channel(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        await self.bot.db.set_config(ctx.guild_id, "planning_channel", channel.id)
        await ctx.respond(embed=success_embed("Salon planning défini", f"→ {channel.mention}"), ephemeral=True)

    @discord.slash_command(name="prochain-match", description="Voir le prochain match prévu")
    async def next_match(self, ctx: discord.ApplicationContext):
        events = await self.bot.db.get_upcoming_events(ctx.guild_id, limit=1)
        if not events:
            await ctx.respond(embed=base_embed("🏎️ Prochain match", "Aucun match prévu pour le moment."))
            return
        ev = events[0]
        try:
            dt = datetime.strptime(ev["scheduled_at"], "%Y-%m-%d %H:%M:%S")
            ts = f"<t:{int(dt.timestamp())}:F>"
            rel = f"<t:{int(dt.timestamp())}:R>"
        except Exception:
            ts = ev["scheduled_at"]
            rel = ""
        e = base_embed(
            title=f"🏎️ Prochain — {ev['title']}",
            description=f"📅 {ts}\n{rel}\n\n{ev.get('description', '')}",
        )
        await ctx.respond(embed=e)

    @discord.slash_command(name="calendrier", description="Calendrier complet des événements")
    async def calendrier(self, ctx: discord.ApplicationContext):
        events = await self.bot.db.get_all_events(ctx.guild_id)
        if not events:
            await ctx.respond(embed=base_embed("📆 Calendrier RLEC", "Aucun événement programmé."))
            return
        lines = []
        for ev in events:
            try:
                dt = datetime.strptime(ev["scheduled_at"], "%Y-%m-%d %H:%M:%S")
                ts = f"<t:{int(dt.timestamp())}:d>"
                past = "~~" if dt < datetime.utcnow() else ""
            except Exception:
                ts = ev["scheduled_at"]
                past = ""
            lines.append(f"• {past}**{ev['title']}**{past} — {ts}")
        e = base_embed("📆 Calendrier RLEC", "\n".join(lines[:20]))
        await ctx.respond(embed=e)


def setup(bot):
    bot.add_cog(Planning(bot))
