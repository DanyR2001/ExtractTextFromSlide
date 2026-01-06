# PDF Text Extraction with Hybrid OCR

Python script for intelligent text extraction from PDF documents using a hybrid approach combining native PDF text extraction and Optical Character Recognition (OCR). Optimized for academic documents, lecture slides, and technical materials containing mathematical notation and scientific symbols.

## Overview

This tool processes PDF files using a dual-method approach:

1. **Native Extraction**: Extracts selectable text directly from PDF structure using PyPDF2
2. **OCR Processing**: Converts pages to high-resolution images and applies Tesseract OCR
3. **Intelligent Merging**: Compares results page-by-page and selects or combines output based on quality metrics

The system preserves technical content including mathematical formulas, variables, and scientific notation while removing common OCR artifacts and noise.

## Features

- Batch processing of all PDFs in a directory
- Page-by-page processing with adaptive method selection
- Automatic text cleaning: removes repetitive headers/footers, page numbers, OCR artifacts
- Preservation of mathematical symbols and scientific notation (Greek letters, operators, etc.)
- Configurable text chunking respecting sentence boundaries
- Natural file sorting (1, 2, 10 instead of 1, 10, 2)
- Individual output files per PDF with detailed statistics

## System Requirements

### Required Software

- Python 3.7+
- Tesseract OCR 4.0+
- Poppler utilities (for pdf2image on Windows)

### Tesseract Installation

#### Windows
1. Download installer from https://github.com/UB-Mannheim/tesseract/wiki
2. Install and add to system PATH
3. If not detected automatically, specify path in code:
```python
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

#### macOS
```bash
brew install tesseract
brew install tesseract-lang
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
sudo apt-get install tesseract-ocr-ita  # for Italian language support
```

### Poppler Installation (Windows only)

Download from https://github.com/oschwartz10612/poppler-windows/releases/ and add the `bin` directory to system PATH.

## Python Dependencies

Install required packages:

```bash
pip install pytesseract pdf2image pillow PyPDF2
```

Or use requirements.txt:

```bash
pip install -r requirements.txt
```

### requirements.txt
```
pytesseract>=0.3.10
pdf2image>=1.16.0
Pillow>=9.0.0
PyPDF2>=3.0.0
```

## Installation

```bash
git clone <repository-url>
cd pdf-text-extractor
pip install -r requirements.txt
```

Verify Tesseract installation:
```bash
tesseract --version
```

## Usage

### Basic Syntax

```bash
python main.py <input_folder> [output_folder]
```

### Arguments

- `input_folder` (required): Path to directory containing PDF files
- `output_folder` (optional): Name of output subdirectory (default: "output_txt")

### Examples

Process PDFs in current directory:
```bash
python main.py ./slides
```

Specify custom output folder:
```bash
python main.py ./documents ./extracted_text
```

### Interactive Configuration

When executed, the script prompts for output format:
```
Modalità output:
  1) Slide separate (--- SLIDE N ---)
  2) Blocchi di parole
Scegli (1/2, default 1):
```

#### Mode 1: Slide-by-Slide (Default)
Each PDF page becomes a separate section with header:
```
--- SLIDE 1 ---
Content of first page...

--- SLIDE 2 ---
Content of second page...
```
Sections are separated by two newlines. Best for preserving document structure and reviewing individual slides.

#### Mode 2: Word Chunks
Prompts for chunk size:
```
Quante parole per blocco? (default 100):
```
- Press Enter for default (100 words per chunk)
- Or specify custom size (e.g., 50, 200, 500)
- All text is merged and divided into chunks of approximately N words
- Chunks respect sentence boundaries and never split mid-sentence
- Chunks are separated by five newlines (\n\n\n\n\n)

Best for continuous reading or feeding to language models with context window constraints.

## Output Structure

```
input_folder/
├── document1.pdf
├── document2.pdf
└── output_txt/
    ├── document1.txt
    └── document2.txt
```

### Mode 1: Slide-by-Slide Output
Each output file contains:
```
--- SLIDE 1 ---
First page content with native text + OCR additions

