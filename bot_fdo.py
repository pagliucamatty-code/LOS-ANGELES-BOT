import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import sys
from datetime import datetime

# ==============================================================================
# CONFIGURAZIONE & GESTIONE TOKEN / RUOLO FDO
# ==============================================================================

NOME_RUOLO_FDO = "FdO"  # Modifica con il nome esatto del ruolo nel tuo server (es. "Polizia")

def get_bot_token():
    token = os.getenv("DISCORD_BOT_TOKEN")
    if token and token.strip():
        return token.strip()
    
    config_file = "fdo_config.json"
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                if config.get("token") and config.get("token") != "INSERISCI_QUI_IL_TUO_TOKEN":
                    return config["token"].strip()
        except Exception:
            pass

    print("=" * 60)
    print("🚓 CONFIGURAZIONE BOT FORZE DELL'ORDINE")
    print("=" * 60)
    token = input("👉 Inserisci il Token del tuo Bot di Discord: ").strip()
    
    if not token:
        print("❌ Token non valido. Il programma verrà terminato.")
        sys.exit(1)
        
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump({"token": token}, f, indent=4)
        print("💾 Token salvato in 'fdo_config.json'!")
    except Exception as e:
        print(f"⚠️ Impossibile salvare fdo_config.json: {e}")
        
    return token

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "database_fdo.json"

# --- GESTIONE DATABASE FDO ---
def load_fdo_data():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_fdo_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Errore salvataggio database FdO: {e}")

def registra_sanzione(user_id: str, tipo: str, dettagli: dict):
    db = load_fdo_data()
    if user_id not in db:
        db[user_id] = {
            "multe": [], 
            "arresti": [], 
            "revoche": []
        }
    
    if tipo == "revoche":
        db[user_id]["revoche"].append(dettagli)
    else:
        db[user_id][tipo].append(dettagli)
        
    save_fdo_data(db)

# --- CONTROLLO ACCESSO RUOLO FDO ---
def check_is_fdo():
    async def predicate(interaction: discord.Interaction) -> bool:
        role = discord.utils.get(interaction.user.roles, name=NOME_RUOLO_FDO)
        if role is not None or interaction.user.guild_permissions.administrator:
            return True
        
        await interaction.response.send_message(
            f"❌ **Accesso Negato:** Solo il personale con il ruolo **{NOME_RUOLO_FDO}** può eseguire questo comando.",
            ephemeral=True
        )
        return False
    return app_commands.check(predicate)

# ==============================================================================
# COMANDI SLASH FDO
# ==============================================================================

