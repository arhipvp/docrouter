# Local File Organizer: AI File Management Run Entirely on Your Device, Privacy Assured

Tired of digital clutter? Overwhelmed by disorganized files scattered across your computer? Let AI do the heavy lifting! The Local File Organizer is your personal organizing assistant, using cutting-edge AI to bring order to your file chaos - all while respecting your privacy.

## How It Works 💡

Before:

```
/home/user/messy_documents/
├── IMG_20230515_140322.jpg
├── IMG_20230516_083045.jpg
├── IMG_20230517_192130.jpg
├── budget_2023.xlsx
├── meeting_notes_05152023.txt
├── project_proposal_draft.docx
├── random_thoughts.txt
├── recipe_chocolate_cake.pdf
├── scan0001.pdf
├── vacation_itinerary.docx
└── work_presentation.pptx

0 directories, 11 files
```

After:

```
/home/user/organized_documents/
├── Financial
│   └── 2023_Budget_Spreadsheet.xlsx
├── Food_and_Recipes
│   └── Chocolate_Cake_Recipe.pdf
├── Meetings_and_Notes
│   └── Team_Meeting_Notes_May_15_2023.txt
├── Personal
│   └── Random_Thoughts_and_Ideas.txt
├── Photos
│   ├── Cityscape_Sunset_May_17_2023.jpg
│   ├── Morning_Coffee_Shop_May_16_2023.jpg
│   └── Office_Team_Lunch_May_15_2023.jpg
├── Travel
│   └── Summer_Vacation_Itinerary_2023.docx
└── Work
    ├── Project_X_Proposal_Draft.docx
    ├── Quarterly_Sales_Report.pdf
    └── Marketing_Strategy_Presentation.pptx

7 directories, 11 files
```

## Updates 🚀

**[2024/09] v0.0.2**:
* Dry Run Mode: check sorting results before committing changes
* Silent Mode: save all logs to a txt file for quieter operation
* Added file support:  `.md`, .`excel`, `.ppt`, and `.csv`
* Three sorting options: by content, by date, and by type
* Improved CLI interaction experience
* Added real-time progress bar for file analysis

Please update the project by deleting the original project folder and reinstalling the requirements. Refer to the installation guide from Step 4.


## Roadmap 📅

- [ ] Copilot Mode: chat with AI to tell AI how you want to sort the file (ie. read and rename all the PDFs)
- [ ] Change models with CLI 
- [ ] ebook format support
- [ ] audio file support
- [ ] video file support
- [ ] Implement best practices like Johnny Decimal
- [ ] Check file duplication
- [ ] Dockerfile for easier installation

## What It Does 🔍

This intelligent file organizer harnesses the power of advanced AI models, including language models (LMs) and vision-language models (VLMs), to automate the process of organizing files by:


* Scanning a specified input directory for files.
* Content Understanding:
  - **Textual Analysis**: Applies simple NLTK-based heuristics to summarize text content and generate descriptive filenames.
  - **Visual Content Analysis**: Derives basic descriptions and categories from image filenames.

* Understanding the content of your files (text, images, and more) to generate relevant descriptions, folder names, and filenames.
* Organizing the files into a new directory structure based on the generated metadata.

All processing happens locally on your device. No internet connection is required, and no external APIs are used, keeping your files private and secure.


## Supported File Types 📁

- **Images:** `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`
- **Text Files:** `.txt`, `.docx`, `.md`
- **Spreadsheets:** `.xlsx`, `.csv`
- **Presentations:** `.ppt`, `.pptx`
- **PDFs:** `.pdf`

## Prerequisites 💻

- **Operating System:** Compatible with Windows, macOS, and Linux.
- **Python Version:** Python 3.12
- **Conda:** Anaconda or Miniconda installed.
- **Git:** For cloning the repository (or you can download the code as a ZIP file).

## Installation 🛠


### 1. Install Python

Before installing the Local File Organizer, make sure you have Python installed on your system. We recommend using Python 3.12 or later.

You can download Python from [the official website]((https://www.python.org/downloads/)).

Follow the installation instructions for your operating system.

### 2. Clone the Repository

Clone this repository to your local machine using Git:

```zsh
git clone https://github.com/QiuYannnn/Local-File-Organizer.git
```

Or download the repository as a ZIP file and extract it to your desired location.

### 3. Set Up the Python Environment

Create a new Conda environment named `local_file_organizer` with Python 3.12:

```zsh
conda create --name local_file_organizer python=3.12
```

Activate the environment:

```zsh
conda activate local_file_organizer
```

### 4. Install Dependencies

1. Ensure you are in the project directory:
   ```zsh
   cd path/to/Local-File-Organizer
   ```
   Replace `path/to/Local-File-Organizer` with the actual path where you cloned or extracted the project.

2. Install the required dependencies:
   ```zsh
   pip install -r requirements.txt
   ```

**Note:** If you encounter issues with any packages, install them individually:

```zsh
pip install Pillow pytesseract PyMuPDF python-docx
```

With the environment activated and dependencies installed, run the script using:

### 5. Running the Script🎉
```zsh
python main.py
```

## Notes

- **Dependencies:**
  - **pytesseract:** Requires Tesseract OCR installed on your system.
    - **macOS:** `brew install tesseract`
    - **Ubuntu/Linux:** `sudo apt-get install tesseract-ocr`
    - **Windows:** Download from [Tesseract OCR Windows Installer](https://github.com/UB-Mannheim/tesseract/wiki)
  - **PyMuPDF (fitz):** Used for reading PDFs.

- **Processing Time:**
  - Processing may take time depending on the number and size of files.
  - The script uses multiprocessing to improve performance.

- **Customizing Prompts:**
  - You can adjust prompts in `data_processing.py` to change how metadata is generated.

## License

This project is dual-licensed under the MIT License and Apache 2.0 License. You may choose which license you prefer to use for this project.

- See the [MIT License](LICENSE-MIT) for more details.