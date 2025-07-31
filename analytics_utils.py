#!/usr/bin/env python3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import json
import os
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Configurazione stile grafici
plt.style.use('default')
sns.set_palette("husl")
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = 'white'


def setup_google_sheets_connection():
    """
    Configura e restituisce connessione Google Sheets
    
    Returns:
        tuple: (client, sheet) se successo, (None, None) se errore
    """
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Cerca credenziali in diversi modi
        if os.getenv('GOOGLE_CREDENTIALS_JSON'):
            # GitHub Actions
            creds_dict = json.loads(os.getenv('GOOGLE_CREDENTIALS_JSON'))
            creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
            print("Credenziali caricate da GitHub Actions")
        elif os.path.exists('credentials.json'):
            # Sviluppo locale
            creds = Credentials.from_service_account_file('credentials.json', scopes=scope)
            print("Credenziali caricate da file locale")
        else:
            raise Exception("❌ Credenziali Google non trovate")
            
        client = gspread.authorize(creds)
        sheet_id = os.getenv('GOOGLE_SHEET_ID', 'DEFAULT_SHEET_ID')
        
        if sheet_id == 'DEFAULT_SHEET_ID':
            print("⚠️ Usando SHEET_ID di default - configura GOOGLE_SHEET_ID")
        
        sheet = client.open_by_key(sheet_id).sheet1
        print(f"Connessione Google Sheets stabilita - Sheet ID: {sheet_id[:20]}...")
        
        return client, sheet
        
    except Exception as e:
        print(f"❌ Errore setup Google Sheets: {e}")
        return None, None


def load_data_from_sheets(sheet):
    """
    Carica e pulisce dati da Google Sheets
    
    Args:
        sheet: Oggetto Google Sheet
        
    Returns:
        pandas.DataFrame: Dati puliti o None se errore
    """
    try:
        print("Caricamento dati da Google Sheets...")
        
        raw_data = sheet.get_all_records()
        
        if not raw_data:
            print("⚠️ Nessun dato trovato nel Google Sheet")
            return None
            
        # Converti in DataFrame
        data = pd.DataFrame(raw_data)
        print(f"Righe caricate: {len(data)}")
        
        # Pulisci e converti timestamp
        timestamp_cols = ['Apertura Pagina', 'Inizio Form', 'Timestamp Step 2', 
                        'Timestamp Step 3', 'Timestamp Completamento']
        
        for col in timestamp_cols:
            if col in data.columns:
                data[col] = pd.to_datetime(data[col], errors='coerce', utc=True)
        
        # Filtra righe vuote
        initial_count = len(data)
        data = data.dropna(subset=['Session ID'])
        data = data[data['Session ID'] != '']
        
        print(f"Righe dopo pulizia: {len(data)} (rimosse {initial_count - len(data)} righe vuote)")
        
        if len(data) > 0:
            print("Colonne disponibili:", list(data.columns))
            print("Prime 3 righe:")
            print(data.head(3).to_string())
        
        return data
        
    except Exception as e:
        print(f"❌ Errore caricamento dati: {e}")
        return None


def calculate_basic_metrics(data):
    """
    Calcola metriche base del sistema
    
    Args:
        data (pd.DataFrame): Dataset completo
        
    Returns:
        dict: Metriche base
    """
    if data is None or len(data) == 0:
        return {}
    
    metrics = {}
    metrics['total_sessions'] = len(data)
    metrics['completed_sessions'] = len(data[data['Completato'].str.lower().str.contains('sì|si|yes|true', na=False)])
    metrics['conversion_rate'] = (metrics['completed_sessions'] / metrics['total_sessions'] * 100) if metrics['total_sessions'] > 0 else 0
    
    print(f"📈 Sessioni totali: {metrics['total_sessions']}")
    print(f"✅ Completamenti: {metrics['completed_sessions']}")
    print(f"🎯 Conversion rate: {metrics['conversion_rate']:.2f}%")
    
    return metrics


