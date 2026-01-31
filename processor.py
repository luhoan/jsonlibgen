import os
import json
import re
from unicodedata import name
import warnings
from bs4 import BeautifulSoup
# --- CRITICAL FIX: Importing ITEM_DOCUMENT preventing the "not defined" error ---
from ebooklib import epub, ITEM_DOCUMENT 

# ================= CONFIGURATION =================
INPUT_DIR = "raw_library"
DB_FILE = "./src/data/library.json"
CLAUDE_PROMPT_FILE = "prompt_for_claude.txt"
CHARS_PER_PAGE = 1200 

warnings.filterwarnings("ignore")
# =================================================

def clean_filename(text):
    if not text: return "Unknown"
    text = re.sub(r'[<>:"/\\|?*]', '', str(text))
    return text.strip()

def paginate_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Clean heavy media
    for tag in soup(["script", "style", "img", "iframe", "video"]):
        tag.decompose()

    root = soup.body if soup.body else soup
    pages = []
    current_page_html = ""
    current_length = 0
    
    elements = root.find_all(recursive=False)
    
    if not elements:
        text = root.get_text()
        elements = [BeautifulSoup(f"<p>{text}</p>", 'html.parser')]

    for tag in elements:
        tag_html = str(tag)
        tag_text_len = len(tag.get_text())
        
        if (current_length + tag_text_len > CHARS_PER_PAGE) and (current_length > 0):
            pages.append(current_page_html)
            current_page_html = tag_html
            current_length = tag_text_len
        else:
            current_page_html += tag_html
            current_length += tag_text_len

    if current_page_html:
        pages.append(current_page_html)
    return pages

def generate_database():
    print("\n🔹 PHASE 3: Generating JSON Database...")
    library_data = []
    
    if not os.path.exists(INPUT_DIR):
        print("❌ Error: Input directory not found. Run organizer.py first.")
        return

    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(('.epub', '.html', '.htm'))]

    for filename in files:
        file_path = os.path.join(INPUT_DIR, filename)
        ext = os.path.splitext(filename)[1].lower()
        
        # Derive Metadata from Filename (Trusting the Organizer)
        if "—" in filename:
            parts = filename.split("—", 1)
            author = parts[0].strip()
            title = parts[1].replace(ext, "").strip()
        else:
            author = "Unknown"
            title = filename.replace(ext, "")
            
        book_id = clean_filename(title).replace(" ", "_").lower()
        processed_chapters = []
        raw_html_chapters = []
        
        # --- STRATEGY A: EPUB ---
        if ext == '.epub':
            try:
                book = epub.read_epub(file_path)
                for item in book.get_items():
                    # Check against the imported constant
                    if item.get_type() == ITEM_DOCUMENT: 
                        content = item.get_content().decode('utf-8', errors='ignore')
                        if len(content) > 500: 
                            raw_html_chapters.append(content)
            except Exception as e:
                print(f"   ❌ Error reading EPUB {filename}: {e}")

        # --- STRATEGY B: HTML ---
        elif ext in ['.html', '.htm']:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    raw_html_chapters.append(f.read())
            except Exception as e:
                print(f"   ❌ Error reading HTML {filename}: {e}")

        # --- PAGINATION ---
        for index, html_chapter in enumerate(raw_html_chapters):
            pages_array = paginate_html(html_chapter)
            if pages_array:
                processed_chapters.append({
                    "chapter_index": index + 1,
                    "pages": pages_array
                })

        if processed_chapters:
            library_data.append({
                "id": book_id,
                "title": title,
                "author": author,
                "chapters": processed_chapters
            })
            print(f"   📖 Processed: {title}")

    # Save
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(library_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✨ DONE! Database saved to: {DB_FILE}")
    return library_data

def generate_claude_prompt(data):
    if not data: return
    sample_json = json.dumps([data[0]], indent=2) if data else "{}"
    
    prompt = f"""
I have a JSON database of books for a React website.
The content is HTML, and it is ALREADY split into 'pages' for a flipbook.

JSON STRUCTURE:
```json
{sample_json}
```

REQUIREMENTS:

    Parse this JSON.
    Create a BookReader component using 'react-pageflip'.
    Map through chapters, and inside that map through pages.
    Render the HTML string inside the pages using dangerouslySetInnerHTML.
    """
    with open(CLAUDE_PROMPT_FILE, 'w', encoding='utf-8') as f:
        f.write(prompt)
    print(f"🤖 Claude Prompt generated at: {CLAUDE_PROMPT_FILE}")

if __name__ == "__main__":
    data = generate_database()
    generate_claude_prompt(data)