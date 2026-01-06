import os
import sys
import re
from pathlib import Path
from difflib import SequenceMatcher

try:
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image
    import PyPDF2
except ImportError:
    print("Errore: librerie mancanti. Installa con:")
    print("pip install pytesseract pdf2image pillow PyPDF2")
    sys.exit(1)

def pulisci_testo_ocr(testo):
    """Rimuove rumore e artefatti comuni dall'OCR, ma mantiene contenuto tecnico."""
    if not testo:
        return ""
    
    # Rimuovi solo caratteri decorativi (mantieni simboli matematici)
    testo = re.sub(r'[•◦▪▫●○■□★☆♦♣♠♥]', '', testo)
    
    # Rimuovi linee con solo caratteri strani o troppo corte
    linee = testo.split('\n')
    linee_pulite = []
    
    for linea in linee:
        linea = linea.strip()
        
        # Salta solo linee veramente vuote o cortissime (meno di 3 caratteri)
        if len(linea) < 3:
            continue
        
        # Salta solo linee che sono SOLO numeri di pagina o date
        if re.match(r'^[\d\s\-/]+$', linea) and len(linea) < 15:
            continue
        
        # Salta linee con pattern tipici di header/footer ripetitivi
        if re.search(r'(Andrea Asperti.*Università.*Bologna.*DISI)', linea, re.IGNORECASE):
            continue
        
        # Salta linee che sono solo una singola parola ripetuta più volte
        parole = linea.split()
        if len(parole) > 2 and len(set(parole)) == 1:
            continue
        
        # Salta linee con troppi caratteri strani consecutivi (rumore OCR)
        if re.search(r'[^\w\s]{5,}', linea):
            continue
        
        # Salta linee che sembrano solo artefatti (es: "| | | |" o "---___")
        if re.match(r'^[\s\|\-_=~`]{3,}$', linea):
            continue
        
        linee_pulite.append(linea)
    
    testo = ' '.join(linee_pulite)
    
    # Normalizza spazi multipli
    testo = re.sub(r'\s+', ' ', testo)
    
    # Correggi spazi prima della punteggiatura
    testo = re.sub(r'\s+([.,;:!?])', r'\1', testo)
    
    # Aggiungi spazio dopo la punteggiatura se mancante
    testo = re.sub(r'([.,;:!?])([A-Za-zÀ-ÿ0-9])', r'\1 \2', testo)
    
    # Rimuovi spazi extra nelle parentesi
    testo = re.sub(r'\(\s+', '(', testo)
    testo = re.sub(r'\s+\)', ')', testo)
    
    # Pulisci caratteri Unicode strani ma mantieni quelli matematici comuni
    # Mantieni: α β γ δ ε θ λ μ π σ τ φ ω Σ Δ Φ Ω ± × ÷ ≈ ≠ ≤ ≥ ∞ ∂ ∇ ∫ √
    testo = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', testo)
    
    return testo.strip()

def estrai_testo_per_pagina_pdf(pdf_path):
    """Estrae il testo nativo PDF pagina per pagina."""
    print(f"  Estrazione testo nativo per pagina...")
    
    try:
        testi_per_pagina = []
        
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            for pagina_num in range(len(pdf_reader.pages)):
                pagina = pdf_reader.pages[pagina_num]
                testo = pagina.extract_text()
                
                testo_pulito = pulisci_testo_ocr(testo) if testo else ""
                testi_per_pagina.append(testo_pulito)
        
        return testi_per_pagina
    
    except Exception as e:
        print(f"  ⚠ Errore estrazione nativa: {e}")
        return []

def calcola_similarita(testo1, testo2):
    """Calcola la similarità tra due testi (0-1)."""
    if not testo1 or not testo2:
        return 0.0
    return SequenceMatcher(None, testo1.lower(), testo2.lower()).ratio()

def estrai_testo_ocr_per_pagina(pdf_path):
    """Applica OCR pagina per pagina."""
    print(f"  Applicazione OCR per pagina...")
    
    try:
        images = convert_from_path(pdf_path, dpi=300)
        
        testi_ocr = []
        for i, img in enumerate(images, 1):
            print(f"    Pagina {i}/{len(images)}")
            testo = pytesseract.image_to_string(img, lang='ita')
            testo_pulito = pulisci_testo_ocr(testo)
            testi_ocr.append(testo_pulito)
        
        return testi_ocr
    
    except Exception as e:
        print(f"  ✗ Errore OCR: {e}")
        return []