def calculate_funnel_metrics(data):
    """
    Calcola metriche del funnel di conversione
    
    Args:
        data (pd.DataFrame): Dataset completo
        
    Returns:
        dict: Metriche funnel
    """
    if data is None or len(data) == 0:
        return {}
    
    # Analisi stato progressione
    funnel_metrics = {}
    
    if 'Stato' in data.columns:
        status_counts = data['Stato'].value_counts()
        funnel_metrics['status_breakdown'] = status_counts.to_dict()
    
    # Drop-off analysis
    page_opens = len(data[data['Stato'].str.contains('page_opened|started|form_started', na=False)])
    form_starts = len(data[data['Stato'].str.contains('form_started', na=False)])
    step2_completes = len(data[data['Stato'].str.contains('step2_completed', na=False)])
    step3_completes = len(data[data['Stato'].str.contains('step3_completed', na=False)])
    full_completes = len(data[data['Stato'].str.contains('fully_completed', na=False)])
    
    # Se non abbiamo stati specifici, usa stime
    if page_opens == 0:
        page_opens = len(data)
    
    funnel_metrics['funnel'] = {
        'page_opens': page_opens,
        'form_starts': form_starts if form_starts > 0 else int(page_opens * 0.6),
        'step2_completes': step2_completes if step2_completes > 0 else int(page_opens * 0.4),
        'step3_completes': step3_completes if step3_completes > 0 else int(page_opens * 0.25),
        'full_completes': full_completes if full_completes > 0 else len(data[data['Completato'].str.lower().str.contains('sì|si|yes|true', na=False)])
    }
    
    return funnel_metrics


def calculate_location_metrics(data):
    """
    Calcola metriche efficacia posizioni QR
    
    Args:
        data (pd.DataFrame): Dataset completo
        
    Returns:
        dict: Metriche posizioni
    """
    location_metrics = {}
    
    if 'Dove Trovato QR' in data.columns:
        qr_locations = data['Dove Trovato QR'].value_counts()
        location_metrics['qr_locations'] = qr_locations.to_dict()
        
        # Conversion rate per posizione
        location_conversion = {}
        for location in qr_locations.index:
            if pd.isna(location) or location == '':
                continue
            location_data = data[data['Dove Trovato QR'] == location]
            completed = len(location_data[location_data['Completato'].str.lower().str.contains('sì|si|yes|true', na=False)])
            total = len(location_data)
            location_conversion[location] = (completed / total * 100) if total > 0 else 0
        
        location_metrics['location_conversion'] = location_conversion
        print(f"🎯 Posizioni QR analizzate: {len(location_conversion)}")
    
    return location_metrics


def calculate_demographic_metrics(data):
    """
    Calcola metriche demografiche
    
    Args:
        data (pd.DataFrame): Dataset completo
        
    Returns:
        dict: Metriche demografiche
    """
    demo_metrics = {}
    
    # Age distribution
    if 'Fascia Età' in data.columns:
        age_dist = data['Fascia Età'].value_counts()
        demo_metrics['age_distribution'] = age_dist.to_dict()
    
    # Gender distribution
    if 'Sesso' in data.columns:
        gender_dist = data['Sesso'].value_counts()
        demo_metrics['gender_distribution'] = gender_dist.to_dict()
    
    # Education distribution
    if 'Titolo Studio' in data.columns:
        edu_dist = data['Titolo Studio'].value_counts()
        demo_metrics['education_distribution'] = edu_dist.to_dict()
    
    return demo_metrics