--- SLIDE 2 ---
Second page content with native text + OCR additions
```
- Each slide header indicates the page number
- Sections separated by two newlines
- OCR is applied page-by-page and merged intelligently with native text
- Preserves document structure for easy navigation

### Mode 2: Word Chunks Output
Each output file contains:
```
First chunk with approximately N words from merged pages...




Second chunk with approximately N words...
```
- All pages merged into continuous text
- Divided into chunks of approximately N words (configurable)
- Chunks separated by five newlines (\n\n\n\n\n)
- Complete sentences only (no mid-sentence breaks)
- OCR applied page-by-page before merging

## Algorithm Details

### Processing Pipeline

1. **Native Extraction** (PyPDF2)
   - Extracts text layer from PDF
   - Page-by-page processing
   - Fast but may miss scanned content

2. **OCR Processing** (Tesseract)
   - Converts each page to 300 DPI image
   - Applies OCR with Italian language model
   - Processed page-by-page in parallel with native extraction
   - Slower but captures all visible text

3. **Intelligent Merging (Per Page)**
   ```
   For each page:
     if native_text is empty:
       use OCR text
     else if OCR_text is empty:
       use native text
     else if similarity > 80%:
       use native text (more reliable)
     else:
       merge native + unique OCR sentences
   ```
   
   This process happens **page-by-page** before any chunking or formatting, ensuring maximum text recovery from each individual page.

4. **Text Cleaning**
   - Remove decorative Unicode characters
   - Filter page numbers and dates
   - Eliminate repetitive headers/footers
   - Normalize whitespace and punctuation
   - Preserve mathematical symbols (α β γ δ ε θ λ μ π σ τ φ ω Σ Δ Φ Ω ± × ÷ ≈ ≠ ≤ ≥ ∞ ∂ ∇ ∫ √)

5. **Output Formatting** (User Choice)
   - **Mode 1 (Slide)**: Keep pages separate with headers
   - **Mode 2 (Chunks)**: Merge all pages, then split into word-count chunks respecting sentence boundaries

### Similarity Calculation

Uses SequenceMatcher from difflib to compute text similarity ratio (0.0 to 1.0). Threshold of 0.8 (80% similarity) determines whether to use native text alone or merge with OCR.

## Configuration Options

### OCR Language

Modify line 125 in main.py:
```python
# Default: Italian
testo = pytesseract.image_to_string(img, lang='ita')

# English
testo = pytesseract.image_to_string(img, lang='eng')

# Multiple languages
testo = pytesseract.image_to_string(img, lang='ita+eng')
```

### OCR Resolution

Modify line 117 in main.py:
```python
# Default: 300 DPI (balanced)
images = convert_from_path(pdf_path, dpi=300)

# High quality: 600 DPI (slower)
images = convert_from_path(pdf_path, dpi=600)

# Fast: 150 DPI (lower quality)
images = convert_from_path(pdf_path, dpi=150)
```

### Similarity Threshold

Modify line 202 in main.py:
```python
# Default: 80% similarity
if similarita > 0.8:

# More permissive (use more OCR): 70%
if similarita > 0.7:

