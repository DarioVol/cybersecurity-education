#!/usr/bin/env python3
import streamlit as st
import pandas as pd
import json
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import os


def setup_google_sheets():
    """
    Configura connessione a Google Sheets in modo DISCRETO e SILENZIOSO
    Supporta: Streamlit Secrets, Variabili d'ambiente, File locale
    
    Returns:
        gspread.Worksheet or None: Sheet object se successo, None se errore
    """
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # PRIORITÀ 1: Streamlit Secrets (Production) - SILENZIOSO
        if "gcp_service_account" in st.secrets:
            creds = Credentials.from_service_account_info(
                st.secrets["gcp_service_account"], 
                scopes=scope
            )
            # Supporta tutti i formati per sheet_id
            sheet_id = (
                st.secrets.get("GOOGLE_SHEET_ID", "") or 
                st.secrets.get("sheet_id", "") or
                st.secrets.get("google_sheet_id", "") or
                st.secrets.get("gcp_service_account", {}).get("sheet_id", "") or
                st.secrets.get("gcp_service_account", {}).get("GOOGLE_SHEET_ID", "")
            )
            
        # PRIORITÀ 2: Variabili d'Ambiente - SILENZIOSO
        elif os.getenv("GOOGLE_PROJECT_ID"):
            service_account_info = {
                "type": "service_account",
                "project_id": os.getenv("GOOGLE_PROJECT_ID"),
                "private_key_id": os.getenv("GOOGLE_PRIVATE_KEY_ID"),
                "private_key": os.getenv("GOOGLE_PRIVATE_KEY", "").replace('\\n', '\n'),
                "client_email": os.getenv("GOOGLE_CLIENT_EMAIL"),
                "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{os.getenv('GOOGLE_CLIENT_EMAIL', '').replace('@', '%40')}"
            }
            creds = Credentials.from_service_account_info(service_account_info, scopes=scope)
            sheet_id = os.getenv("GOOGLE_SHEET_ID", "")
            
        # PRIORITÀ 3: File JSON locale (Development) - SILENZIOSO
        elif os.path.exists("credentials.json"):
            creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
            sheet_id = os.getenv("GOOGLE_SHEET_ID", "DEFAULT_SHEET_ID")
            
        # PRIORITÀ 4: File config.json - SILENZIOSO
        elif os.path.exists("config.json"):
            with open("config.json", "r") as f:
                config = json.load(f)
            creds = Credentials.from_service_account_info(
                config["google_sheets"]["service_account"], 
                scopes=scope
            )
            sheet_id = config["google_sheets"]["sheet_id"]
            
        else:
            # FALLBACK SILENZIOSO - nessun warning
            return None
            
        # Verifica sheet_id SILENZIOSAMENTE
        if not sheet_id or sheet_id == "DEFAULT_SHEET_ID":
            return None
            
        # Connetti 
        client = gspread.authorize(creds)
        sheet = client.open_by_key(sheet_id).sheet1
        
        return sheet
        
    except Exception as e:
        # Errori visibili solo se in debug mode
        if os.getenv("DEBUG_MODE", "").lower() == "true":
            st.error(f"Debug: Errore Google Sheets: {e}")
        return None


def initialize_google_sheet_structure(sheet):
    """
    Inizializza la struttura fissa del Google Sheet con header predefiniti
    """
    try:
        # Header fissi che NON cambiano mai
        FIXED_HEADERS = [
            'Session_ID',
            'Timestamp_Apertura', 
            'Timestamp_Inizio_Form',
            'Timestamp_Step2',
            'Timestamp_Completamento',
            'Dove_Trovato_QR',
            'Fascia_Eta',
            'Sesso', 
            'Provincia_Nascita',
            'Titolo_Studio',
            'Status_Finale',
            'Completato',
            'User_Agent',
            'Data_Creazione'
        ]
        
        # Verifica se il sheet è vuoto o ha struttura sbagliata
        try:
            existing_data = sheet.get_all_values()
            
            # Se è vuoto o la prima riga non corrisponde agli header, resetta
            if (not existing_data or 
                len(existing_data) == 0 or 
                existing_data[0] != FIXED_HEADERS):
                
                # Pulisce tutto e ricrea con header fissi
                sheet.clear()
                sheet.append_row(FIXED_HEADERS)
                
        except Exception:
            # Se c'è qualsiasi errore, ricrea da zero
            sheet.clear()
            sheet.append_row(FIXED_HEADERS)
            
        return True
        
    except Exception as e:
        if os.getenv("DEBUG_MODE", "").lower() == "true":
            st.error(f"Debug: Errore inizializzazione: {e}")
        return False