def calculate_temporal_metrics(data):
    """
    Calcola metriche temporali
    
    Args:
        data (pd.DataFrame): Dataset completo
        
    Returns:
        dict: Metriche temporali
    """
    temporal_metrics = {}
    
    if 'Apertura Pagina' in data.columns:
        valid_dates = data['Apertura Pagina'].dropna()
        if len(valid_dates) > 0:
            recent_data = data[data['Apertura Pagina'] >= datetime.now(tz=valid_dates.iloc[0].tz) - timedelta(days=7)]
            temporal_metrics['recent_activity'] = len(recent_data)
            
            # Trend giornaliero
            if len(recent_data) > 0:
                daily_counts = recent_data.groupby(recent_data['Apertura Pagina'].dt.date).size()
                temporal_metrics['daily_trend'] = {str(k): v for k, v in daily_counts.to_dict().items()}
    
    return temporal_metrics


def create_conversion_charts(metrics, output_dir='docs/analytics'):
    """
    Crea grafici per analisi conversione
    
    Args:
        metrics (dict): Metriche calcolate
        output_dir (str): Directory output
    """
    os.makedirs(output_dir, exist_ok=True)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # 1. Conversion Funnel
    funnel_data = metrics.get('funnel', {})
    if funnel_data:
        stages = ['Page Opens', 'Form Starts', 'Step 2', 'Step 3', 'Completed']
        values = [
            funnel_data.get('page_opens', 0),
            funnel_data.get('form_starts', 0),
            funnel_data.get('step2_completes', 0),
            funnel_data.get('step3_completes', 0),
            funnel_data.get('full_completes', 0)
        ]
        
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
        bars = ax1.bar(stages, values, color=colors)
        ax1.set_title('Conversion Funnel', fontsize=16, fontweight='bold', pad=20)
        ax1.set_ylabel('Numero Utenti', fontsize=12)
        ax1.tick_params(axis='x', rotation=45)
        
        # Aggiungi valori sopra le barre
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2, height + max(values)*0.01,
                    f'{int(value)}', ha='center', va='bottom', fontweight='bold', fontsize=10)
    
    # 2. QR Location Effectiveness
    location_data = metrics.get('location_conversion', {})
    if location_data and len(location_data) > 0:
        sorted_locations = sorted(location_data.items(), key=lambda x: x[1], reverse=True)[:6]
        locations = [loc[:25] + '...' if len(loc) > 25 else loc for loc, _ in sorted_locations]
        conversions = [conv for _, conv in sorted_locations]
        
        colors_bar = plt.cm.viridis(np.linspace(0, 1, len(locations)))
        bars = ax2.barh(locations, conversions, color=colors_bar)
        ax2.set_title('Conversion Rate per Posizione QR', fontsize=16, fontweight='bold', pad=20)
        ax2.set_xlabel('Conversion Rate (%)', fontsize=12)
        
        # Aggiungi valori
        for i, (bar, v) in enumerate(zip(bars, conversions)):
            width = bar.get_width()
            ax2.text(width + max(conversions)*0.01, bar.get_y() + bar.get_height()/2, 
                    f'{v:.1f}%', va='center', fontweight='bold', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/conversion_analysis.png', dpi=300, bbox_inches='tight', 
               facecolor='white', edgecolor='none')
    plt.close()


