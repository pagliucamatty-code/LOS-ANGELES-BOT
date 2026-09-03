import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import sys
from datetime import datetime

# ==============================================================================
# CONFIGURAZIONE TOKEN E BOT
# ==============================================================================

# ⚠️ INSERISCI IL TUO TOKEN DISCORD TRA LE VIRGOLETTE QUI SOTTO:
TOKEN = "MTUzODY1MDg3NjE2NjgwNzU5Mg.GC10Vi.wVRNwLHkRfkPlNby3U07dgUF3yD3smGL6F__1A"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "database_documenti.json"

# ==============================================================================
# GESTIONE DATABASE LOCALE (DOCUMENTI)
# ==============================================================================

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Errore salvataggio database: {e}")

# ==============================================================================
# MODAL INTERATTIVI PER CREAZIONE DOCUMENTI
# ==============================================================================

class CittadinanzaModal(discord.ui.Modal, title="Richiesta Cittadinanza"):
    nome_cognome = discord.ui.TextInput(label="Nome e Cognome IC", placeholder="es. Mario Rossi", required=True, max_length=100)
    data_nascita = discord.ui.TextInput(label="Data di Nascita (GG/MM/AAAA)", placeholder="es. 15/05/1990", required=True, max_length=10)
    luogo_nascita = discord.ui.TextInput(label="Luogo di Nascita", placeholder="es. Los Santos", required=True, max_length=50)
    sesso = discord.ui.TextInput(label="Sesso (M/F/Altro)", placeholder="M o F", required=True, max_length=10)

    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        db = load_data()
        if user_id not in db:
            db[user_id] = {}
            
        db[user_id]["cittadinanza"] = {
            "nome_cognome": self.nome_cognome.value,
            "data_nascita": self.data_nascita.value,
            "luogo_nascita": self.luogo_nascita.value,
            "sesso": self.sesso.value,
            "data_emissione": datetime.now().strftime("%d/%m/%Y")
        }
        save_data(db)

        embed = discord.Embed(title="🪪 CARTA DI CITTADINANZA EMESSA", color=discord.Color.blue(), timestamp=datetime.now())
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="Nome & Cognome", value=f"```\n{self.nome_cognome.value}\n```", inline=True)
        embed.add_field(name="Data di Nascita", value=f"```\n{self.data_nascita.value}\n```", inline=True)
        embed.add_field(name="Luogo di Nascita", value=f"```\n{self.luogo_nascita.value}\n```", inline=True)
        embed.add_field(name="Sesso", value=f"```\n{self.sesso.value}\n```", inline=True)
        embed.set_footer(text="Repubblica Roleplay • Documento Ufficiale")
        
        await interaction.response.send_message(content="✅ **Cittadinanza registrata con successo!**", embed=embed)


class PatenteModal(discord.ui.Modal, title="Emissione Patente di Guida"):
    categorie = discord.ui.TextInput(label="Categorie Abilitate", placeholder="es. A, B", default="A, B", required=True)
    punti = discord.ui.TextInput(label="Punti Iniziali", placeholder="20", default="20", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        db = load_data()
        
        if user_id not in db or "cittadinanza" not in db[user_id]:
            await interaction.response.send_message("⚠️ Registra prima la Cittadinanza usando `/cittadinanza`.", ephemeral=True)
            return

        db[user_id]["patente"] = {
            "categorie": self.categorie.value,
            "punti": self.punti.value,
            "stato": "VALIDA",
            "data_emissione": datetime.now().strftime("%d/%m/%Y")
        }
        save_data(db)

        embed = discord.Embed(title="🚗 PATENTE DI GUIDA EMESSA", color=discord.Color.green(), timestamp=datetime.now())
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="Titolare", value=f"```\n{db[user_id]['cittadinanza']['nome_cognome']}\n```", inline=False)
        embed.add_field(name="Categorie", value=f"```\n{self.categorie.value}\n```", inline=True)
        embed.add_field(name="Punti", value=f"```\n{self.punti.value} PT\n```", inline=True)
        embed.set_footer(text="Dipartimento Trasporti e Motorizzazione")
        
        await interaction.response.send_message(content="✅ **Patente registrata con successo!**", embed=embed)


