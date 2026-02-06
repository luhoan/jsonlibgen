import os
import json
import requests
import time
import re

# ================= CONFIGURATION =================
OUTPUT_FILE = "./src/data/library_rapid.json"

# YOUR RAPID API CREDENTIALS (For downloading text)
RAPID_API_KEY = "4c8e552382mshba2b4a050fb4d04p1d1c33jsn39df4ba3cd13"
RAPID_API_HOST = "project-gutenberg-free-books-api1.p.rapidapi.com"

# PAGINATION SETTINGS
CHARS_PER_PAGE = 1200
# =================================================

BOOKS_TO_FIND = [
    "Fyodor Dostoyevsky — The Idiot",
    "Leo Tolstoy — The Death of Ivan Ilyich",
    "Thomas De Quincey — Confessions of an English Opium-Eater",
    "Giacomo Leopardi — Zibaldone", 
    "Georg Christoph Lichtenberg — Aphorisms",
    "August Strindberg — Inferno",
    "Rainer Maria Rilke — The Notebooks of Malte Laurids Brigge",
    "Johann Wolfgang von Goethe — Wilhelm Meister’s Apprenticeship",
    "Thomas Mann — Buddenbrooks",
    "Robert Musil — Young Törless",
    "Alain-Fournier — The Lost Domain",
    "Henrik Ibsen — Peer Gynt",
    "Jacob Burckhardt — The Civilization of the Renaissance in Italy",
    "Matthew Arnold — Culture and Anarchy",
    "Walter Pater — The Renaissance",
    "Thomas Carlyle — Sartor Resartus",
    "Joris-Karl Huysmans — Against Nature",
    "Italo Svevo — Zeno’s Conscience",
    "Emanuel Swedenborg — Heaven and Hell",
    "Rumi — Masnavi",
    "The Upanishads",
    "Confucius — Analects",
    "Mencius — Mencius",
    "Zhuangzi — Zhuangzi",
    "Friedrich Nietzsche — Thus Spoke Zarathustra",
    "Friedrich Nietzsche — Beyond Good and Evil",
    "Friedrich Nietzsche — Genealogy of Morals",
    "Søren Kierkegaard — Fear and Trembling",
    "Fyodor Dostoyevsky — Crime and Punishment",
    "Franz Kafka — The Trial",
    "Karl Marx — The Communist Manifesto",
    "Alexis de Tocqueville — Democracy in America",
    "Edmund Burke — Reflections on the Revolution in France",
    "Plato — Republic",
    "Carl Jung — Modern Man in Search of a Soul",
    "James Frazer — The Golden Bough",
    "T. S. Eliot — The Waste Land",
    "Virginia Woolf — Mrs Dalloway",
    "Samuel Beckett — Waiting for Godot"
]

def paginate_text(text):
    if not text: return []
    paragraphs = text.split('\n\n')
    pages = []
    current_page_html = ""
    current_length = 0
    
    for para in paragraphs:
        para = para.strip()
        if not para: continue
        para_html = f"<p>{para}</p>"
        para_len = len(para)
        
        if (current_length + para_len > CHARS_PER_PAGE) and (current_length > 0):
            pages.append(current_page_html)
            current_page_html = para_html
            current_length = para_len
        else:
            current_page_html += para_html
            current_length += para_len
            
    if current_page_html:
        pages.append(current_page_html)
    return pages

def fetch_books():
    library_data = []
    print(f"🚀 Starting Hybrid Fetch (Gutendex Search + RapidAPI Download)...")

    for line in BOOKS_TO_FIND:
        # 1. Parse Input
        if "—" in line:
            parts = line.split("—")
            author_query = parts[0].strip()
            title_query = parts[1].strip()
        else:
            author_query = ""
            title_query = line.strip()

        print(f"\n🔍 Searching: '{title_query}'...")

        try:
            # ---------------------------------------------------------
            # STEP 1: FIND BOOK ID (Using Gutendex - It's Free & Reliable)
            # ---------------------------------------------------------
            search_url = "https://gutendex.com/books"
            # We search just by title to ensure we find something
            res = requests.get(search_url, params={"search": title_query})
            data = res.json()
            
            target_book = None
            
            if data['count'] > 0:
                # Filter results to find matching author
                for b in data['results']:
                    # Check if author name matches
                    authors_str = str(b.get('authors', [])).lower()
                    if author_query.lower() in authors_str or author_query == "":
                        target_book = b
                        break
                
                # If no strict author match, take first result
                if not target_book:
                    target_book = data['results'][0]
                    print("   ⚠️ Author mismatch, picking first result.")
            
            if not target_book:
                print("   ❌ Not found on Gutenberg (Likely Copyrighted).")
                continue

            book_id = target_book['id']
            book_title = target_book['title']
            subjects = target_book.get('subjects', [])
            
            print(f"   ✅ Identified ID: {book_id} ({book_title})")

            # ---------------------------------------------------------
            # STEP 2: DOWNLOAD TEXT (Using your RapidAPI Key)
            # ---------------------------------------------------------
            text_url = f"https://{RAPID_API_HOST}/books/{book_id}/text"
            
            headers = {
                "X-RapidAPI-Key": RAPID_API_KEY,
                "X-RapidAPI-Host": RAPID_API_HOST
            }
            
            print(f"   ⬇️  Fetching Text via RapidAPI...")
            text_res = requests.get(text_url, headers=headers, params={"cleaning_mode": "simple"})
            
            if text_res.status_code != 200:
                print(f"   ❌ RapidAPI Error: {text_res.status_code}")
                continue

            text_data = text_res.json()
            raw_text = text_data.get('text', '')

            if not raw_text:
                print("   ⚠️ Content empty.")
                continue

            # ---------------------------------------------------------
            # STEP 3: PROCESS & SAVE
            # ---------------------------------------------------------
            pages = paginate_text(raw_text)
            
            entry = {
                "id": str(book_id),
                "title": book_title,
                "author": author_query if author_query else "Unknown",
                "genre": subjects,
                "gutenberg_url": f"https://www.gutenberg.org/ebooks/{book_id}",
                "chapters": [
                    {
                        "chapter_index": 1,
                        "title": "Full Text",
                        "pages": pages
                    }
                ]
            }
            
            library_data.append(entry)
            print(f"   💾 Saved ({len(pages)} pages).")
            
            time.sleep(1) # Be polite

        except Exception as e:
            print(f"   💥 Error: {e}")

    # Save to JSON
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(library_data, f, indent=2, ensure_ascii=False)
        
    print(f"\n✨ COMPLETE. Data saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    fetch_books()