def save_to_google_sheets_fixed(data, sheet):
    """
    Salva dati con struttura FISSA e CONSISTENTE - sempre 14 colonne
    """
    try:
        if not sheet:
            return False
            
        # Inizializza struttura se necessario
        if not initialize_google_sheet_structure(sheet):
            return False
        
        # Struttura FISSA dei dati (sempre uguale)
        session_id = data.get('session_id', '')
        
        # Prepara riga con struttura FISSA (sempre 14 colonne)
        fixed_row = [
            session_id,                                      # Session_ID
            data.get('page_open_timestamp', ''),             # Timestamp_Apertura
            data.get('form_started_timestamp', ''),          # Timestamp_Inizio_Form  
            data.get('step2_timestamp', ''),                 # Timestamp_Step2
            data.get('completion_timestamp', ''),            # Timestamp_Completamento
            data.get('qr_location', ''),                     # Dove_Trovato_QR
            data.get('age_range', ''),                       # Fascia_Eta
            data.get('gender', ''),                          # Sesso
            data.get('birth_province', ''),                  # Provincia_Nascita
            data.get('education', ''),                       # Titolo_Studio
            data.get('status', ''),                          # Status_Finale
            'Sì' if data.get('completed') else 'No',        # Completato
            data.get('user_agent', ''),                      # User_Agent
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')     # Data_Creazione
        ]
        
        # Cerca se esiste già una riga per questa sessione
        all_data = sheet.get_all_values()
        existing_row_index = None
        
        for i, row in enumerate(all_data[1:], start=2):  # Skip header
            if len(row) > 0 and row[0] == session_id:
                existing_row_index = i
                break
        
        if existing_row_index:
            # AGGIORNA riga esistente - mantiene sempre 14 colonne
            for col_index, value in enumerate(fixed_row, start=1):
                if value:  # Aggiorna solo se c'è un valore
                    sheet.update_cell(existing_row_index, col_index, value)
        else:
            # AGGIUNGI nuova riga - sempre 14 colonne
            sheet.append_row(fixed_row)
        
        return True
        
    except Exception as e:
        if os.getenv("DEBUG_MODE", "").lower() == "true":
            st.error(f"Debug: Errore salvataggio: {e}")
        return False


def emergency_cleanup_sheet():
    """
    FUNZIONE TEMPORANEA - Pulisce completamente il Google Sheet rovinato
    Esegui UNA VOLTA SOLA, poi rimuovi questa funzione
    """
    sheet = setup_google_sheets()
    if sheet:
        try:
            # PULISCE TUTTO
            sheet.clear()
            
            # RICREA HEADER FISSI
            FIXED_HEADERS = [
                'Session_ID',
                'Timestamp_Apertura', 
                'Timestamp_Inizio_Form',
                'Timestamp_Step2',
                'Timestamp_Completamento',
                'Dove_Trovato_QR',
                'Fascia_Eta',
                'Sesso', 
                'Provincia_Nascita',
                'Titolo_Studio',
                'Status_Finale',
                'Completato',
                'User_Agent',
                'Data_Creazione'
            ]
            sheet.append_row(FIXED_HEADERS)
            
            st.success("✅ Google Sheet ripulito e ricreato con struttura corretta!")
            st.info("🗑️ RIMUOVI questa funzione dal codice dopo l'uso!")
            
        except Exception as e:
            st.error(f"Errore pulizia sheet: {e}")
    else:
        st.warning("Impossibile connettersi al Google Sheet per la pulizia")


