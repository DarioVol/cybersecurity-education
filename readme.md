# 🔒 Cybersecurity Education - Social Engineering Demo

## 📋 Descrizione

Applicazione educativa che simula un attacco di **social engineering** e **phishing** attraverso QR code fasulli. L'obiettivo è sensibilizzare gli utenti sui rischi della cybersicurezza mostrando loro come i criminali informatici raccolgono dati personali.

## ⚠️ Importante

**Questo progetto è esclusivamente educativo.** Non utilizzare per scopi malevoli. L'applicazione dimostra tecniche di social engineering per scopi didattici e di sensibilizzazione.

## 🎯 Caratteristiche

- **Simulazione realistica** di una truffa QR code
- **Tracking silenzioso** dell'apertura pagina
- **Raccolta dati progressiva** attraverso form apparentemente innocui
- **Rivelazione educativa** finale con consigli di sicurezza
- **Salvataggio dati** su Google Sheets per analisi successive
- **Sistema no log** - nessun log visibile agli utenti

## 🚀 Installazione Locale

### 1. Clona il Repository
```bash
git clone https://github.com/tuousername/cybersecurity-education.git
cd cybersecurity-education
```

### 2. Installa le Dipendenze
```bash
pip install -r requirements.txt
```

### 3. Configurazione Google Sheets (Opzionale)

#### Opzione A: File credentials.json (Sviluppo)
1. Vai su [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuovo progetto
3. Abilita le API:
   - Google Sheets API
   - Google Drive API
4. Crea un Service Account
5. Scarica il file JSON delle credenziali
6. Rinominalo in `credentials.json` e mettilo nella directory root
7. Crea un Google Sheet e condividilo con l'email del service account

#### Opzione B: Variabili d'Ambiente
```bash
# Crea file .env
GOOGLE_PROJECT_ID=il-tuo-project-id
GOOGLE_PRIVATE_KEY_ID=il-tuo-private-key-id
GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nla-tua-chiave\n-----END PRIVATE KEY-----\n"
GOOGLE_CLIENT_EMAIL=service-account@progetto.iam.gserviceaccount.com
GOOGLE_CLIENT_ID=il-tuo-client-id
GOOGLE_SHEET_ID=id-del-tuo-google-sheet
```

### 4. Esegui l'Applicazione
```bash
streamlit run app.py
```

## ☁️ Deployment su Streamlit Cloud

### 1. Fork su GitHub
Fork questo repository sul tuo account GitHub

### 2. Deploy su Streamlit Cloud
1. Vai su [share.streamlit.io](https://share.streamlit.io)
2. Connetti il tuo repository GitHub
3. Seleziona il file `app.py` come entry point

### 3. Configura i Secrets
Vai nelle impostazioni dell'app → Secrets e aggiungi:

```toml
sheet_id = "ID_DEL_TUO_GOOGLE_SHEET"

[gcp_service_account]
type = "service_account"
project_id = "il-tuo-project-id"
private_key_id = "il-tuo-private-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\nla-tua-chiave-privata\n-----END PRIVATE KEY-----\n"
client_email = "service-account@progetto.iam.gserviceaccount.com"
client_id = "il-tuo-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/service-account%40progetto.iam.gserviceaccount.com"
universe_domain = "googleapis.com"
```

## 🔧 Primo Setup - Pulizia Google Sheet

Se hai un Google Sheet già esistente rovinato, puliscilo:

1. **Decommentare** in `app.py` nella funzione `main()`:
```python
emergency_cleanup_sheet()  # USARE UNA VOLTA SOLA
```

2. **Eseguire l'app una volta** - pulirà automaticamente il sheet
3. **Ricommentare immediatamente** quella riga

## 📊 Struttura Dati Google Sheet

Il sistema crea automaticamente un Google Sheet con questi header fissi:

| Session_ID | Timestamp_Apertura | Timestamp_Inizio_Form | Timestamp_Step2 | Timestamp_Completamento | Dove_Trovato_QR | Fascia_Eta | Sesso | Provincia_Nascita | Titolo_Studio | Status_Finale | Completato | User_Agent | Data_Creazione |
|------------|-------------------|----------------------|-----------------|-------------------------|-----------------|------------|-------|-------------------|---------------|---------------|------------|------------|----------------|

## 🛡️ Sicurezza e Privacy

- **Email NON salvata** - richiesta solo per l'effetto demo
- **Dati anonimi** - utilizzati solo per scopi educativi
- **Cancellazione automatica** - configurabile per conformità GDPR
- **Tracking trasparente** - mostrato nella rivelazione finale

## 🎓 Utilizzo Educativo

### Scenari d'Uso
- **Corsi di cybersicurezza**
- **Formazione aziendale**
- **Sensibilizzazione pubblica**
- **Workshop universitari**

### Personalizzazione
- Modifica i testi in `app.py` per adattarli al tuo contesto
- Aggiungi il tuo logo nei CSS di `cybersecurity_utils.py`
- Personalizza i consigli di sicurezza nella sezione finale

## 🐛 Debug e Troubleshooting

### Modalità Debug
Abilita logs dettagliati settando:
```bash
export DEBUG_MODE=true
```

### Problemi Comuni

**Google Sheets non si connette:**
- Verifica che l'ID del sheet sia corretto
- Controlla che il service account abbia accesso al sheet
- Assicurati che le API siano abilitate

**App non traccia dati:**
- L'app funziona anche senza Google Sheets
- I dati sono sempre scaricabili come JSON
- Controlla la console del browser per errori

## 📝 Licenza

Progetto open source per scopi educativi. Utilizzare responsabilmente.

## 🤝 Contributi

I contributi sono benvenuti! Aprire una issue o una pull request.

## ⚠️ Disclaimer

Questo strumento è creato esclusivamente per scopi educativi e di sensibilizzazione sulla cybersicurezza. Gli autori non sono responsabili per usi impropri o illegali di questo software.

---

**Ricorda:** L'obiettivo è educare, non ingannare. Usa sempre questo strumento in contesti formativi autorizzati.