def is_frase_valida(frase):
    """Verifica se una frase è sensata e non rumore OCR - ottimizzata per contenuto STEM."""
    # Deve avere almeno 2 parole o simboli
    parole = frase.split()
    if len(parole) < 2:
        return False
    
    # Conta caratteri validi: alfanumerici + matematici comuni + punteggiatura
    caratteri_validi = sum(
        c.isalnum() or 
        c.isspace() or 
        c in '.,;:!?()+-*/=<>[]{}^_αβγδεθλμπστφωΣΔΦΩ±×÷≈≠≤≥∞∂∇∫√' 
        for c in frase
    )
    
    # Almeno 60% di caratteri validi
    if len(frase) > 0 and caratteri_validi / len(frase) < 0.6:
        return False
    
    # Evita solo vero rumore: troppi caratteri speciali ripetuti
    if re.search(r'([^\w\s])\1{4,}', frase):
        return False
    
    return True

def trova_frasi_uniche(testo_base, testo_ocr):
    """Trova frasi dall'OCR che non sono nel testo base."""
    if not testo_ocr:
        return []
    
    if not testo_base:
        # Anche se non c'è testo base, filtra solo il vero rumore
        frasi = re.split(r'[.!?]+', testo_ocr)
        return [f.strip() for f in frasi if len(f.strip()) > 15 and is_frase_valida(f.strip())]
    
    # Dividi in frasi
    frasi_base = set(re.split(r'[.!?]+', testo_base.lower()))
    frasi_ocr = re.split(r'[.!?]+', testo_ocr)
    
    frasi_nuove = []
    for frase in frasi_ocr:
        frase_pulita = frase.strip()
        
        # Filtri molto più permissivi per contenuto tecnico
        if not frase_pulita or len(frase_pulita) < 15:
            continue
        
        # Verifica che sia una frase valida (solo contro vero rumore)
        if not is_frase_valida(frase_pulita):
            continue
        
        # Verifica se questa frase è già presente nel testo base
        trovata = False
        for frase_base in frasi_base:
            if calcola_similarita(frase_pulita.lower(), frase_base.strip()) > 0.85:
                trovata = True
                break
        
        if not trovata:
            frasi_nuove.append(frase_pulita)
    
    return frasi_nuove

def unisci_testo_pagina(testo_nativo, testo_ocr, num_pagina):
    """Unisce testo nativo e OCR per una singola pagina."""
    
    # Se non c'è testo nativo, usa l'OCR
    if not testo_nativo or len(testo_nativo.strip()) < 10:
        if testo_ocr:
            print(f"      Pag {num_pagina}: solo OCR")
            return testo_ocr
        return ""
    
    # Se non c'è OCR, usa il nativo
    if not testo_ocr or len(testo_ocr.strip()) < 10:
        print(f"      Pag {num_pagina}: solo nativo")
        return testo_nativo
    
    # Calcola similarità
    similarita = calcola_similarita(testo_nativo, testo_ocr)
    
    # Se molto simili, usa solo il nativo
    if similarita > 0.8:
        print(f"      Pag {num_pagina}: nativo ({similarita:.0%} simile)")
        return testo_nativo
    
    # Trova frasi uniche dall'OCR
    frasi_nuove = trova_frasi_uniche(testo_nativo, testo_ocr)
    
    if frasi_nuove:
        testo_aggiuntivo = '. '.join(frasi_nuove)
        print(f"      Pag {num_pagina}: nativo + {len(frasi_nuove)} frasi OCR")
        return f"{testo_nativo}. {testo_aggiuntivo}"
    else:
        print(f"      Pag {num_pagina}: solo nativo (OCR duplicato)")
        return testo_nativo

def estrai_testo_completo_pdf(pdf_path):
    """Estrae testo combinando estrazione nativa e OCR pagina per pagina."""
    print(f"  Elaborazione: {pdf_path.name}")
    
    # Estrai testo nativo per ogni pagina
    testi_nativi = estrai_testo_per_pagina_pdf(pdf_path)
    
    # Applica OCR per ogni pagina
    testi_ocr = estrai_testo_ocr_per_pagina(pdf_path)
    
    # Assicurati che abbiano la stessa lunghezza
    num_pagine = max(len(testi_nativi), len(testi_ocr))
    
    # Riempi con stringhe vuote se necessario
    while len(testi_nativi) < num_pagine:
        testi_nativi.append("")
    while len(testi_ocr) < num_pagine:
        testi_ocr.append("")
    
    print(f"  Unione intelligente dei testi:")
    
    # Unisci pagina per pagina
    testi_finali = []
    for i in range(num_pagine):
        testo_unito = unisci_testo_pagina(testi_nativi[i], testi_ocr[i], i + 1)
        if testo_unito:
            testi_finali.append(testo_unito)
    
    # Unisci tutte le pagine
    return ' '.join(testi_finali)