def get_province_list():
    """
    Restituisce lista completa delle province italiane + Estero
    
    Returns:
        list: Lista province
    """
    return [
        "","Estero", "Agrigento", "Alessandria", "Ancona", "Aosta", "Arezzo", "Ascoli Piceno", 
        "Asti", "Avellino", "Bari", "Barletta-Andria-Trani", "Belluno", "Benevento", 
        "Bergamo", "Biella", "Bologna", "Bolzano", "Brescia", "Brindisi", "Cagliari", 
        "Caltanissetta", "Campobasso", "Caserta", "Catania", "Catanzaro", "Chieti", 
        "Como", "Cosenza", "Cremona", "Crotone", "Cuneo", "Enna", "Fermo", "Ferrara", 
        "Firenze", "Foggia", "Forlì-Cesena", "Frosinone", "Genova", "Gorizia", 
        "Grosseto", "Imperia", "Isernia", "L'Aquila", "La Spezia", "Latina", "Lecce", 
        "Lecco", "Livorno", "Lodi", "Lucca", "Macerata", "Mantova", "Massa-Carrara", 
        "Matera", "Messina", "Milano", "Modena", "Monza e Brianza", "Napoli", "Novara", 
        "Nuoro", "Oristano", "Padova", "Palermo", "Parma", "Pavia", "Perugia", 
        "Pesaro e Urbino", "Pescara", "Piacenza", "Pisa", "Pistoia", "Pordenone", 
        "Potenza", "Prato", "Ragusa", "Ravenna", "Reggio Calabria", "Reggio Emilia", 
        "Rieti", "Rimini", "Roma", "Rovigo", "Salerno", "Sassari", "Savona", "Siena", 
        "Siracusa", "Sondrio", "Sud Sardegna", "Taranto", "Teramo", "Terni", "Torino", 
        "Trapani", "Trento", "Treviso", "Trieste", "Udine", "Varese", "Venezia", 
        "Verbano-Cusio-Ossola", "Vercelli", "Verona", "Vibo Valentia", "Vicenza", 
        "Viterbo"
    ]


def get_qr_location_options():
    """
    Restituisce lista opzioni dove è stato trovato il QR code
    
    Returns:
        list: Lista opzioni QR location
    """
    return [
        "",
        "Mezzi pubblici",
        "Posto di lavoro", 
        "Spazio pubblico",
        "Cassetta della posta",
        "Macchina",
        "Università/Scuola",
        "Bar/Ristorante",
        "Centro commerciale",
        "Centro sportivo",
        "Altro"
    ]

def is_bot_or_health_check():
    """
    Rileva se la richiesta proviene da un bot, health check o sistema automatico
    
    Returns:
        bool: True se è un bot/health check, False se è un utente reale
    """
    try:
        # Ottieni User-Agent dalla richiesta
        user_agent = st.context.headers.get('user-agent', '').lower()
        
        # Ottieni eventuali header di health check
        referer = st.context.headers.get('referer', '').lower()
        
        # Lista di pattern che indicano bot o health check
        bot_patterns = [
            'bot', 'crawler', 'spider', 'scraper',
            'health', 'check', 'monitor', 'ping',
            'uptime', 'status', 'test', 'probe',
            'streamlit-cloud', 'streamlit-health',
            'python-requests', 'curl', 'wget',
            'axios', 'fetch', 'httpx'
        ]
        
        # Health check endpoint patterns (se accessibili tramite query params o simili)
        health_check_patterns = [
            'healthz', 'health-check', 'script-health-check',
            '_stcore/health', 'ping', 'status'
        ]
        
        # Controlla User-Agent per pattern di bot
        for pattern in bot_patterns:
            if pattern in user_agent:
                return True
                
        # Controlla se il referer contiene pattern di health check
        for pattern in health_check_patterns:
            if pattern in referer:
                return True
        
        # User-Agent troppo corto o generico (spesso bot)
        if len(user_agent) < 10:
            return True
            
        # User-Agent vuoto o "Unknown" (il nostro fallback)
        if user_agent in ['', 'unknown', 'none', '-']:
            return True
            
        # Controlla se User-Agent è troppo semplice (es: solo "python" o "streamlit")
        simple_patterns = ['python', 'streamlit', 'requests', 'urllib']
        if any(user_agent.strip() == pattern for pattern in simple_patterns):
            return True
            
        return False
        
    except Exception:
        # Se c'è qualsiasi errore, assumiamo che sia un utente reale
        return False


