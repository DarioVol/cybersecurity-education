#!/usr/bin/env python3
import streamlit as st
from datetime import datetime
from cybersecurity_utils import (
    setup_google_sheets,
    initialize_session_state,
    track_page_opening,
    create_progress_bar,
    validate_step_data,
    save_step_data,
    get_province_list,
    get_qr_location_options,
    get_age_ranges,
    get_education_levels,
    get_gender_options,
    create_data_download,
    display_collected_data,
    reset_session,
    load_custom_css
    # emergency_cleanup_sheet  # DECOMMENTARE PER PULIZIA UNA-TANTUM DEL SHEET
)


def configure_app():
    """Configurazione iniziale dell'applicazione Streamlit"""
    st.set_page_config(
        page_title="Promozione Speciale",
        page_icon="🎯",
        layout="centered",
        initial_sidebar_state="collapsed"
    )
    
    # Carica CSS personalizzato
    load_custom_css()


def step_1_welcome():
    """Step 1: Schermata di benvenuto e consenso"""
    st.markdown("#Hai la possibilità di vincere un buono Amazon.")
    
    #st.success("Hai la possibilità di vincere un buono Amazon.")
    st.info("Completa il questionario di 1 minuto per vedere se hai vinto.")
    
    # Campo dove è stato trovato il QR code
    st.markdown("### 📱 Dove hai trovato questo QR Code?")
    qr_location = st.selectbox(
        "Seleziona dove hai scansionato il codice:", 
        get_qr_location_options()
    )

    st.info("""
    **Privacy:** I tuoi dati saranno trattati in conformità al GDPR per finalità promozionali e di marketing. Potrai richiedere la cancellazione in qualsiasi momento.
    """)

    # Checkbox consenso
    consent = st.checkbox("✅ Accetto il trattamento dei dati personali per partecipare all'estrazione di un buono sconto")
    
    # Progress bar
    create_progress_bar(1)
    
    # Bottone continua
    if st.button("Inizia Ora", type="primary", use_container_width=True):
        # Valida dati
        is_valid, error_msg = validate_step_data(1, qr_location=qr_location, consent=consent)
        
        if is_valid:
            # Salva dati step 1
            sheet = setup_google_sheets()
            save_step_data(1, sheet, qr_location=qr_location)
            
            # Vai al prossimo step
            st.session_state.step = 2
            st.rerun()
        else:
            st.error(error_msg)


def step_2_personal_info():
    """Step 2: Informazioni personali"""
    st.markdown("## 📋 Informazioni Personali")
    
    col1, col2 = st.columns(2)
    
    with col1:
        age_range = st.selectbox("Fascia d'età:", get_age_ranges())
        
    with col2:
        gender = st.selectbox("Sesso:", get_gender_options())
    
    birth_province = st.selectbox("Provincia di nascita:", get_province_list())

    education = st.selectbox("Titolo di studio:", get_education_levels())
    
    # Progress bar
    create_progress_bar(2)
    
    # Bottone continua
    if st.button("Continua", type="primary", use_container_width=True):
        # Valida dati
        is_valid, error_msg = validate_step_data(
            2, age_range=age_range, gender=gender, birth_province=birth_province, education=education
        )
        
        if is_valid:
            # Salva dati step 2
            sheet = setup_google_sheets()
            save_step_data(2, sheet, age_range=age_range, gender=gender, 
                           birth_province=birth_province, education=education)
            
            # Vai al prossimo step
            st.session_state.step = 3
            st.rerun()
        else:
            st.error(error_msg)


def step_3_final_confirmation():
    """Step 3: Conferma finale"""
    st.markdown("## 💳 Inserisci la tua mail per vedere se hai vinto il buono Amazon")
    
    #st.info("📧 Inserisci la tua email per ricevere l'eventuale buono")
    
    # Email richiesta ma NON salvata (solo per l'effetto della demo)
    email_input = st.text_input("Email:")
    
    #st.success("Prosegui per vedere se hai vinto.")
    
    # Progress bar
    create_progress_bar(3)
    
    # Bottone finale
    if st.button("Continua", type="primary", use_container_width=True):
        # Valida email
        is_valid, error_msg = validate_step_data(3, email_input=email_input)
        
        if is_valid:
            # Salva completamento finale (email NON salvata)
            sheet = setup_google_sheets()
            save_step_data(3, sheet)
            
            # Vai al disclaimer
            st.session_state.step = 4
            st.rerun()
        else:
            st.error(error_msg)


