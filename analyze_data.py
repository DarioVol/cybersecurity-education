#!/usr/bin/env python3
import sys
from datetime import datetime
from analytics_utils import (
    setup_google_sheets_connection,
    load_data_from_sheets,
    calculate_basic_metrics,
    calculate_funnel_metrics,
    calculate_location_metrics,
    calculate_demographic_metrics,
    calculate_temporal_metrics,
    create_conversion_charts,
    create_demographic_charts,
    create_temporal_charts,
    generate_markdown_report,
    export_data_files
)


def main():
    """
    Main function - orchestrates the complete analytics process
    """
    print("🛡️ CYBERSECURITY EDUCATION - DATA ANALYZER")
    print("=" * 60)
    print(f"🚀 Avvio analisi dati - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    try:
        # Step 1: Setup connessione Google Sheets
        print("\n📡 STEP 1: Configurazione connessione Google Sheets")
        client, sheet = setup_google_sheets_connection()
        
        if not sheet:
            print("❌ Impossibile stabilire connessione - terminazione")
            return False
        
        # Step 2: Caricamento dati
        print("\n📥 STEP 2: Caricamento e pulizia dati")
        data = load_data_from_sheets(sheet)
        
        if data is None or len(data) == 0:
            print("❌ Nessun dato valido trovato - terminazione")
            return False
        
        print(f"✅ Dataset caricato: {len(data)} record validi")
        
        # Step 3: Calcolo metriche
        print("\n📊 STEP 3: Calcolo metriche analytics")
        
        # Calcola tutte le metriche
        basic_metrics = calculate_basic_metrics(data)
        funnel_metrics = calculate_funnel_metrics(data)
        location_metrics = calculate_location_metrics(data)
        demographic_metrics = calculate_demographic_metrics(data)
        temporal_metrics = calculate_temporal_metrics(data)
        
        # Combina tutte le metriche
        all_metrics = {
            **basic_metrics,
            **funnel_metrics,
            **location_metrics,
            **demographic_metrics,
            **temporal_metrics
        }
        
        print(f"✅ Metriche calcolate: {len(all_metrics)} categorie")
        
        # Step 4: Generazione visualizzazioni
        print("\n📈 STEP 4: Generazione grafici e visualizzazioni")
        
        create_conversion_charts(all_metrics)
        print("✅ Grafici conversione generati")
        
        create_demographic_charts(all_metrics)
        print("✅ Grafici demografici generati")
        
        create_temporal_charts(all_metrics)
        print("✅ Grafici temporali generati")
        
        # Step 5: Generazione report
        print("\n📝 STEP 5: Generazione report markdown")
        
        report_content = generate_markdown_report(all_metrics)
        print("✅ Report markdown generato")
        
        # Step 6: Export dati
        print("\n💾 STEP 6: Export dati in formati multipli")
        
        export_data_files(data)
        print("✅ Export dati completato")
        
        # Step 7: Riepilogo finale
        print("\n" + "=" * 60)
        print("🎉 ANALISI COMPLETATA CON SUCCESSO!")
        print("=" * 60)
        print("📁 File generati:")
        print("   📝 docs/analytics-report.md - Report principale")
        print("   📊 docs/analytics/*.png - Grafici analytics")
        print("   💾 docs/data/*.xlsx - Export Excel")
        print("   📄 docs/data/*.csv - CSV anonimizzato")
        print("=" * 60)
        print(f"📈 Metriche principali:")
        print(f"   • Sessioni totali: {all_metrics.get('total_sessions', 0):,}")
        print(f"   • Completamenti: {all_metrics.get('completed_sessions', 0):,}")
        print(f"   • Conversion Rate: {all_metrics.get('conversion_rate', 0):.2f}%")
        print(f"   • Posizioni QR monitorate: {len(all_metrics.get('location_conversion', {}))}")
        print("=" * 60)
        print("🌐 Visualizza report su:")
        print("   https://github.com/TUOUSERNAME/REPOSITORY/blob/main/docs/analytics-report.md")
        print("=" * 60)
        
        return True
        
    except KeyboardInterrupt:
        print("\n⚠️ Analisi interrotta dall'utente")
        return False
        
    except Exception as e:
        print(f"\n❌ ERRORE CRITICO DURANTE L'ANALISI:")
        print(f"   {str(e)}")
        print("\n🔧 Suggerimenti per risoluzione:")
        print("   • Verifica credenziali Google Sheets")
        print("   • Controlla ID del Google Sheet")
        print("   • Assicurati connessione internet attiva")
        print("   • Verifica presenza dati nel foglio")
        print("   • Controlla permessi service account")
        
        # Debug info per sviluppatori
        import traceback
        print(f"\n🐛 Stack trace completo:")
        traceback.print_exc()
        
        return False


if __name__ == "__main__":
    print("🔧 Modalità: Esecuzione diretta")
    success = main()
    
    if success:
        print("\n✨ Processo completato con successo!")
        sys.exit(0)
    else:
        print("\n💥 Processo fallito - controlla log per dettagli")
        sys.exit(1)