def is_frequent_visitor():
    """
    Rileva accessi troppo frequenti dalla stessa sessione (possibili health check)
    
    Returns:
        bool: True se l'accesso è troppo frequente
    """
    try:
        # Ottieni timestamp corrente
        current_time = datetime.now()
        
        # Controlla se esiste già un timestamp di ultimo accesso
        if 'last_access_time' in st.session_state:
            last_access = st.session_state.last_access_time
            time_diff = (current_time - last_access).total_seconds()
            
            # Se l'accesso è avvenuto meno di 2 minuti fa, probabilmente è un health check
            if time_diff < 120:  # 2 minuti
                return True
        
        # Aggiorna timestamp ultimo accesso
        st.session_state.last_access_time = current_time
        return False
        
    except Exception:
        return False


def should_track_visit():
    """
    Determina se questa visita dovrebbe essere tracciata
    
    Returns:
        bool: True se dovrebbe essere tracciata, False se ignorata
    """
    user_agent = st.context.headers.get('user-agent', 'Unknown')
    
    # Se User-Agent è 'Unknown', è un health check automatico
    if user_agent == 'Unknown':
        return False  # Non tracciare
        
    return True  # traccia


def track_page_opening():
    """
    Versione FILTRATA per tracking apertura pagina - ignora bot e health check
    
    Returns:
        bool: True se è la prima apertura tracciata, False se già tracciata o ignorata
    """
    # Controlla se dovremmo tracciare questa visita
    if not should_track_visit():
        return False
        
    if 'page_tracked' not in st.session_state:
        st.session_state.page_tracked = True
        st.session_state.user_data.update({
            'page_open_timestamp': datetime.now().isoformat(),
            'status': 'page_opened',
            'user_agent': st.context.headers.get('user-agent', 'Unknown'),
            'session_id': st.session_state.session_id
        })
        
        # Salva SILENZIOSAMENTE solo se è un utente reale
        sheet = setup_google_sheets()
        if sheet:
            save_to_google_sheets_fixed(st.session_state.user_data, sheet)
        
        return True
    
    return False

def save_step_data(step, sheet, **kwargs):
    """
    Versione FILTRATA per salvare dati step - ignora bot e health check
    
    Args:
        step (int): Numero step
        sheet: Google Sheet object  
        **kwargs: Dati da salvare
        
    Returns:
        bool: True se salvato correttamente
    """
    # Non salvare dati se è un bot o health check
    if not should_track_visit():
        return True  # Ritorna True per non bloccare l'UI, ma non salva nulla
        
    timestamp = datetime.now().isoformat()
    
    if step == 1:
        st.session_state.user_data.update({
            'qr_location': kwargs.get('qr_location'),
            'form_started_timestamp': timestamp,
            'status': 'form_started'
        })
    
    elif step == 2:
        st.session_state.user_data.update({
            'age_range': kwargs.get('age_range'),
            'gender': kwargs.get('gender'),
            'birth_province': kwargs.get('birth_province'),
            'education': kwargs.get('education'),
            'status': 'step2_completed',
            'step2_timestamp': timestamp
        })
    
    elif step == 3:
        st.session_state.user_data.update({
            'status': 'fully_completed',
            'completion_timestamp': timestamp,
            'completed': True
        })
    
    # Salva con la nuova funzione FISSA solo se è un utente reale
    if sheet:
        return save_to_google_sheets_fixed(st.session_state.user_data, sheet)
    
    return True


