import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import sys
import asyncio
from datetime import datetime

# ==============================================================================
# CONFIGURAZIONE & GESTIONE TOKEN
# ==============================================================================

def get_bot_token():
    token = os.getenv("DISCORD_BOT_TOKEN")
    if token and token.strip():
        return token.strip()
    
    config_file = "ticket_config.json"
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                if config.get("token") and config.get("token") != "INSERISCI_QUI_IL_TUO_TOKEN":
                    return config["token"].strip()
        except Exception:
            pass

    print("=" * 60)
    print("🤖 CONFIGURAZIONE BOT TICKET DISCORD")
    print("=" * 60)
    token = input("👉 Inserisci il Token del tuo Bot di Discord: ").strip()
    
    if not token:
        print("❌ Token non valido. Il programma verrà terminato.")
        sys.exit(1)
        
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump({"token": token}, f, indent=4)
        print("💾 Token salvato in 'ticket_config.json'!")
    except Exception as e:
        print(f"⚠️ Impossibile salvare ticket_config.json: {e}")
        
    return token

# Configurazione Bot con Intents moderni
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ==============================================================================
# INTERFACCIA INTERATTIVA TICKET (BOTTONI INTERNI AL CANALE)
# ==============================================================================

class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # Timeout None per bottoni persistenti dopo i riavvii

    # --- BOTTONE RECLAMA TICKET (SOLO STAFF) ---
    @discord.ui.button(
        label="✋ Reclama Ticket", 
        style=discord.ButtonStyle.success, 
        custom_id="claim_ticket_btn"
    )
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Controllo Permessi: solo chi ha i permessi di Gestire i Canali (Staff/Admin) può reclamare
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message(
                "❌ **Solo i membri dello Staff possono reclamare questo ticket!**", 
                ephemeral=True
            )
            return

        # Disabilita il bottone Reclama per evitare che venga cliccato più volte
        button.disabled = True
        button.label = f"Reclamato da {interaction.user.display_name}"
        
        # Aggiorna la vista del messaggio
        await interaction.message.edit(view=self)

        # Modifica i permessi del canale: assegna la gestione diretta allo Staffer
        channel = interaction.channel
        await channel.set_permissions(interaction.user, read_messages=True, send_messages=True, manage_channels=True)

        embed = discord.Embed(
            title="👮 Ticket Reclamato",
            description=f"Questo ticket è stato preso in carico da {interaction.user.mention}.",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        await interaction.response.send_message(embed=embed)

    # --- BOTTONE CHIUDI TICKET ---
    @discord.ui.button(
        label="🔒 Chiudi Ticket", 
        style=discord.ButtonStyle.danger, 
        custom_id="close_ticket_btn"
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 **Il ticket verrà chiuso ed eliminato tra 5 secondi...**")
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete()
        except discord.NotFound:
            pass

# ==============================================================================
# INTERFACCIA PANNELLO APERTURA TICKET
# ==============================================================================

class TicketLaunchView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="📩 Apri Ticket", 
        style=discord.ButtonStyle.primary, 
        custom_id="open_ticket_btn"
    )
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        # Genera nome univoco pulito per il canale
        clean_username = "".join(c for c in user.name.lower() if c.isalnum() or c in "-_")
        channel_name = f"ticket-{clean_username}"

        # Controllo se l'utente ha già un ticket aperto
        existing_channel = discord.utils.get(guild.text_channels, name=channel_name)
        if existing_channel:
            await interaction.response.send_message(
                f"⚠️ Hai già un ticket aperto in corso: {existing_channel.mention}", 
                ephemeral=True
            )
            return

        # Crea o recupera la categoria TICKETS
        category = discord.utils.get(guild.categories, name="TICKETS")
        if not category:
            category = await guild.create_category("TICKETS")

        # Configurazione rigorosa dei permessi
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        # Dà visibilità automatica agli amministratori o ruoli con gestione canali
        for role in guild.roles:
            if role.permissions.administrator or role.permissions.manage_channels:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        # Crea il canale privato
        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="🎟️ TICKET DI SUPPORTO APERTO",
            description=(
                f"Benvenuto {user.mention}!\n\n"
                "Un membro dello Staff prenderà in carico la tua richiesta a breve.\n"
                "Descrivi il tuo problema in dettaglio fornendo tutte le informazioni utili."
            ),
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.set_footer(text="Usa i bottoni sottostanti per gestire il ticket.")

        # Invia il messaggio di benvenuto con i bottoni 'Reclama' e 'Chiudi'
        await channel.send(content=f"{user.mention}", embed=embed, view=TicketControlView())
        
        # Notifica privata all'utente
        await interaction.response.send_message(
            f"✅ **Ticket creato con successo!** Clicca qui per andare al canale: {channel.mention}", 
            ephemeral=True
        )

# ==============================================================================
# EVENTI E COMANDI BOT
# ==============================================================================

@bot.event
async def on_ready():
    # Registrazione Views persistenti (mantengono le funzionalità anche dopo i riavvii)
    bot.add_view(TicketLaunchView())
    bot.add_view(TicketControlView())
    
    print("--------------------------------------------------")
    print(f"🤖 Bot Ticket Online come: {bot.user.name} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"🔄 Sincronizzati {len(synced)} comandi Slash con successo!")
    except Exception as e:
        print(f"❌ Errore durante la sincronizzazione: {e}")
    print("--------------------------------------------------")

@bot.tree.command(name="setup_ticket", description="Invia il pannello per aprire i ticket (Solo per Staff/Admin).")
@app_commands.checks.has_permissions(manage_channels=True)
async def setup_ticket(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎫 CENTRO SUPPORTO & ASSISTENZA",
        description=(
            "Hai bisogno di aiuto o vuoi fare una segnalazione?\n\n"
            "Clicca sul pulsante **📩 Apri Ticket** qui sotto per creare una chat privata con lo Staff."
        ),
        color=discord.Color.green()
    )
    embed.set_footer(text="Sistema Gestione Ticket Ufficiale")
    
    await interaction.channel.send(embed=embed, view=TicketLaunchView())
    await interaction.response.send_message("✅ **Pannello ticket inviato con successo nel canale!**", ephemeral=True)

# Gestione errore permessi per /setup_ticket
@setup_ticket.error
async def setup_ticket_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "❌ Non hai i permessi necessari (Gestione Canali) per inviare il pannello dei ticket.", 
            ephemeral=True
        )

# ==============================================================================
# AVVIO BOT
# ==============================================================================

if __name__ == "__main__":
    token = get_bot_token()
    try:
        bot.run(token)
    except discord.errors.LoginFailure:
        print("❌ Token inserito non valido! Elimina 'ticket_config.json' e riavvia il bot.")