class PortoDarmiModal(discord.ui.Modal, title="Richiesta Porto d'Armi"):
    tipo_licenza = discord.ui.TextInput(label="Tipo Licenza", placeholder="es. Difesa Personale", default="Difesa Personale", required=True)
    armi_consentite = discord.ui.TextInput(label="Armi Consentite", placeholder="es. Pistole 9mm", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        db = load_data()
        
        if user_id not in db or "cittadinanza" not in db[user_id]:
            await interaction.response.send_message("⚠️ Registra prima la Cittadinanza usando `/cittadinanza`.", ephemeral=True)
            return

        db[user_id]["porto_darmi"] = {
            "tipo": self.tipo_licenza.value,
            "armi": self.armi_consentite.value,
            "stato": "ATTIVO",
            "data_emissione": datetime.now().strftime("%d/%m/%Y")
        }
        save_data(db)

        embed = discord.Embed(title="🔫 PORTO D'ARMI UFFICIALE", color=discord.Color.red(), timestamp=datetime.now())
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="Intestatario", value=f"```\n{db[user_id]['cittadinanza']['nome_cognome']}\n```", inline=False)
        embed.add_field(name="Tipo Licenza", value=f"```\n{self.tipo_licenza.value}\n```", inline=True)
        embed.add_field(name="Armi Autorizzate", value=f"```\n{self.armi_consentite.value}\n```", inline=False)
        embed.set_footer(text="Dipartimento di Pubblica Sicurezza")
        
        await interaction.response.send_message(content="✅ **Porto d'armi registrato con successo!**", embed=embed)

# ==============================================================================
# COMANDI SLASH (DOCUMENTI)
# ==============================================================================

@bot.tree.command(name="cittadinanza", description="Richiedi e compila la tua Carta di Cittadinanza IC.")
async def cittadinanza(interaction: discord.Interaction):
    await interaction.response.send_modal(CittadinanzaModal())

@bot.tree.command(name="patente", description="Richiedi e registra la tua Patente di Guida.")
async def patente(interaction: discord.Interaction):
    await interaction.response.send_modal(PatenteModal())

@bot.tree.command(name="porto_darmi", description="Richiedi la Licenza di Porto d'Armi.")
async def porto_darmi(interaction: discord.Interaction):
    await interaction.response.send_modal(PortoDarmiModal())

@bot.tree.command(name="documenti", description="Mostra il portafoglio con tutti i tuoi documenti o quelli di un altro utente.")
@app_commands.describe(utente="L'utente di cui vuoi verificare i documenti (Opzionale)")
async def documenti(interaction: discord.Interaction, utente: discord.User = None):
    target = utente or interaction.user
    user_id = str(target.id)
    db = load_data()

    if user_id not in db or not db[user_id]:
        await interaction.response.send_message(f"❌ Nessun documento registrato trovato per **{target.display_name}**.", ephemeral=True)
        return

    user_docs = db[user_id]
    embed = discord.Embed(title=f"🗂️ Portafoglio Documenti - {target.display_name}", color=discord.Color.gold(), timestamp=datetime.now())
    embed.set_thumbnail(url=target.display_avatar.url)

    if "cittadinanza" in user_docs:
        c = user_docs["cittadinanza"]
        embed.add_field(name="🪪 Cittadinanza", value=f"**Nome:** {c['nome_cognome']}\n**Data Nascita:** {c['data_nascita']}\n**Luogo:** {c['luogo_nascita']}\n**Sesso:** {c['sesso']}", inline=False)

    if "patente" in user_docs:
        p = user_docs["patente"]
        embed.add_field(name="🚗 Patente di Guida", value=f"**Categorie:** {p['categorie']}\n**Punti:** {p['punti']} PT\n**Stato:** {p['stato']}", inline=False)

    if "porto_darmi" in user_docs:
        pa = user_docs["porto_darmi"]
        embed.add_field(name="🔫 Porto d'Armi", value=f"**Tipo:** {pa['tipo']}\n**Armi:** {pa['armi']}\n**Stato:** {pa['stato']}", inline=False)

    embed.set_footer(text="Sistema Gestione Documentale Ufficiale")
    await interaction.response.send_message(embed=embed)

# ==============================================================================
# EVENTI DI AVVIO
# ==============================================================================

@bot.event
async def on_ready():
    print("--------------------------------------------------")
    print(f"🤖 Bot Documenti Online come: {bot.user.name} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"🔄 Sincronizzati {len(synced)} comandi Slash con successo!")
    except Exception as e:
        print(f"❌ Errore sincronizzazione comandi: {e}")
    print("--------------------------------------------------")

if __name__ == "__main__":
    if TOKEN == "INSERISCI_QUI_IL_TUO_TOKEN" or not TOKEN.strip():
        print("❌ ERRORE: Non hai inserito il Token del bot!")
        print("👉 Apri il file 'main.py' e incolla il tuo Token alla riga 14 nella variabile TOKEN.")
        sys.exit(1)
        
    try:
        bot.run(TOKEN.strip())
    except discord.errors.LoginFailure:
        print("❌ Token non valido! Controlla di aver copiato correttamente il token dal Developer Portal di Discord.")
