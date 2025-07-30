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


def log_all_visits():
    """
    LOGGER TEMPORANEO - registra TUTTE le visite per trovare il pattern degli health check
    
    Aggiunge una riga di log per ogni visita con timestamp preciso per identificare 
    gli accessi automatici ogni 5 minuti
    """
    try:
        # Ottieni tutti gli header disponibili
        user_agent = st.context.headers.get('user-agent', 'N/A')
        referer = st.context.headers.get('referer', 'N/A')
        host = st.context.headers.get('host', 'N/A')
        
        # Timestamp preciso con secondi
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Genera un ID unico per questa visita specifica
        visit_id = f"visit_{datetime.now().strftime('%H%M%S')}_{hash(str(datetime.now().microsecond))}"
        
        # Dati di debug da salvare
        debug_data = {
            'visit_id': visit_id,
            'timestamp': timestamp,
            'user_agent': user_agent,
            'referer': referer,
            'host': host,
            'session_id': getattr(st.session_state, 'session_id', 'no_session'),
            'is_page_tracked': 'page_tracked' in st.session_state,
            'step': getattr(st.session_state, 'step', 'no_step')
        }
        
        # Salva nel Google Sheet con una riga speciale di debug
        sheet = setup_google_sheets()
        if sheet:
            # Riga di debug separata per non rovinare i dati reali
            debug_row = [
                f"DEBUG_{visit_id}",  # Session_ID
                timestamp,            # Timestamp_Apertura
                "",                   # Timestamp_Inizio_Form
                "",                   # Timestamp_Step2
                "",                   # Timestamp_Completamento
                "",                   # Dove_Trovato_QR
                "",                   # Fascia_Eta
                "",                   # Sesso
                "",                   # Provincia_Nascita
                "",                   # Titolo_Studio
                "DEBUG_LOG",          # Status_Finale
                "No",                 # Completato
                user_agent,           # User_Agent
                f"REF:{referer}|HOST:{host}"  # Data_Creazione (usiamo per altri header)
            ]
            
            sheet.append_row(debug_row)
        
        return debug_data
        
    except Exception as e:
        # Se c'è errore, almeno mostra in debug mode
        if os.getenv("DEBUG_MODE", "").lower() == "true":
            st.error(f"Errore debug logging: {e}")
        return None


def show_detailed_debug():
    """
    Mostra DEBUG DETTAGLIATO per ogni visita
    """
    if os.getenv("DEBUG_MODE", "").lower() == "true":
        st.write("🔍 **DEBUG DETTAGLIATO:**")
        
        # Log questa visita
        debug_data = log_all_visits()
        
        if debug_data:
            st.write(f"**Visit ID:** {debug_data['visit_id']}")
            st.write(f"**Timestamp:** {debug_data['timestamp']}")
            st.write(f"**User-Agent:** '{debug_data['user_agent']}'")
            st.write(f"**Referer:** '{debug_data['referer']}'")
            st.write(f"**Host:** '{debug_data['host']}'")
            st.write(f"**Session ID:** {debug_data['session_id']}")
            st.write(f"**Page già tracciata:** {debug_data['is_page_tracked']}")
            st.write(f"**Step corrente:** {debug_data['step']}")
        
        # Analisi automatica per rilevare health check
        user_agent = debug_data['user_agent'] if debug_data else 'N/A'
        
        # Possibili pattern di health check
        possible_health_check = False
        reasons = []
        
        if user_agent == 'N/A' or user_agent == '':
            possible_health_check = True
            reasons.append("User-Agent vuoto")
            
        if 'python' in user_agent.lower():
            possible_health_check = True
            reasons.append("Contiene 'python'")
            
        if 'streamlit' in user_agent.lower():
            possible_health_check = True
            reasons.append("Contiene 'streamlit'")
            
        if 'health' in user_agent.lower():
            possible_health_check = True
            reasons.append("Contiene 'health'")
            
        if len(user_agent) < 20 and user_agent != 'N/A':
            possible_health_check = True
            reasons.append("User-Agent troppo corto")
        
        if possible_health_check:
            st.error(f"🚨 **POSSIBILE HEALTH CHECK** - Motivi: {', '.join(reasons)}")
        else:
            st.success("✅ **PROBABILMENTE UTENTE REALE**")
            
        st.write("---")
        
        # Istruzioni per analisi
        st.info("""
        **📊 Come analizzare:**
        1. Lascia questa pagina aperta per 10-15 minuti
        2. Vai nel Google Sheet e ordina per timestamp
        3. Cerca righe che appaiono ogni ~5 minuti con lo stesso User-Agent
        4. Quelle sono gli health check automatici!
        """)


def track_page_opening():
    """
    Versione con LOGGING DETTAGLIATO per trovare health check
    """
    # SEMPRE mostra debug se abilitato (anche senza dovrebbe tracciare)
    show_detailed_debug()
    
    # Per ora, traccia TUTTO per raccogliere dati
    # (Dopo aver trovato il pattern, aggiungeremo il filtro)
    if 'page_tracked' not in st.session_state:
        st.session_state.page_tracked = True
        st.session_state.user_data.update({
            'page_open_timestamp': datetime.now().isoformat(),
            'status': 'page_opened',
            'user_agent': st.context.headers.get('user-agent', 'Unknown'),
            'session_id': st.session_state.session_id
        })
        
        # Salva SEMPRE per ora (per raccogliere dati)
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
    Versione TEMPORANEA - salva TUTTO per raccogliere dati sui pattern
    (Aggiungeremo il filtro dopo aver trovato il pattern degli health check)
    
    Args:
        step (int): Numero step
        sheet: Google Sheet object  
        **kwargs: Dati da salvare
        
    Returns:
        bool: True se salvato correttamente
    """
    # PER ORA NON FILTRIAMO - raccogliamo tutti i dati per analisi
    
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
    
    # Salva SEMPRE per raccogliere dati completi
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