def debug_visit_info():
    """
    Funzione DEBUG per vedere informazioni sulla visita corrente
    Usare solo temporaneamente per verificare il filtro
    """
    if os.getenv("DEBUG_MODE", "").lower() == "true":
        st.write("🔍 **DEBUG VISITA:**")
        
        user_agent = st.context.headers.get('user-agent', 'N/A')
        st.write(f"User-Agent: {user_agent}")
        
        is_bot = is_bot_or_health_check()
        st.write(f"È Bot/Health Check: {is_bot}")
        
        is_frequent = is_frequent_visitor()
        st.write(f"È Accesso Frequente: {is_frequent}")
        
        should_track = should_track_visit()
        st.write(f"Dovrebbe essere tracciato: {should_track}")
        
        st.write("---")

def get_age_ranges():
    """
    Restituisce lista fasce d'età
    
    Returns:
        list: Lista fasce età
    """
    return [
        "",
        "< 18",
        "18-23", 
        "24-29",
        "30-35",
        "36-40", 
        "41-50",
        "51-60",
        "61-70",
        "Over 71"
    ]


def get_education_levels():
    """
    Restituisce lista titoli di studio
    
    Returns:
        list: Lista titoli studio
    """
    return [
        "",
        "Scuola media",
        "Diploma superiore", 
        "Laurea triennale",
        "Laurea magistrale",
        "Master/Dottorato"
    ]


def get_gender_options():
    """
    Restituisce opzioni genere
    
    Returns:
        list: Lista opzioni genere
    """
    return ["", "Maschio", "Femmina", "Altro"]


def initialize_session_state():
    """
    Inizializza session state di Streamlit con valori di default
    """
    if 'step' not in st.session_state:
        st.session_state.step = 1
    if 'user_data' not in st.session_state:
        st.session_state.user_data = {}
    if 'session_id' not in st.session_state:
        # Genera un ID unico per questa sessione
        st.session_state.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(str(datetime.now()))}"
        st.session_state.user_data['session_id'] = st.session_state.session_id


def track_page_opening():
    """
    Versione DISCRETA per tracking apertura pagina - SILENZIOSO
    
    Returns:
        bool: True se è la prima apertura, False se già tracciata
    """
    if 'page_tracked' not in st.session_state:
        st.session_state.page_tracked = True
        st.session_state.user_data.update({
            'page_open_timestamp': datetime.now().isoformat(),
            'status': 'page_opened',
            'user_agent': st.context.headers.get('user-agent', 'Unknown'),
            'session_id': st.session_state.session_id
        })
        
        # Salva SILENZIOSAMENTE 
        sheet = setup_google_sheets()
        if sheet:
            save_to_google_sheets_fixed(st.session_state.user_data, sheet)
        
        return True
    
    return False


def create_progress_bar(step_number, total_steps=3):
    """
    Crea barra di progresso per i step
    
    Args:
        step_number (int): Step corrente (1-3)
        total_steps (int): Numero totale step
    """
    progress = step_number / total_steps
    st.progress(progress)
    st.write(f"Progresso: {int(progress*100)}%")


