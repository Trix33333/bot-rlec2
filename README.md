# 🏎️ RLEC Bot — Rocket League Esport Championship

Bot Discord complet pour gérer un championnat Rocket League.

---

## 📦 Installation

### 1. Prérequis
- Python 3.10 ou supérieur
- Un bot Discord créé sur le [Developer Portal](https://discord.com/developers/applications)

### 2. Cloner / télécharger le projet
```bash
# Placer tous les fichiers dans un dossier rlec/
cd rlec
```

### 3. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 4. Configurer le token
Dans `bot.py`, remplace :
```python
TOKEN = os.getenv("DISCORD_TOKEN", "VOTRE_TOKEN_ICI")
```
Par ton token, **ou** utilise une variable d'environnement :
```bash
# Linux / Mac
export DISCORD_TOKEN="ton_token_ici"

# Windows
set DISCORD_TOKEN=ton_token_ici
```

### 5. Lancer le bot
```bash
python bot.py
```

---

## ⚙️ Configuration initiale sur Discord

Une fois le bot en ligne, utilise `/setup` dans ton serveur pour voir toutes les commandes de configuration, puis :

| Commande | Description |
|---|---|
| `/config staff_role @Role` | Définir le rôle staff |
| `/welcome set_channel #salon` | Salon de bienvenue |
| `/welcome set_role @Role` | Rôle attribué à l'arrivée |
| `/ticket set_category` | Catégorie pour les tickets |
| `/ticket panel` | Afficher le panel de tickets |
| `/annonce set_channel #salon` | Salon d'annonces |
| `/planning set_channel #salon` | Salon du calendrier |
| `/config show` | Voir la config complète |

---

## 🏆 Lancer un tournoi

```
1. /bracket create name:"RLEC Saison 1" type:single
2. /bracket start equipes:"Équipe A, Équipe B, Équipe C, Équipe D"
3. /bracket show                          → voir le bracket
4. /bracket result match_id:1 score1:3 score2:1
5. /bracket close                         → fin du tournoi
```

---

## 📁 Structure des fichiers

```
rlec/
├── bot.py                  # Point d'entrée principal
├── requirements.txt
├── data/
│   └── rlec.db             # Base SQLite (créée automatiquement)
├── utils/
│   ├── database.py         # Toutes les requêtes SQLite
│   └── embeds.py           # Helpers pour les embeds Discord
└── cogs/
    ├── welcome.py          # Système de bienvenue
    ├── tickets.py          # Système de tickets
    ├── teams.py            # Gestion des équipes
    ├── brackets.py         # Tournois & brackets
    ├── planning.py         # Calendrier & événements
    ├── stats.py            # Statistiques joueurs
    ├── announcements.py    # Annonces officielles
    ├── admin.py            # Panneau administrateur
    └── help.py             # Aide interactive
```

---

## 🔐 Permissions Discord requises

Le bot a besoin des permissions suivantes :
- `Manage Channels` — création des salons tickets
- `Manage Roles` — attribution des rôles bienvenue
- `Send Messages` / `Embed Links` / `Attach Files`
- `Read Message History` — transcriptions tickets
- `Mention Everyone` — pings d'annonces (optionnel)

**Intents requis (Developer Portal) :**
- `Server Members Intent` ✅
- `Message Content Intent` ✅

---

## 🎨 Identité visuelle

Couleur principale : `#e2231a` (rouge RLEC)

Pour personnaliser les embeds, modifie `RLEC_COLOR` dans `utils/embeds.py`.

---

## 📞 Commandes complètes

Utilise `/help` sur Discord pour la liste complète, ou `/help staff` pour les commandes réservées au staff.
