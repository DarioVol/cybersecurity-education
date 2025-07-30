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
            
        # Connetti SILENZIOSAMENTE
        client = gspread.authorize(creds)
        sheet = client.open_by_key(sheet_id).sheet1
        
        return sheet
        
    except Exception as e:
        # Errori SILENZIOSI - solo se in debug mode
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


def is_health_check():
    """
    FILTRO DEFINITIVO - Rileva health check automatici basato sui dati reali raccolti
    
    Pattern identificato:
    - User-Agent: "Unknown"
    - Host: "N/A" 
    - Referer: "N/A"
    
    Returns:
        bool: True se è un health check, False se è un utente reale
    """
    try:
        # Ottieni header dalla richiesta
        user_agent = st.context.headers.get('user-agent', '')
        host = st.context.headers.get('host', '')
        referer = st.context.headers.get('referer', '')
        
        # PATTERN ESATTO degli health check automatici
        if user_agent == 'Unknown':
            return True
            
        # Backup: se tutti gli header sono N/A o vuoti
        if (user_agent in ['Unknown', 'N/A', '', None] and 
            host in ['N/A', '', None] and 
            referer in ['N/A', '', None]):
            return True
            
        return False
        
    except Exception:
        # Se c'è errore, assumiamo che sia un utente reale
        return False


def should_track_visit():
    """
    VERSIONE FINALE - Filtra health check basato sui dati reali
    
    Returns:
        bool: True se dovrebbe essere tracciata, False se è health check
    """
    # Se è un health check automatico, NON tracciare
    if is_health_check():
        return False
        
    # Altrimenti, traccia la visita
    return True


def show_debug_final():
    """
    DEBUG FINALE - mostra se il filtro funziona
    """
    if os.getenv("DEBUG_MODE", "").lower() == "true":
        user_agent = st.context.headers.get('user-agent', 'N/A')
        host = st.context.headers.get('host', 'N/A')
        referer = st.context.headers.get('referer', 'N/A')
        
        is_hc = is_health_check()
        should_track = should_track_visit()
        
        st.write("🔍 **DEBUG FINALE:**")
        st.write(f"**User-Agent:** '{user_agent}'")
        st.write(f"**Host:** '{host}'")
        st.write(f"**Referer:** '{referer}'")
        st.write(f"**È Health Check:** {is_hc}")
        st.write(f"**Verrà Tracciato:** {should_track}")
        
        if is_hc:
            st.error("❌ **HEALTH CHECK RILEVATO** - NON verrà tracciato")
        else:
            st.success("✅ **UTENTE REALE** - Verrà tracciato")
            
        st.write("---")


def track_page_opening():
    """
    VERSIONE FINALE con filtro health check funzionante
    
    Returns:
        bool: True se è la prima apertura tracciata, False se già tracciata o health check
    """
    # Debug finale solo se abilitato
    show_debug_final()
    
    # FILTRO HEALTH CHECK
    if not should_track_visit():
        return False  # ❌ Health check - NON tracciare
        
    if 'page_tracked' not in st.session_state:
        st.session_state.page_tracked = True
        st.session_state.user_data.update({
            'page_open_timestamp': datetime.now().isoformat(),
            'status': 'page_opened',
            'user_agent': st.context.headers.get('user-agent', 'Unknown'),
            'session_id': st.session_state.session_id
        })
        
        # Salva solo se è un utente reale
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
    VERSIONE FINALE con filtro health check
    
    Args:
        step (int): Numero step
        sheet: Google Sheet object  
        **kwargs: Dati da salvare
        
    Returns:
        bool: True se salvato correttamente
    """
    # FILTRO HEALTH CHECK
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
    
    # Salva solo se NON è health check
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