# --- 1. COMANDO MULTA (CON DECURTAZIONE PUNTI) ---
@bot.tree.command(name="multa", description="Emetti una multa e decurta facoltativamente punti dalla patente.")
@app_commands.describe(
    utente="Il cittadino da sanzionare",
    importo="Importo della sanzione (es. 500)",
    motivo="Motivazione della multa",
    punti_decurtati="Punti da togliere dalla patente (Opzionale)"
)
@check_is_fdo()
async def multa(interaction: discord.Interaction, utente: discord.User, importo: int, motivo: str, punti_decurtati: int = 0):
    if importo <= 0:
        await interaction.response.send_message("⚠️ L'importo della multa deve essere maggiore di zero.", ephemeral=True)
        return
    
    if punti_decurtati < 0:
        await interaction.response.send_message("⚠️ I punti decurtati non possono essere negativi.", ephemeral=True)
        return

    dettagli = {
        "agente_id": interaction.user.id,
        "agente_nome": interaction.user.display_name,
        "importo": importo,
        "motivo": motivo,
        "punti_decurtati": punti_decurtati,
        "data": datetime.now().strftime("%d/%m/%Y - %H:%M")
    }
    
    registra_sanzione(str(utente.id), "multe", dettagli)

    embed = discord.Embed(
        title="📑 VERBALE DI SANZIONE AMMINISTRATIVA",
        color=discord.Color.gold(),
        timestamp=datetime.now()
    )
    embed.set_author(name=f"Agente: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
    embed.add_field(name="Cittadino Sanzionato", value=f"{utente.mention} (`{utente.display_name}`)", inline=False)
    embed.add_field(name="Importo Sanzione", value=f"```yaml\n$ {importo:,}\n```", inline=True)
    
    if punti_decurtati > 0:
        embed.add_field(name="Punti Decurtati", value=f"```diff\n- {punti_decurtati} Punti\n```", inline=True)
        
    embed.add_field(name="Motivazione", value=f"```\n{motivo}\n```", inline=False)
    embed.set_footer(text="Dipartimento di Polizia • Verbale Ufficiale")

    await interaction.response.send_message(content=f"🚨 {utente.mention}, ti è stata emessa una multa!", embed=embed)


# --- 2. COMANDO REVOCA PATENTE ---
@bot.tree.command(name="revoca_patente", description="Revoca ufficialmente la patente di guida a un cittadino.")
@app_commands.describe(
    utente="Il cittadino a cui revocare la patente",
    motivo="Motivazione della revoca (es. Guida pericolosa, 0 punti rimasti)"
)
@check_is_fdo()
async def revoca_patente(interaction: discord.Interaction, utente: discord.User, motivo: str):
    dettagli = {
        "agente_id": interaction.user.id,
        "agente_nome": interaction.user.display_name,
        "tipo_documento": "Patente di Guida",
        "motivo": motivo,
        "data": datetime.now().strftime("%d/%m/%Y - %H:%M")
    }

    registra_sanzione(str(utente.id), "revoche", dettagli)

    embed = discord.Embed(
        title="🚫 REVOCA PATENTE DI GUIDA",
        color=discord.Color.red(),
        timestamp=datetime.now()
    )
    embed.set_author(name=f"Agente Operante: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
    embed.add_field(name="Cittadino", value=f"{utente.mention} (`{utente.display_name}`)", inline=False)
    embed.add_field(name="Provvedimento", value="```yaml\nREVOCA IMMEDIATA PATENTE\n```", inline=True)
    embed.add_field(name="Motivazione", value=f"```\n{motivo}\n```", inline=False)
    embed.set_footer(text="Dipartimento Trasporti & Motorizzazione / FdO")

    await interaction.response.send_message(content=f"⚠️ {utente.mention}, la tua **Patente di Guida** è stata revocata!", embed=embed)


# --- 3. COMANDO REVOCA PORTO D'ARMI ---
@bot.tree.command(name="revoca_porto_darmi", description="Revoca ufficialmente il porto d'armi a un cittadino.")
@app_commands.describe(
    utente="Il cittadino a cui revocare il porto d'armi",
    motivo="Motivazione della revoca (es. Uso improprio, reato grave)"
)
@check_is_fdo()
async def revoca_porto_darmi(interaction: discord.Interaction, utente: discord.User, motivo: str):
    dettagli = {
        "agente_id": interaction.user.id,
        "agente_nome": interaction.user.display_name,
        "tipo_documento": "Porto d'Armi",
        "motivo": motivo,
        "data": datetime.now().strftime("%d/%m/%Y - %H:%M")
    }

    registra_sanzione(str(utente.id), "revoche", dettagli)

    embed = discord.Embed(
        title="🛑 REVOCA PORTO D'ARMI",
        color=discord.Color.dark_red(),
        timestamp=datetime.now()
    )
    embed.set_author(name=f"Agente Operante: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
    embed.add_field(name="Cittadino", value=f"{utente.mention} (`{utente.display_name}`)", inline=False)
    embed.add_field(name="Provvedimento", value="```yaml\nREVOCA E SEQUESTRO LICENZA ARMI\n```", inline=True)
    embed.add_field(name="Motivazione", value=f"```\n{motivo}\n```", inline=False)
    embed.set_footer(text="Dipartimento di Pubblica Sicurezza / FdO")

    await interaction.response.send_message(content=f"⚠️ {utente.mention}, il tuo **Porto d'Armi** è stato revocato!", embed=embed)


# --- 4. COMANDO ARRESTO TEMPORANEO ---
@bot.tree.command(name="arresto", description="Registra l'arresto temporaneo di un cittadino.")
@app_commands.describe(
    utente="Il cittadino da arrestare",
    mesi="Mesi/Minuti di carcere (es. 20)",
    capi_imputazione="Reati commessi dal cittadino"
)
@check_is_fdo()
async def arresto(interaction: discord.Interaction, utente: discord.User, mesi: int, capi_imputazione: str):
    if mesi <= 0:
        await interaction.response.send_message("⚠️ La durata della pena deve essere maggiore di zero.", ephemeral=True)
        return

    dettagli = {
        "agente_id": interaction.user.id,
        "agente_nome": interaction.user.display_name,
        "durata_mesi": mesi,
        "reati": capi_imputazione,
        "data": datetime.now().strftime("%d/%m/%Y - %H:%M")
    }

    registra_sanzione(str(utente.id), "arresti", dettagli)

    embed = discord.Embed(
        title="🚔 MANDATO DI ARRESTO E DETENZIONE",
        color=discord.Color.orange(),
        timestamp=datetime.now()
    )
    embed.set_author(name=f"Agente Operante: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
    embed.add_field(name="Detenuto", value=f"{utente.mention} (`{utente.display_name}`)", inline=False)
    embed.add_field(name="Pena Detentiva", value=f"```yaml\n{mesi} Mesi/Minuti\n```", inline=True)
    embed.add_field(name="Capi di Imputazione", value=f"```\n{capi_imputazione}\n```", inline=False)
    embed.set_footer(text="Dipartimento di Giustizia • Struttura Penitenziaria")

    await interaction.response.send_message(content=f"🔒 {utente.mention} è stato tratto in arresto!", embed=embed)


# --- 5. COMANDO FEDINA PENALE ---
@bot.tree.command(name="fedina_penale", description="Visualizza lo storico sanzioni, arresti e revoche di un cittadino.")
@app_commands.describe(utente="Il cittadino da controllare")
@check_is_fdo()
async def fedina_penale(interaction: discord.Interaction, utente: discord.User):
    db = load_fdo_data()
    user_id = str(utente.id)

    if user_id not in db or (not db[user_id]["multe"] and not db[user_id]["arresti"] and not db[user_id].get("revoche")):
        await interaction.response.send_message(f"✅ La fedina penale di **{utente.display_name}** è pulita.", ephemeral=True)
        return

    record = db[user_id]
    embed = discord.Embed(
        title=f"📋 Fedina Penale - {utente.display_name}",
        color=discord.Color.red(),
        timestamp=datetime.now()
    )
    embed.set_thumbnail(url=utente.display_avatar.url)

    # Storico Revoche Documenti
    if record.get("revoche"):
        revoche_txt = ""
        for i, r in enumerate(record["revoche"][-5:], 1):
            revoche_txt += f"**{i}.** Documento: `{r['tipo_documento']}` | Motivo: `{r['motivo']}` ({r['data']})\n"
        embed.add_field(name="🚫 Documenti Revocati", value=revoche_txt, inline=False)

    # Storico Arresti
    if record.get("arresti"):
        arresti_txt = ""
        for i, arr in enumerate(record["arresti"][-5:], 1):
            arresti_txt += f"**{i}.** Durata: `{arr['durata_mesi']} Mesi` | Reato: `{arr['reati']}` ({arr['data']})\n"
        embed.add_field(name="🚔 Ultimi Arresti", value=arresti_txt, inline=False)

    # Storico Multe
    if record.get("multe"):
        multe_txt = ""
        for i, m in enumerate(record["multe"][-5:], 1):
            punti = f" ( -{m['punti_decurtati']} PT )" if m.get("punti_decurtati", 0) > 0 else ""
            multe_txt += f"**{i}.** Importo: `$ {m['importo']}`{punti} | Motivo: `{m['motivo']}` ({m['data']})\n"
        embed.add_field(name="📑 Ultime Multe", value=multe_txt, inline=False)

    await interaction.response.send_message(embed=embed)

# ==============================================================================
# EVENTI E AVVIO
# ==============================================================================

@bot.event
async def on_ready():
    print("--------------------------------------------------")
    print(f"🚓 Bot FdO Online come: {bot.user.name} (ID: {bot.user.id})")
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
        print("❌ Token inserito non valido! Elimina 'fdo_config.json' e riavvia il bot.")
