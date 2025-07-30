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
    Configura connessione a Google Sheets in modo sicuro
    Supporta: Streamlit Secrets, Variabili d'ambiente, File locale
    
    Returns:
        gspread.Worksheet or None: Sheet object se successo, None se errore
    """
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # PRIORITÀ 1: Streamlit Secrets (Production)
        if "gcp_service_account" in st.secrets:
            st.info("Usando Streamlit Secrets per Google Sheets")
            creds = Credentials.from_service_account_info(
                st.secrets["gcp_service_account"], 
                scopes=scope
            )
            # FIX: Supporta entrambi i formati per sheet_id
            sheet_id = (
                st.secrets.get("GOOGLE_SHEET_ID", "") or 
                st.secrets.get("sheet_id", "") or
                st.secrets.get("google_sheet_id", "")
            )
            
        # PRIORITÀ 2: Variabili d'Ambiente
        elif os.getenv("GOOGLE_PROJECT_ID"):
            st.info("Usando variabili d'ambiente per Google Sheets")
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
            
        # PRIORITÀ 3: File JSON locale (Development)
        elif os.path.exists("credentials.json"):
            st.info("Usando file credentials.json locale")
            creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
            sheet_id = os.getenv("GOOGLE_SHEET_ID", "DEFAULT_SHEET_ID")
            
        # PRIORITÀ 4: File config.json
        elif os.path.exists("config.json"):
            st.info("Usando file config.json")
            with open("config.json", "r") as f:
                config = json.load(f)
            creds = Credentials.from_service_account_info(
                config["google_sheets"]["service_account"], 
                scopes=scope
            )
            sheet_id = config["google_sheets"]["sheet_id"]
            
        else:
            st.warning("⚠️ Nessuna configurazione Google Sheets trovata")
            st.info("""
            **Per abilitare Google Sheets, configura uno di questi:**
            - **Streamlit Cloud:** Aggiungi secrets nelle impostazioni app
            - **Locale:** Crea file .env con le variabili d'ambiente
            - **Development:** Usa file credentials.json
            
            **L'app funziona comunque** con download JSON! 📥
            """)
            return None
            
        # Verifica che abbiamo l'ID del foglio
        if not sheet_id or sheet_id == "DEFAULT_SHEET_ID":
            st.warning("⚠️ ID Google Sheet non configurato")
            st.info("""
            **Per Streamlit Secrets:** Aggiungi `sheet_id` o `GOOGLE_SHEET_ID` nei secrets
            **Per variabili d'ambiente:** Aggiungi `GOOGLE_SHEET_ID`
            """)
            # DEBUG: Mostra cosa è stato trovato
            st.write("🔍 **DEBUG:** Sheet ID letto:", repr(sheet_id))
            if "gcp_service_account" in st.secrets:
                available_keys = [k for k in st.secrets.keys() if 'sheet' in k.lower()]
                st.write("🔍 **DEBUG:** Chiavi con 'sheet' nei secrets:", available_keys)
            return None
            
        # Connetti al Google Sheet
        client = gspread.authorize(creds)
        sheet = client.open_by_key(sheet_id).sheet1
        
        st.success("✅ Google Sheets connesso con successo!")
        return sheet
        
    except FileNotFoundError:
        st.warning("📁 File credentials.json non trovato")
        return None
    except Exception as e:
        st.warning(f"❌ Errore configurazione Google Sheets: {e}")
        st.info("""
        **Possibili cause:**
        - Credenziali non valide
        - Foglio Google non condiviso con il service account
        - ID del foglio errato
        - Permessi insufficienti
        
        **Soluzione:** Controlla la configurazione o usa solo download JSON
        """)
        return None


def save_to_google_sheets(data, sheet):
    """
    Salva i dati raccolti su Google Sheets con tracking progressivo e aperture pagina
    
    Args:
        data (dict): Dati da salvare
        sheet: Google Sheet object
        
    Returns:
        bool: True se salvato con successo, False se errore
    """
    try:
        # Genera un ID unico per la sessione se non esiste
        if 'session_id' not in data:
            data['session_id'] = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(str(data.get('page_open_timestamp', '')))}"
        
        # Prepara i dati per Google Sheets
        row_data = [
            data.get('session_id', ''),
            data.get('page_open_timestamp', ''),
            data.get('form_started_timestamp', ''),
            data.get('qr_location', ''),
            data.get('age_range', ''),
            data.get('gender', ''),
            data.get('birth_province', ''),
            #data.get('residence_province', ''),
            data.get('education', ''),
            data.get('status', ''),
            data.get('step2_timestamp', ''),
            data.get('step3_timestamp', ''),
            data.get('completion_timestamp', ''),
            data.get('user_agent', ''),
            'Sì' if data.get('completed') else 'No'
        ]
        
        # Aggiungi intestazioni se è la prima riga
        if sheet.row_count == 0:
            headers = [
                'Session ID', 'Apertura Pagina', 'Inizio Form', 'Dove Trovato QR', 'Fascia Età', 
                'Sesso', 'Provincia Nascita', 'Provincia Residenza', 'Titolo Studio',
                'Stato', 'Timestamp Step 2', 'Timestamp Step 3', 
                'Timestamp Completamento', 'User Agent', 'Completato'
            ]
            sheet.append_row(headers)
        
        # Controlla se esiste già una riga per questa sessione
        try:
            all_values = sheet.get_all_values()
            session_id = data.get('session_id', '')
            
            # Trova la riga esistente (se esiste)
            existing_row = None
            for i, row in enumerate(all_values[1:], start=2):  # Skip header
                if len(row) > 0 and row[0] == session_id:
                    existing_row = i
                    break
            
            if existing_row:
                # Aggiorna la riga esistente
                for col, value in enumerate(row_data, start=1):
                    if value:  # Solo aggiorna se c'è un valore
                        sheet.update_cell(existing_row, col, value)
                st.success("Dati aggiornati su Google Sheets")
            else:
                # Aggiungi nuova riga
                sheet.append_row(row_data)
                st.success("Dati salvati su Google Sheets")
                
        except Exception as e:
            # Fallback: aggiungi sempre nuova riga
            sheet.append_row(row_data)
            st.success("Dati salvati su Google Sheets")
        
        return True
        
    except Exception as e:
        st.error(f"❌ Errore nel salvare su Google Sheets: {e}")
        return False


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


def track_page_opening():
    """
    Traccia l'apertura della pagina (eseguito una sola volta per sessione)
    
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
        
        # Salva subito il tracking dell'apertura
        sheet = setup_google_sheets()
        if sheet:
            save_to_google_sheets(st.session_state.user_data, sheet)
        
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
                      #residence_province=None, 
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
    Salva dati di uno step specifico
    
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
    
    # Salva su Google Sheets
    if sheet:
        return save_to_google_sheets(st.session_state.user_data, sheet)
    
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
        #'residence_province': user_data.get('residence_province', ''),
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
        #["Provincia di residenza", user_data.get('residence_province', '')],
        ["Titolo di studio", user_data.get('education', '')],
        ["⚠️ Email", "SÌ (avresti dato anche quella!)"]
        #,["Timestamp completamento", user_data.get('completion_timestamp', '')]
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


# Configurazione CSS per styling
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
