import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import sys
from datetime import datetime

# ==============================================================================
# CONFIGURAZIONE RUOLI E TOKEN
# ==============================================================================

NOME_RUOLO_FDO = "FdO"      # 1544460755884187705
NOME_RUOLO_STAFF = "Staff"  # 1544460755892445384

def get_bot_token():
    token = os.getenv("DISCORD_BOT_TOKEN")
    if token and token.strip():
        return token.strip()
    
    config_file = "perm_config.json"
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                if config.get("token") and config.get("token") != "INSERISCI_QUI_IL_TUO_TOKEN":
                    return config["token"].strip()
        except Exception:
            pass

    print("=" * 60)
    print("⚖️ CONFIGURAZIONE BOT PERMAJAIL & PERMADEATH")
    print("=" * 60)
    token = input("👉 Inserisci il Token del tuo Bot di Discord: ").strip()
    
    if not token:
        print("❌ Token non valido. Il programma verrà terminato.")
        sys.exit(1)
        
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump({"token": token}, f, indent=4)
        print("💾 Token salvato in 'perm_config.json'!")
    except Exception as e:
        print(f"⚠️ Impossibile salvare perm_config.json: {e}")
        
    return token

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "database_permanenti.json"

# --- GESTIONE DATABASE PERMANENTI ---
def load_perm_data():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_perm_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Errore salvataggio database registri: {e}")

def registra_condanna(user_id: str, tipo: str, dettagli: dict):
    db = load_perm_data()
    if user_id not in db:
        db[user_id] = {"permajail": None, "permadeath": None}
    
    db[user_id][tipo] = dettagli
    save_perm_data(db)

# --- CONTROLLO ACCESSO: STAFF O FDO ---
def check_is_staff_or_fdo():
    async def predicate(interaction: discord.Interaction) -> bool:
        # Verifica se l'utente possiede il ruolo Staff, FdO o i permessi di Amministratore
        role_fdo = discord.utils.get(interaction.user.roles, name=NOME_RUOLO_FDO)
        role_staff = discord.utils.get(interaction.user.roles, name=NOME_RUOLO_STAFF)
        
        is_admin = interaction.user.guild_permissions.administrator
        has_staff_perm = interaction.user.guild_permissions.manage_messages
        
        if role_fdo or role_staff or is_admin or has_staff_perm:
            return True
        
        await interaction.response.send_message(
            f"❌ **Accesso Negato:** Questo comando è riservato allo **Staff** e alle **{NOME_RUOLO_FDO}**.",
            ephemeral=True
        )
        return False
    return app_commands.check(predicate)

# ==============================================================================
# COMANDI SLASH PERMANENTI
# ==============================================================================