def dividi_in_blocchi_con_frasi(testo, parole_per_blocco):
    """Divide il testo in blocchi rispettando i punti delle frasi."""
    frasi = re.split(r'([.!?]+)', testo)
    
    frasi_complete = []
    for i in range(0, len(frasi) - 1, 2):
        if i + 1 < len(frasi):
            frase = frasi[i] + frasi[i + 1]
            frasi_complete.append(frase.strip())
    
    if len(frasi) % 2 == 1 and frasi[-1].strip():
        frasi_complete.append(frasi[-1].strip())
    
    blocchi = []
    blocco_corrente = []
    conteggio_parole = 0
    
    for frase in frasi_complete:
        parole_frase = frase.split()
        num_parole = len(parole_frase)
        
        if conteggio_parole + num_parole > parole_per_blocco and blocco_corrente:
            blocchi.append(' '.join(blocco_corrente))
            blocco_corrente = [frase]
            conteggio_parole = num_parole
        else:
            blocco_corrente.append(frase)
            conteggio_parole += num_parole
    
    if blocco_corrente:
        blocchi.append(' '.join(blocco_corrente))
    
    return '\n\n'.join(blocchi)

def ordina_file_naturalmente(files):
    """Ordina i file in modo naturale (1, 2, 10 invece di 1, 10, 2)."""
    def chiave_naturale(path):
        parti = re.split(r'(\d+)', path.name.lower())
        return [int(p) if p.isdigit() else p for p in parti]
    
    return sorted(files, key=chiave_naturale)

def elabora_cartella(cartella, output_folder="output_txt"):
    """Elabora tutti i PDF in una cartella e crea file TXT separati."""
    cartella_path = Path(cartella)
    
    if not cartella_path.exists():
        print(f"Errore: la cartella '{cartella}' non esiste.")
        return
    
    pdf_files = list(cartella_path.glob("*.pdf"))
    pdf_files = ordina_file_naturalmente(pdf_files)
    
    if not pdf_files:
        print(f"Nessun file PDF trovato nella cartella '{cartella}'.")
        return
    
    output_path = cartella_path / output_folder
    output_path.mkdir(exist_ok=True)
    
    print(f"Trovati {len(pdf_files)} file PDF (ordinati).\n")
    
    while True:
        try:
            parole_input = input("Quante parole per blocco? (default 100): ").strip()
            parole_per_blocco = int(parole_input) if parole_input else 100
            
            if parole_per_blocco <= 0:
                print("Errore: inserisci un numero positivo.")
                continue
            
            print(f"\nElaborazione con blocchi di ~{parole_per_blocco} parole (rispettando i periodi).\n")
            break
        except ValueError:
            print("Errore: inserisci un numero valido.")
    
    statistiche = []
    
    for idx, pdf_file in enumerate(pdf_files, 1):
        print(f"\n[{idx}/{len(pdf_files)}] {pdf_file.name}")
        print("="*70)
        
        testo = estrai_testo_completo_pdf(pdf_file)
        
        if testo.strip():
            num_parole = len(testo.split())
            testo_formattato = dividi_in_blocchi_con_frasi(testo, parole_per_blocco)
            num_blocchi = len(testo_formattato.split('\n\n'))
            
            output_filename = pdf_file.stem + ".txt"
            output_filepath = output_path / output_filename
            
            with open(output_filepath, 'w', encoding='utf-8') as f:
                f.write(testo_formattato)
            
            statistiche.append({
                'nome': pdf_file.name,
                'parole': num_parole,
                'blocchi': num_blocchi
            })
            
            print(f"  ✓ Salvato: {output_filename} ({num_parole:,} parole, {num_blocchi} blocchi)")
        else:
            print(f"  ✗ Nessun testo estratto")
    
    print(f"\n{'='*70}")
    print(f"RIEPILOGO FINALE:")
    print(f"{'='*70}")
    
    totale_parole = sum(s['parole'] for s in statistiche)
    totale_blocchi = sum(s['blocchi'] for s in statistiche)
    
    for stat in statistiche:
        print(f"  {stat['nome']:<50} {stat['parole']:>8,} parole, {stat['blocchi']:>4} blocchi")
    
    print(f"{'='*70}")
    print(f"  {'TOTALE:':<50} {totale_parole:>8,} parole, {totale_blocchi:>4} blocchi")
    print(f"{'='*70}")
    print(f"\n✓ File salvati in: {output_path}")
    print(f"✓ {len(statistiche)} file TXT creati")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python main.py <cartella> [cartella_output]")
        print("\nEsempio: python main.py ./slide txt_output")
        sys.exit(1)
    
    cartella = sys.argv[1]
    output_folder = sys.argv[2] if len(sys.argv) > 2 else "output_txt"
    
    elabora_cartella(cartella, output_folder)