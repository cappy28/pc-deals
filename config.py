# ==========================================================
#  CONFIGURATION — le seul fichier que tu dois modifier
# ==========================================================

INTERVALLE_MINUTES = 30   # temps entre deux collectes (ne descends pas sous 15)

# --- Notifications Telegram (optionnel : laisse vide pour désactiver)
TELEGRAM_TOKEN = ""
TELEGRAM_CHAT_ID = ""

# --- Mots qui éliminent une annonce, quelle que soit la source
EXCLUSIONS_GLOBALES = [
    "cherche", "hs", "pour pieces", "en panne", "defectueux", "ne fonctionne",
    "boite vide", "pc gamer", "pc complet", "unite centrale", "portable", "laptop",
]

# --- Composants surveillés
#  mots     : TOUS doivent être présents dans le titre (espaces ignorés : "7800xt" = "7800 XT")
#  exclure  : si UN est présent, l'annonce est ignorée
#  prix_max : en dessous = bonne affaire 🔥  (valeurs d'exemple : ajuste-les !)
#  recherche: texte tapé dans Leboncoin (sinon le nom est utilisé)
WATCHLIST = [
    {"nom": "RX 9070 XT", "type": "GPU", "mots": ["9070xt"], "exclure": [], "prix_max": 550, "recherche": "rx 9070 xt"},
    {"nom": "RTX 5070", "type": "GPU", "mots": ["5070"], "exclure": ["ti", "5070ti"], "prix_max": 480, "recherche": "rtx 5070"},
    {"nom": "RTX 4070 Super", "type": "GPU", "mots": ["4070", "super"], "exclure": ["ti", "4070ti"], "prix_max": 420, "recherche": "rtx 4070 super"},
    {"nom": "Ryzen 7 9800X3D", "type": "CPU", "mots": ["9800x3d"], "exclure": [], "prix_max": 400},
    {"nom": "Ryzen 7 7800X3D", "type": "CPU", "mots": ["7800x3d"], "exclure": [], "prix_max": 280},
    {"nom": "Ryzen 5 7600", "type": "CPU", "mots": ["7600"], "exclure": ["rx", "rx7600", "xt", "7600xt", "i5"], "prix_max": 140, "recherche": "ryzen 5 7600"},
    {"nom": "Carte mère B650", "type": "Carte mère", "mots": ["b650"], "exclure": [], "prix_max": 120},
    {"nom": "DDR5 32 Go", "type": "RAM", "mots": ["ddr5", "32go"], "exclure": ["sodimm", "so dimm"], "prix_max": 110, "recherche": "ddr5 32go"},
    {"nom": "SSD NVMe 2 To", "type": "SSD", "mots": ["nvme", "2to"], "exclure": [], "prix_max": 120, "recherche": "ssd nvme 2to"},
    {"nom": "Alim 850W Gold", "type": "Alimentation", "mots": ["850w", "gold"], "exclure": [], "prix_max": 90, "recherche": "alimentation 850w gold"},
]

# --- Ta config cible (noms pris dans la WATCHLIST) : le site calcule le total
MA_CONFIG = ["Ryzen 7 7800X3D", "Carte mère B650", "DDR5 32 Go", "RX 9070 XT", "SSD NVMe 2 To", "Alim 850W Gold"]
