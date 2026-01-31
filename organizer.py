import os
import shutil
import re
import pdfplumber
import warnings
from bs4 import BeautifulSoup
from ebooklib import epub

# ================= CONFIGURATION =================
INPUT_DIR = "raw_library"
ARCHIVE_PDF_DIR = os.path.join(INPUT_DIR, "pdfs")

warnings.filterwarnings("ignore")
# =================================================

def setup_directories():
    if not os.path.exists(INPUT_DIR):
        os.makedirs(INPUT_DIR)
        print(f"📁 Created '{INPUT_DIR}'. Put your raw books here.")
        exit()
    if not os.path.exists(ARCHIVE_PDF_DIR):
        os.makedirs(ARCHIVE_PDF_DIR)

def clean_filename(text):
    if not text: return "Unknown"
    text = re.sub(r'[<>:"/\\|?*]', '', str(text))
    return text.strip()

def convert_pdfs_to_epub():
    print("\n🔹 PHASE 1: Converting PDFs...")
    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]
    
    if not files:
        print("   No PDFs found to convert.")
        return

    for filename in files:
        pdf_path = os.path.join(INPUT_DIR, filename)
        print(f"   Processing PDF: {filename}...")
        
        text_content = ""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                meta = pdf.metadata
                title = meta.get('Title', filename.replace('.pdf', '')) if meta else filename
                author = meta.get('Author', 'Unknown') if meta else 'Unknown'

                for page in pdf.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text_content += extracted + "\n\n"
        except Exception as e:
            print(f"   ❌ Error reading PDF: {e}")
            continue

        if len(text_content) < 50:
            print("   ⚠️ Skipped (No text found).")
            continue

        # Create EPUB
        book = epub.EpubBook()
        book.set_identifier(filename)
        book.set_title(title)
        book.set_language('en')
        book.add_author(author)

        # Convert content
        formatted_text = text_content.replace('\n', '<br/>')
        c1 = epub.EpubHtml(title='Full Text', file_name='content.xhtml', lang='en')
        c1.content = f"<h1>{title}</h1><p>{formatted_text}</p>"
        book.add_item(c1)
        
        # Navigation
        book.toc = (c1,)
        book.spine = ['nav', c1]
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        # Save & Archive
        epub.write_epub(os.path.join(INPUT_DIR, filename.replace('.pdf', '.epub')), book, {})
        shutil.move(pdf_path, os.path.join(ARCHIVE_PDF_DIR, filename))
        print(f"   ✅ Converted & Archived: {filename}")

def get_metadata(path, ext):
    title, author = "Untitled", "Unknown"
    try:
        if ext == '.epub':
            book = epub.read_epub(path)
            t = book.get_metadata('DC', 'title')
            if t: title = t[0][0]
            c = book.get_metadata('DC', 'creator')
            if c: author = c[0][0]
            
        elif ext in ['.html', '.htm']:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                soup = BeautifulSoup(f, 'html.parser')
                if soup.title: title = soup.title.string
                meta = soup.find("meta", attrs={"name": "author"})
                if meta: author = meta["content"]
    except: pass
    return title, author

def rename_files():
    print("\n🔹 PHASE 2: Renaming Files...")
    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(('.epub', '.html', '.htm'))]

    for filename in files:
        if "—" in filename: continue 
        
        path = os.path.join(INPUT_DIR, filename)
        ext = os.path.splitext(filename)[1].lower()
        title, author = get_metadata(path, ext)
        
        if title and title != "Untitled":
            new_name = f"{clean_filename(author)} — {clean_filename(title)}{ext}"
            new_path = os.path.join(INPUT_DIR, new_name)
            
            if not os.path.exists(new_path) and new_name != filename:
                os.rename(path, new_path)
                print(f"   ✏️  Renamed: {new_name}")

if __name__ == "__main__":
    setup_directories()
    convert_pdfs_to_epub()
    rename_files()
    print("\n✨ Organization Complete. Now run processor.py")