# More restrictive (use less OCR): 90%
if similarita > 0.9:
```

## Performance Benchmarks

Tested on Intel i5 CPU, 8GB RAM:

| PDF Type | Pages | Processing Time | Output Quality |
|----------|-------|----------------|----------------|
| Native text only | 50 | 5-10 seconds | Excellent |
| Scanned images | 50 | 2-5 minutes | Good |
| Mixed (text + images) | 50 | 1-3 minutes | Excellent |

OCR is CPU-intensive. Processing time scales linearly with page count and DPI setting.

## Troubleshooting

### Tesseract not found

**Error**: `TesseractNotFoundError`

**Solution**: Verify installation and PATH configuration
```bash
which tesseract  # macOS/Linux
where tesseract  # Windows
```

Or specify path explicitly in code (see Tesseract Installation section).

### pdf2image requires poppler

**Error**: `PDFInfoNotInstalledError`

**Windows Solution**: 
1. Download poppler from https://github.com/oschwartz10612/poppler-windows/releases/
2. Extract and add `bin` directory to PATH
3. Or specify path in code:
```python
images = convert_from_path(pdf_path, dpi=300, poppler_path=r'C:\path\to\poppler\bin')
```

**macOS/Linux Solution**:
```bash
brew install poppler  # macOS
sudo apt-get install poppler-utils  # Linux
```

### Slow processing

- Reduce DPI to 150-200
- Process fewer files per batch
- Use faster CPU or parallel processing

### Incomplete text extraction

- Increase DPI to 400-600
- Verify Tesseract language support
- Check PDF is not password-protected
- Ensure PDF contains actual text/images (not blank pages)

### Excessive noise in output

Adjust filtering parameters in `pulisci_testo_ocr()` and `is_frase_valida()` functions for more restrictive cleaning.

## Architecture

### Core Functions

- `pulisci_testo_ocr()`: Text cleaning and normalization
- `estrai_testo_per_pagina_pdf()`: Native PDF text extraction (page-by-page)
- `estrai_testo_ocr_per_pagina()`: OCR processing (page-by-page)
- `calcola_similarita()`: Sequence matching for similarity scoring
- `unisci_testo_pagina()`: Intelligent text merging logic (per page)
- `is_frase_valida()`: Sentence validation for STEM content
- `trova_frasi_uniche()`: Unique sentence detection
- `dividi_per_slide()`: Format text with slide headers
- `dividi_in_blocchi_con_frasi()`: Sentence-aware chunking by word count
- `elabora_cartella()`: Main orchestration and batch processing

### Data Flow

```
PDF Files → Native Extraction (page-by-page) → Clean Text per Page
         → OCR Processing (page-by-page)    → Clean Text per Page
                                             → Similarity Comparison per Page
                                             → Intelligent Merge per Page
                                             → User Choice:
                                                ├─ Mode 1: Add Slide Headers
                                                └─ Mode 2: Merge All + Chunk by Words
                                             → Output TXT Files
```

The key difference from traditional approaches: **OCR and merging happen at the page level**, ensuring each page gets optimal text extraction before any formatting decisions are made.

## Use Cases

- Academic lecture slides with mathematical notation
- Scanned documents and books
- Mixed-content PDFs (text + images)
- Technical presentations with diagrams
- Multilingual educational materials
- Historical documents requiring digitization

## Limitations

- OCR accuracy depends on image quality and font clarity
- Mathematical formulas may require manual verification
- Complex table layouts may not preserve structure
- Right-to-left languages require additional configuration
- Performance scales linearly with document size

## Contributing

Contributions welcome. Please follow standard Git workflow:

1. Fork repository
2. Create feature branch (`git checkout -b feature/improvement`)
3. Commit changes (`git commit -m 'Add improvement'`)
4. Push to branch (`git push origin feature/improvement`)
5. Open Pull Request

## License

MIT License. See LICENSE file for details.

## Dependencies and Credits

- **Tesseract OCR**: Google's open-source OCR engine
- **PyPDF2**: PDF manipulation library
- **pdf2image**: PDF to PIL Image conversion wrapper
- **Pillow**: Python Imaging Library fork
- **pytesseract**: Python wrapper for Tesseract

## Technical Specifications

- **Language**: Python 3.7+
- **Architecture**: Pipeline-based processing with modular functions
- **Encoding**: UTF-8 for all input/output operations
- **OCR Engine**: Tesseract 4.0+ with LSTM neural networks
- **Image Processing**: 300 DPI default, configurable
- **Text Similarity**: SequenceMatcher (Ratcliff/Obershelp algorithm)

## Contact and Support

For bugs, feature requests, or questions:
- Open an issue in the repository
- Include system information, error messages, and sample files when applicable

## Changelog

### Version 1.0.0
- Initial release
- Hybrid extraction pipeline
- STEM content optimization
- Batch processing support
- Configurable chunking
- Comprehensive text cleaning