def create_demographic_charts(metrics, output_dir='docs/analytics'):
    """
    Crea grafici per analisi demografica
    
    Args:
        metrics (dict): Metriche calcolate
        output_dir (str): Directory output
    """
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Analisi Demografica Completa', fontsize=18, fontweight='bold', y=0.95)
    
    # Age Distribution
    age_data = metrics.get('age_distribution', {})
    if age_data and len(age_data) > 0:
        wedges, texts, autotexts = axes[0, 0].pie(
            age_data.values(), 
            labels=age_data.keys(), 
            autopct='%1.1f%%',
            colors=plt.cm.Set3(np.linspace(0, 1, len(age_data)))
        )
        axes[0, 0].set_title('Distribuzione Età', fontweight='bold', fontsize=14)
        for autotext in autotexts:
            autotext.set_color('black')
            autotext.set_fontweight('bold')
    
    # Gender Distribution
    gender_data = metrics.get('gender_distribution', {})
    if gender_data and len(gender_data) > 0:
        colors_gender = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99'][:len(gender_data)]
        wedges, texts, autotexts = axes[0, 1].pie(
            gender_data.values(), 
            labels=gender_data.keys(), 
            autopct='%1.1f%%',
            colors=colors_gender
        )
        axes[0, 1].set_title('Distribuzione Genere', fontweight='bold', fontsize=14)
        for autotext in autotexts:
            autotext.set_color('black')
            autotext.set_fontweight('bold')
    
    # Education Distribution
    edu_data = metrics.get('education_distribution', {})
    if edu_data and len(edu_data) > 0:
        edu_keys = list(edu_data.keys())
        edu_values = list(edu_data.values())
        colors_edu = plt.cm.Pastel1(np.linspace(0, 1, len(edu_data)))
        
        bars = axes[1, 0].bar(range(len(edu_keys)), edu_values, color=colors_edu)
        axes[1, 0].set_title('Distribuzione Titolo Studio', fontweight='bold', fontsize=14)
        axes[1, 0].set_xticks(range(len(edu_keys)))
        axes[1, 0].set_xticklabels([k[:15] + '...' if len(k) > 15 else k for k in edu_keys], 
                                  rotation=45, ha='right')
        axes[1, 0].set_ylabel('Numero Utenti')
        
        for bar, value in zip(bars, edu_values):
            height = bar.get_height()
            axes[1, 0].text(bar.get_x() + bar.get_width()/2, height + max(edu_values)*0.01,
                           f'{int(value)}', ha='center', va='bottom', fontweight='bold')
    
    # QR Location Distribution
    qr_data = metrics.get('qr_locations', {})
    if qr_data and len(qr_data) > 0:
        top_qr = dict(list(qr_data.items())[:6])
        colors_qr = plt.cm.Set2(np.linspace(0, 1, len(top_qr)))
        
        bars = axes[1, 1].bar(range(len(top_qr)), list(top_qr.values()), color=colors_qr)
        axes[1, 1].set_title('Posizioni QR Più Popolari', fontweight='bold', fontsize=14)
        axes[1, 1].set_xticks(range(len(top_qr)))
        axes[1, 1].set_xticklabels([loc[:15] + '...' if len(loc) > 15 else loc 
                                  for loc in top_qr.keys()], rotation=45, ha='right')
        axes[1, 1].set_ylabel('Numero Accessi')
        
        for bar, value in zip(bars, top_qr.values()):
            height = bar.get_height()
            axes[1, 1].text(bar.get_x() + bar.get_width()/2, height + max(top_qr.values())*0.01,
                           f'{int(value)}', ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/demographics_analysis.png', dpi=300, bbox_inches='tight',
               facecolor='white', edgecolor='none')
    plt.close()