# --- 1. COMANDO PERMAJAIL ---
@bot.tree.command(name="permajail", description="Esegui una condanna a vita (Permajail / Ergastolo) per un personaggio.")
@app_commands.describe(
    utente="Il cittadino condannato al Permajail",
    motivo="Motivazione penale grave, capo di imputazione o sentenza giudiziaria"
)
@check_is_staff_or_fdo()
async def permajail(interaction: discord.Interaction, utente: discord.User, motivo: str):
    dettagli = {
        "esecutore_id": interaction.user.id,
        "esecutore_nome": interaction.user.display_name,
        "motivo": motivo,
        "data": datetime.now().strftime("%d/%m/%Y - %H:%M")
    }

    registra_condanna(str(utente.id), "permajail", dettagli)

    embed = discord.Embed(
        title="🏛️ SENTENZA DI PERMAJAIL (ERGASTOLO)",
        description="**Il soggetto è stato condannato alla detenzione a vita in un penitenziario di massima sicurezza.**",
        color=discord.Color.dark_red(),
        timestamp=datetime.now()
    )
    embed.set_thumbnail(url=utente.display_avatar.url)
    embed.set_author(name=f"Autorità Esecutrice: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
    embed.add_field(name="Condannato", value=f"{utente.mention} (`{utente.display_name}`)", inline=False)
    embed.add_field(name="Capi d'Imputazione / Motivo", value=f"```\n{motivo}\n```", inline=False)
    embed.set_footer(text="Corte Suprema & Dipartimento di Giustizia • Sentenza Inappellabile")

    await interaction.response.send_message(content=f"⛔ **PERMAJAIL CONFERMATO PER {utente.mention}**", embed=embed)


# --- 2. COMANDO PERMADEATH ---
@bot.tree.command(name="permadeath", description="Registra la morte permanente (Permadeath / Wipe) di un personaggio.")
@app_commands.describe(
    utente="Il cittadino/personaggio deceduto definitivamente",
    motivo="Causa della morte IC o motivazione approvata dal regolamento"
)
@check_is_staff_or_fdo()
async def permadeath(interaction: discord.Interaction, utente: discord.User, motivo: str):
    dettagli = {
        "esecutore_id": interaction.user.id,
        "esecutore_nome": interaction.user.display_name,
        "motivo": motivo,
        "data": datetime.now().strftime("%d/%m/%Y - %H:%M")
    }

    registra_condanna(str(utente.id), "permadeath", dettagli)

    embed = discord.Embed(
        title="☠️ REGISTRO DECESSO PERMANENTE (PERMADEATH)",
        description="**Questo personaggio è stato dichiarato ufficialmente deceduto IC. La sua storia termina qui.**",
        color=discord.Color.from_rgb(20, 20, 20),
        timestamp=datetime.now()
    )
    embed.set_thumbnail(url=utente.display_avatar.url)
    embed.set_author(name=f"Ufficiale/Staffer: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
    embed.add_field(name="Personaggio Deceduto", value=f"{utente.mention} (`{utente.display_name}`)", inline=False)
    embed.add_field(name="Causa del Decesso", value=f"```\n{motivo}\n```", inline=False)
    embed.set_footer(text="Registro di Stato Civile • Personaggio Archiviato")

    await interaction.response.send_message(content=f"💀 **PERMADEATH CONVALIDATO PER {utente.mention}**", embed=embed)


# --- 3. COMANDO CONTROLLO STATO ---
@bot.tree.command(name="stato_personaggio", description="Verifica se un utente ha un Permajail o Permadeath attivo.")
@app_commands.describe(utente="L'utente da controllare")
@check_is_staff_or_fdo()
async def stato_personaggio(interaction: discord.Interaction, utente: discord.User):
    db = load_perm_data()
    user_id = str(utente.id)

    if user_id not in db or (not db[user_id]["permajail"] and not db[user_id]["permadeath"]):
        await interaction.response.send_message(f"✅ Il personaggio di **{utente.display_name}** non ha condanne permanenti attive.", ephemeral=True)
        return

    record = db[user_id]
    embed = discord.Embed(
        title=f"📋 Stato Giudiziario - {utente.display_name}",
        color=discord.Color.dark_grey(),
        timestamp=datetime.now()
    )
    embed.set_thumbnail(url=utente.display_avatar.url)

    if record["permajail"]:
        pj = record["permajail"]
        embed.add_field(
            name="⛔ PERMAJAIL ATTIVO",
            value=f"**Motivo:** {pj['motivo']}\n**Data:** {pj['data']}\n**Eseguito da:** {pj['esecutore_nome']}",
            inline=False
        )

    if record["permadeath"]:
        pd = record["permadeath"]
        embed.add_field(
            name="☠️ PERMADEATH ATTIVO",
            value=f"**Causa:** {pd['motivo']}\n**Data:** {pd['data']}\n**Eseguito da:** {pd['esecutore_nome']}",
            inline=False
        )

    await interaction.response.send_message(embed=embed)

# ==============================================================================
# EVENTI E AVVIO
# ==============================================================================

@bot.event
async def on_ready():
    print("--------------------------------------------------")
    print(f"⚖️ Bot Permajail/Permadeath Online come: {bot.user.name} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"🔄 Sincronizzati {len(synced)} comandi Slash con successo!")
    except Exception as e:
        print(f"❌ Errore durante la sincronizzazione: {e}")
    print("--------------------------------------------------")

if __name__ == "__main__":
    token = get_bot_token()
    try:
        bot.run(token)
    except discord.errors.LoginFailure:
        print("❌ Token inserito non valido! Elimina 'perm_config.json' e riavvia il bot.")