def step_4_educational_disclaimer():
    """Step 4: Disclaimer educativo finale"""
    st.markdown('<div class="warning-box">', unsafe_allow_html=True)
    st.markdown("# ⚠️ ATTENZIONE! SEI STATO TRUFFATO!")
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.error("**Questo era un esempio di SOCIAL ENGINEERING e PHISHING.**")
    st.warning("Non esisteva nessuna promozione. Hai appena fornito i tuoi dati personali a sconosciuti.")
    
    # Mostra dati raccolti
    st.markdown('<div class="data-collected">', unsafe_allow_html=True)
    st.markdown("### 📊 Dati che hai condiviso:")
    
    data_df = display_collected_data(st.session_state.user_data)
    st.dataframe(data_df, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.warning("""
    **🚨 NOTA IMPORTANTE:** 
    Ti abbiamo chiesto anche l'email! In una truffa reale, avresti fornito 
    anche quel dato sensibile. Fortunatamente qui non l'abbiamo salvata, 
    ma i criminali l'avrebbero usata per attacchi mirati e per campagne pubblicitarie moleste e non richieste.
    
    **🎯 Dato Cruciale:** Anche sapere DOVE hai trovato il QR code è prezioso
    per i truffatori - gli dice dove piazzare meglio le loro truffe!
    
    **📱 Tracking Nascosto:** Il tuo accesso è stato tracciato dal momento dell'apertura della pagina, PRIMA ancora che iniziassi il questionario!
    """)
    
    # Consigli di sicurezza
    st.markdown("### 🛡️ Come proteggersi:")
    st.markdown("""
    - **NON scansionare QR code sospetti** trovati in luoghi pubblici non sicuri
    - **Diffida dei QR su** mezzi pubblici, cassette postali, macchine random
    - **Verifica sempre la fonte** delle offerte troppo belle per essere vere
    - **Anche solo aprire** un link sospetto può tracciare informazioni su di te
    - **Controlla sempre l'URL** del sito (https, dominio corretto)
    - **Diffida delle urgenze** ("offerta valida solo oggi!")
    - **QR code legittimi** sono di solito in contesti ufficiali
    - **Chiudi immediatamente** siti sospetti, anche se sembrano professionali
    - **Educa** familiari e colleghi su queste tecniche
    """)
    
    st.error("**Ricorda:** i cybercriminali utilizzano proprio queste tecniche per rubare identità, soldi e dati personali!")
    
    st.info("""
    📊 **Dati tracciati in questo progetto:**
    - **Aperture pagina:** anche chi apre e basta viene tracciato con ID unico
    - **Informazioni tecniche:** browser, timestamp di apertura
    - **Punto di abbandono:** dove esci se non completi
    - **Dati demografici:** solo se procedi nel questionario
    - **Email richiesta ma NON salvata** (solo per l'effetto demo)
    - Dati anonimi utilizzati per statistiche
    
    **🎯 Lezione fondamentale:** Anche solo APRIRE un link sospetto può essere pericoloso!
    """)

    st.markdown("**Progetto Educativo di Cybersicurezza** - Utilizzato esclusivamente per scopi didattici")
    
    # Download dei dati
    json_data = create_data_download(st.session_state.user_data)
    st.download_button(
        label="📥 Scarica Report Dati Raccolti",
        data=json_data,
        file_name=f"cybersecurity_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json"
    )
    
    # Bottone ricomincia
    if st.button("🔄 Ricomincia Demo", use_container_width=True):
        reset_session()
        st.rerun()


def main():
    """Funzione principale dell'applicazione"""
    # Configurazione app
    configure_app()
    
    # Inizializzazione session state
    initialize_session_state()
    
    # Tracking apertura pagina con FILTRO ANTI-HEALTH CHECK FINALE
    # (Il debug finale è integrato nella funzione se DEBUG_MODE=true)
    track_page_opening()
    
    # DECOMMENTARE LA RIGA SOTTO PER PULIZIA UNA-TANTUM DEL GOOGLE SHEET ROVINATO
    # emergency_cleanup_sheet()  # USARE UNA VOLTA SOLA, POI RICOMMENTARE
    
    # Router per i diversi step
    if st.session_state.step == 1:
        step_1_welcome()
    elif st.session_state.step == 2:
        step_2_personal_info()
    elif st.session_state.step == 3:
        step_3_final_confirmation()
    elif st.session_state.step == 4:
        step_4_educational_disclaimer()
    
    # Footer informativo
    st.markdown("---")
    #st.markdown("**Progetto Educativo di Cybersicurezza** - Utilizzato esclusivamente per scopi didattici")


if __name__ == "__main__":
    main()