def validate_step_data(step, age_range=None, gender=None, birth_province=None, 
                      education=None, qr_location=None, 
                      consent=None, email_input=None):
    """
    Valida i dati inseriti per ogni step
    
    Args:
        step (int): Numero step da validare
        **kwargs: Dati da validare per lo step specifico
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if step == 1:
        if not consent:
            return False, "Devi accettare il trattamento dati per continuare"
        if not qr_location:
            return False, "Indica dove hai trovato il QR code per continuare"
        return True, ""
    
    elif step == 2:
        if not age_range or not gender or not birth_province or not education:
            return False, "Completa tutti i campi per continuare"
        return True, ""
    
    elif step == 3:
        if not email_input:
            return False, "Inserisci la tua email per ricevere il buono Amazon"
        return True, ""
    
    return True, ""


def save_step_data(step, sheet, **kwargs):
    """
    Versione FISSA per salvare dati step - sempre stessa struttura
    
    Args:
        step (int): Numero step
        sheet: Google Sheet object  
        **kwargs: Dati da salvare
        
    Returns:
        bool: True se salvato correttamente
    """
    timestamp = datetime.now().isoformat()
    
    if step == 1:
        st.session_state.user_data.update({
            'qr_location': kwargs.get('qr_location'),
            'form_started_timestamp': timestamp,
            'status': 'form_started'
        })
    
    elif step == 2:
        st.session_state.user_data.update({
            'age_range': kwargs.get('age_range'),
            'gender': kwargs.get('gender'),
            'birth_province': kwargs.get('birth_province'),
            'education': kwargs.get('education'),
            'status': 'step2_completed',
            'step2_timestamp': timestamp
        })
    
    elif step == 3:
        st.session_state.user_data.update({
            'status': 'fully_completed',
            'completion_timestamp': timestamp,
            'completed': True
        })
    
    # Salva con la nuova funzione FISSA
    if sheet:
        return save_to_google_sheets_fixed(st.session_state.user_data, sheet)
    
    return True


def create_data_download(user_data):
    """
    Crea file JSON scaricabile con i dati utente
    
    Args:
        user_data (dict): Dati utente
        
    Returns:
        str: JSON string per download
    """
    download_data = {
        'session_id': user_data.get('session_id', 'unknown'),
        'completion_timestamp': user_data.get('completion_timestamp', datetime.now().isoformat()),
        'qr_location': user_data.get('qr_location', ''),
        'age_range': user_data.get('age_range', ''),
        'gender': user_data.get('gender', ''),
        'birth_province': user_data.get('birth_province', ''),
        'education': user_data.get('education', ''),
        'status': user_data.get('status', ''),
        'note': 'Dati raccolti per progetto educativo cybersecurity - Email NON salvata'
    }
    
    return json.dumps(download_data, indent=2, ensure_ascii=False)


def display_collected_data(user_data):
    """
    Mostra i dati raccolti in formato tabella
    
    Args:
        user_data (dict): Dati da visualizzare
        
    Returns:
        pandas.DataFrame: DataFrame per visualizzazione
    """
    data_df = pd.DataFrame([
        ["🆔 ID Sessione", user_data.get('session_id', '')],
        ["⏱️ Apertura pagina", user_data.get('page_open_timestamp', '')],
        ["Dove trovato QR Code", user_data.get('qr_location', '')],
        ["Fascia d'età", user_data.get('age_range', '')],
        ["Sesso", user_data.get('gender', '')],
        ["Provincia di nascita", user_data.get('birth_province', '')],
        ["Titolo di studio", user_data.get('education', '')],
        ["⚠️ Email", "SÌ (avresti dato anche quella!)"]
    ], columns=["Campo", "Valore"])
    
    return data_df


def reset_session():
    """
    Resetta completamente la sessione per ricominciare
    """
    st.session_state.step = 1
    st.session_state.user_data = {}
    st.session_state.page_tracked = False
    
    # Genera nuovo session ID
    st.session_state.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(str(datetime.now()))}"
    st.session_state.user_data['session_id'] = st.session_state.session_id


def load_custom_css():
    """
    Carica CSS personalizzato per migliorare l'aspetto dell'app
    """
    st.markdown("""
    <style>
        .main-header {
            text-align: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 2rem;
            border-radius: 15px;
            color: white;
            margin-bottom: 2rem;
        }
        
        .discount-badge {
            background: linear-gradient(45deg, #ff416c, #ff4b2b);
            color: white;
            padding: 1rem 2rem;
            border-radius: 50px;
            font-size: 2rem;
            font-weight: bold;
            text-align: center;
            margin: 1rem 0;
        }
        
        .warning-box {
            background: #ff4444;
            color: white;
            padding: 2rem;
            border-radius: 10px;
            margin: 2rem 0;
            text-align: center;
        }
        
        .data-collected {
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
            border-left: 4px solid #ff4444;
        }
        
        .logo {
            background: #ff9900;
            color: white;
            padding: 1rem 2rem;
            border-radius: 8px;
            font-weight: bold;
            text-align: center;
            margin: 1rem auto;
            width: fit-content;
        }
    </style>
    """, unsafe_allow_html=True)