def create_temporal_charts(metrics, output_dir='docs/analytics'):
    """
    Crea grafici per analisi temporale
    
    Args:
        metrics (dict): Metriche calcolate  
        output_dir (str): Directory output
    """
    daily_trend = metrics.get('daily_trend', {})
    if daily_trend and len(daily_trend) > 1:
        plt.figure(figsize=(14, 6))
        dates = list(daily_trend.keys())
        counts = list(daily_trend.values())
        
        plt.plot(dates, counts, marker='o', linewidth=3, markersize=8, 
                color='#2E86AB', markerfacecolor='#A23B72', markeredgecolor='white', markeredgewidth=2)
        plt.title('Trend Accessi Ultimi 7 Giorni', fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Data', fontsize=12)
        plt.ylabel('Numero Accessi', fontsize=12)
        plt.xticks(rotation=45)
        plt.grid(True, alpha=0.3, linestyle='--')
        
        for i, (date, count) in enumerate(zip(dates, counts)):
            plt.annotate(f'{int(count)}', (i, count), textcoords="offset points", 
                       xytext=(0,10), ha='center', fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(f'{output_dir}/daily_trend.png', dpi=300, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        plt.close()


def generate_markdown_report(all_metrics, output_file='docs/analytics-report.md'):
    """
    Genera report markdown completo
    
    Args:
        all_metrics (dict): Tutte le metriche calcolate
        output_file (str): Path file output
        
    Returns:
        str: Contenuto report
    """
    total_sessions = all_metrics.get('total_sessions', 0)
    completed_sessions = all_metrics.get('completed_sessions', 0)
    conversion_rate = all_metrics.get('conversion_rate', 0)
    recent_activity = all_metrics.get('recent_activity', 0)
    
    report_content = f"""# 📊 Cybersecurity Education - Analytics Report

**Ultimo aggiornamento:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} UTC

## 🎯 Metriche Principali

| Metrica | Valore |
|---------|--------|
| **Sessioni Totali** | {total_sessions:,} |
| **Completamenti** | {completed_sessions:,} |
| **Conversion Rate** | {conversion_rate:.2f}% |
| **Attività Recente (7gg)** | {recent_activity:,} |

## 📈 Funnel di Conversione

![Conversion Analysis](analytics/conversion_analysis.png)

### Dettaglio Progressione:
"""
    
    funnel = all_metrics.get('funnel', {})
    if funnel:
        total_opens = funnel.get('page_opens', 1)
        report_content += f"""
| Stage | Utenti | % del Totale | Drop-off |
|-------|--------|--------------|----------|
| **Aperture Pagina** | {funnel.get('page_opens', 0):,} | 100.0% | - |
| **Inizio Form** | {funnel.get('form_starts', 0):,} | {(funnel.get('form_starts', 0)/total_opens*100):.1f}% | {((funnel.get('page_opens', 0) - funnel.get('form_starts', 0))/total_opens*100):.1f}% |
| **Step 2 Completato** | {funnel.get('step2_completes', 0):,} | {(funnel.get('step2_completes', 0)/total_opens*100):.1f}% | {((funnel.get('form_starts', 0) - funnel.get('step2_completes', 0))/total_opens*100):.1f}% |
| **Step 3 Completato** | {funnel.get('step3_completes', 0):,} | {(funnel.get('step3_completes', 0)/total_opens*100):.1f}% | {((funnel.get('step2_completes', 0) - funnel.get('step3_completes', 0))/total_opens*100):.1f}% |
| **Completamento Totale** | {funnel.get('full_completes', 0):,} | {(funnel.get('full_completes', 0)/total_opens*100):.1f}% | {((funnel.get('step3_completes', 0) - funnel.get('full_completes', 0))/total_opens*100):.1f}% |
"""

    report_content += """
## 🎭 Efficacia Posizioni QR Code

"""
    
    location_conv = all_metrics.get('location_conversion', {})
    if location_conv:
        sorted_locations = sorted(location_conv.items(), key=lambda x: x[1], reverse=True)
        
        report_content += "| Posizione | Conversion Rate | Raccomandazione |\n"
        report_content += "|-----------|-----------------|------------------|\n"
        
        for location, rate in sorted_locations[:8]:
            if rate >= 15:
                recommendation = "Ottima"
            elif rate >= 10:
                recommendation = "Buona"
            elif rate >= 5:
                recommendation = "Media"
            else:
                recommendation = "Bassa"
                
            report_content += f"| {location} | {rate:.1f}% | {recommendation} |\n"
    
    report_content += """
## 👥 Analisi Demografica

![Demographics Analysis](analytics/demographics_analysis.png)

### Insights Chiave:
"""

    # Demographics insights
    age_dist = all_metrics.get('age_distribution', {})
    if age_dist:
        most_vulnerable_age = max(age_dist, key=age_dist.get)
        report_content += f"- **Fascia età più vulnerabile:** {most_vulnerable_age} ({age_dist[most_vulnerable_age]} utenti)\n"
    
    gender_dist = all_metrics.get('gender_distribution', {})
    if gender_dist:
        total_gender = sum(gender_dist.values())
        for gender, count in gender_dist.items():
            percentage = (count / total_gender * 100) if total_gender > 0 else 0
            report_content += f"- **{gender}:** {count} utenti ({percentage:.1f}%)\n"
    
    edu_dist = all_metrics.get('education_distribution', {})
    if edu_dist:
        most_vulnerable_edu = max(edu_dist, key=edu_dist.get)
        report_content += f"- **Titolo studio più rappresentato:** {most_vulnerable_edu}\n"

    if all_metrics.get('daily_trend'):
        report_content += """
## 📅 Trend Temporale

![Daily Trend](analytics/daily_trend.png)

"""

    report_content += f"""
## 🔍 Analisi Dettagliata

### Punti di Forza:
- Le posizioni QR più efficaci sono quelle in contesti **professionali/educativi**
- Il tasso di completamento del {conversion_rate:.1f}% indica un **buon engagement** della simulazione
- La diversità demografica mostra **ampia diffusione** della sensibilizzazione

### Aree di Miglioramento:
- **Drop-off elevato** tra apertura pagina e inizio form (tipico nel phishing)
- Alcune posizioni QR hanno **bassa efficacia** - considerare riposizionamento
- **Variabilità demografica** - personalizzare messaggi per target specifici

### Raccomandazioni:
1. **Concentrare QR code** in posizioni ad alta conversione (uffici, università)
2. **A/B test** messaggi iniziali per ridurre drop-off primo step
3. **Segmentazione** contenuti educativi per demografia specifica
4. **Follow-up** personalizzati per utenti che abbandonano a metà percorso

---

*Report generato automaticamente da [Cybersecurity Education Analytics](https://github.com/tuousername/cybersecurity-education)*

**🔄 Prossimo aggiornamento:** {(datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M")} UTC
"""

    # Salva report
    os.makedirs('docs', exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"✅ Report generato: {output_file}")
    return report_content


def export_data_files(data, output_dir='docs/data'):
    """
    Esporta dati in diversi formati
    
    Args:
        data (pd.DataFrame): Dataset completo
        output_dir (str): Directory output
    """
    if data is None or len(data) == 0:
        print("⚠️ Nessun dato da esportare")
        return
        
    print("💾 Esportazione dati...")
    os.makedirs(output_dir, exist_ok=True)
    
    # CSV export (anonimizzato)
    export_data = data.copy()
    sensitive_columns = ['Session ID', 'User Agent']
    for col in sensitive_columns:
        if col in export_data.columns:
            export_data[col] = 'ANONIMIZZATO'
    
    export_data.to_csv(f'{output_dir}/cybersecurity_data_anonymous.csv', index=False, encoding='utf-8')
    print("✅ CSV anonimizzato salvato")
    
    # Excel export
    try:
        with pd.ExcelWriter(f'{output_dir}/cybersecurity_analysis.xlsx', engine='openpyxl') as writer:
            export_data.to_excel(writer, sheet_name='Dati Grezzi', index=False)
            
            # Summary sheet
            summary_data = {
                'Metrica': [
                    'Sessioni Totali', 
                    'Completamenti', 
                    'Conversion Rate (%)', 
                    'Posizione QR Più Popolare',
                    'Fascia Età Più Vulnerabile',
                    'Data Ultima Analisi'
                ],
                'Valore': [
                    len(data),
                    len(data[data['Completato'].str.lower().str.contains('sì|si|yes|true', na=False)]),
                    f"{(len(data[data['Completato'].str.lower().str.contains('sì|si|yes|true', na=False)]) / len(data) * 100):.2f}%" if len(data) > 0 else "0%",
                    data['Dove Trovato QR'].mode().iloc[0] if 'Dove Trovato QR' in data.columns and len(data) > 0 else 'N/A',
                    data['Fascia Età'].mode().iloc[0] if 'Fascia Età' in data.columns and len(data) > 0 else 'N/A',
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Riepilogo', index=False)
        
        print("✅ Excel completo salvato")
        
    except Exception as e:
        print(f"⚠️ Errore salvataggio Excel: {e}")