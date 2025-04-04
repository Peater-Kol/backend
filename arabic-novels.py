import requests
from bs4 import BeautifulSoup
import json
import os
import re
import time
import pymongo
from urllib.parse import unquote
from flask import Flask, jsonify, request
from bson.objectid import ObjectId
from flask_cors import CORS  # Import CORS

# MongoDB connection setup3

def get_database_connection():

    
    try:
        # MongoDB Atlas connection string
        # connection_string = "mongodb+srv://titou:titou1234@cluster0.1fx2g.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
        connection_string = "mongodb://localhost:27017"
        # Connect to MongoDB Atlas with SSL certificate verification disabled
        # This is a workaround for certificate verification issues
        client = pymongo.MongoClient(connection_string)
        
        # Verify connection is successful by pinging the database
        client.admin.command('ping')
        
        
        # Database and collections setup
        db = client["manga_database"]
        manga_collection = db["manga_info"] 
        chapters_collection = db["chapters"]
        
        return db, manga_collection, chapters_collection
    except Exception as e:
        print("\033[91m✗ Failed to connect to MongoDB Atlas: {}\033[0m".format(str(e)))
        # Print more detailed error info for debugging
        import traceback
        traceback.print_exc()
        
        # Instead of raising the exception, provide empty collections
        # This allows the application to start even if DB connection fails
        print("Continuing with empty database connection...")
        class EmptyCollection:
            def find_one(self, *args, **kwargs): return None
            def find(self, *args, **kwargs): return []
            def insert_one(self, *args, **kwargs): return None
            def update_one(self, *args, **kwargs): return None
        
        empty_db = {}
        empty_manga = EmptyCollection()
        empty_chapters = EmptyCollection()
        return empty_db, empty_manga, empty_chapters
# def scrape_and_store_manga_data(url):
#     try:
#         db, manga_collection, chapters_collection = get_database_connection()
        
#         # Check if manga already exists in database
#         existing_manga = manga_collection.find_one({"manga_url": url})
#         if existing_manga:
#             print(f"Manga already exists in database with ID: {existing_manga['_id']}")
#             return existing_manga
        
#         # Scrape manga data
#         response = requests.get(url)
#         response.raise_for_status()
        
#         soup = BeautifulSoup(response.content, 'html.parser')
        
#         # Get the manga title
#         title_element = soup.find('div', class_='post-title')
#         title = title_element.h1.text.strip() if title_element and title_element.h1 else "Unknown Title"
        
#         # Find all chapter list items
#         chapter_items = soup.find_all('li', class_='wp-manga-chapter')
        
#         chapters = []
#         for item in chapter_items:
#             chapter_link = item.find('a')
#             if chapter_link:
#                 chapter_url = chapter_link['href']
#                 chapter_title = chapter_link.text.strip()
                
#                 # Extract chapter number if available
#                 chapter_number = None
#                 number_match = re.search(r'chapter[- ](\d+)', chapter_title.lower())
#                 if number_match:
#                     chapter_number = int(number_match.group(1))
#                 else:
#                     # Try to find number in the URL
#                     url_match = re.search(r'chapter-(\d+)', chapter_url)
#                     if url_match:
#                         chapter_number = int(url_match.group(1))
                
#                 chapters.append({
#                     "title": chapter_title,
#                     "url": chapter_url,
#                     "chapter_number": chapter_number,
#                     "content_extracted": False
#                 })
        
#         # Create a dictionary to hold all manga data
#         manga_data = {
#             "manga_url": url,
#             "manga_title": title,
#             "total_chapters": len(chapters),
#             "last_updated": time.time(),
#             "chapters": chapters
#         }
        
#         # Insert manga data into MongoDB
#         result = manga_collection.insert_one(manga_data)
#         manga_id = result.inserted_id
        
#         print(f"Manga '{title}' with {len(chapters)} chapters saved to database with ID: {manga_id}")
        
#         # Return manga data with ID
#         manga_data["_id"] = manga_id
#         return manga_data
    
#     except Exception as e:
#         print(f"Error scraping manga data: {str(e)}")
#         return None
def scrape_and_store_manga_data(url):
    try:
        db, manga_collection, chapters_collection = get_database_connection()
        
        # Check if manga already exists in database
        existing_manga = manga_collection.find_one({"manga_url": url})
        if existing_manga:
            print(f"Manga already exists in database with ID: {existing_manga['_id']}")
            return existing_manga
        
        # Scrape manga data
        response = requests.get(url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Get the manga title
        title_element = soup.find('div', class_='post-title')
        title = title_element.h1.text.strip() if title_element and title_element.h1 else "Unknown Title"
        
        # Get the manga cover image
        cover_image_url = None
        cover_image_alt = None
        
        # Try to find image in summary_image div first
        summary_image_div = soup.find('div', class_='summary_image')
        if summary_image_div:
            img_tag = summary_image_div.find('img')
            if img_tag:
                cover_image_url = img_tag.get('src')
                cover_image_alt = img_tag.get('alt')
        
        # If not found, try other common image containers
        if not cover_image_url:
            # Try tab-summary area
            tab_summary = soup.find('div', class_='tab-summary')
            if tab_summary:
                img_tag = tab_summary.find('img')
                if img_tag:
                    cover_image_url = img_tag.get('src')
                    cover_image_alt = img_tag.get('alt')
        
        # If still not found, try any prominent image
        if not cover_image_url:
            # Look for the first image with classes commonly used for manga covers
            img_tag = soup.find('img', class_=['img-responsive', 'wp-post-image'])
            if img_tag:
                cover_image_url = img_tag.get('src')
                cover_image_alt = img_tag.get('alt')
        
        # Find all chapter list items
        chapter_items = soup.find_all('li', class_='wp-manga-chapter')
        
        chapters = []
        for item in chapter_items:
            chapter_link = item.find('a')
            if chapter_link:
                chapter_url = chapter_link['href']
                chapter_title = chapter_link.text.strip()
                
                # Extract chapter number if available
                chapter_number = None
                number_match = re.search(r'chapter[- ](\d+)', chapter_title.lower())
                if number_match:
                    chapter_number = int(number_match.group(1))
                else:
                    # Try to find number in the URL
                    url_match = re.search(r'chapter-(\d+)', chapter_url)
                    if url_match:
                        chapter_number = int(url_match.group(1))
                
                chapters.append({
                    "title": chapter_title,
                    "url": chapter_url,
                    "chapter_number": chapter_number,
                    "content_extracted": False
                })
        
        # Create a dictionary to hold all manga data
        manga_data = {
            "manga_url": url,
            "manga_title": title,
            "cover_image_url": cover_image_url,
            "cover_image_alt": cover_image_alt,
            "total_chapters": len(chapters),
            "last_updated": time.time(),
            "chapters": chapters
        }
        
        # Insert manga data into MongoDB
        result = manga_collection.insert_one(manga_data)
        manga_id = result.inserted_id
        
        print(f"Manga '{title}' with {len(chapters)} chapters saved to database with ID: {manga_id}")
        
        # Return manga data with ID
        manga_data["_id"] = manga_id
        return manga_data
    
    except Exception as e:
        print(f"Error scraping manga data: {str(e)}")
        return None
def extract_and_store_chapter_content(manga_id, chapter_url, chapter_index=None):
    try:
        db, manga_collection, chapters_collection = get_database_connection()
        
        # Check if chapter already exists
        existing_chapter = chapters_collection.find_one({"chapter_url": chapter_url})
        if existing_chapter:
            print(f"Chapter already exists in database with ID: {existing_chapter['_id']}")
            
            # Update manga document to mark this chapter as extracted
            if manga_id:
                manga_collection.update_one(
                    {"_id": ObjectId(manga_id), "chapters.url": chapter_url},
                    {"$set": {"chapters.$.content_extracted": True}}
                )
            
            return existing_chapter
        
        # Send HTTP request with retries
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://cenele.com/'
        }

        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                response = requests.get(chapter_url, headers=headers, timeout=30)
                response.raise_for_status()
                break
            except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
                if attempt < max_retries - 1:
                    print(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise

        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract chapter title - try multiple approaches
        title_element = soup.find('h2', style=lambda value: value and 'text-align: center' in value)
        if not title_element:
            title_element = soup.find('h1', class_='entry-title')
        if not title_element:
            title_element = soup.find(['h1', 'h2', 'h3'], class_=['chapter-title', 'entry-title'])

        chapter_title = title_element.text.strip() if title_element else "Unknown Title"

        # Extract chapter ID from input if present
        chapter_id = None
        id_input = soup.find('input', id='wp-manga-current-chap')
        if id_input:
            chapter_id = id_input.get('data-id')

        # Find the reading content container - try multiple possible selectors
        content_div = soup.find('div', class_='reading-content')
        if not content_div:
            content_div = soup.find('div', class_=['entry-content', 'chapter-content', 'text-content'])

        # Extract the chapter content - try different approaches based on the site structure
        paragraphs = []

        if content_div:
            # First try to find text-right or text-left containers
            text_div = content_div.find('div', class_=['text-right', 'text-left'])

            # If that fails, use the content_div directly
            if text_div:
                all_paragraphs = text_div.find_all('p')
            else:
                all_paragraphs = content_div.find_all('p')

            for p in all_paragraphs:
                # Skip if paragraph contains only an image or empty content
                if p.find('img') and len(p.get_text(strip=True)) == 0:
                    continue

                text = p.get_text(strip=True)
                # Skip empty paragraphs and non-breaking spaces
                if text and text != '&nbsp;':
                    # Replace any HTML entities
                    text = text.replace('&nbsp;', ' ')
                    paragraphs.append(text)

        # Extract chapter number from URL or title
        chapter_number = None
        # Try to extract from URL using both encoded and decoded formats
        chapter_match = re.search(r'%d8%a7%d9%84%d9%81%d8%b5%d9%84-(\d+)', chapter_url)
        if not chapter_match:
            # Try with unquoted URL (in case it's already decoded)
            chapter_match = re.search(r'الفصل-(\d+)', unquote(chapter_url))
        
        # Try extracting chapter number from URL
        if not chapter_match:
            chapter_match = re.search(r'chapter-(\d+)', chapter_url)

        if chapter_match:
            chapter_number = chapter_match.group(1)
            try:
                chapter_number = int(chapter_number)
            except ValueError:
                pass
        else:
            # Try to extract from title
            title_match = re.search(r'(\d+)', chapter_title)
            if title_match:
                chapter_number = title_match.group(1)
                try:
                    chapter_number = int(chapter_number)
                except ValueError:
                    pass
            else:
                # As a last resort, try to find it in the page content
                chapter_text = soup.find(string=re.compile(r'chapter\s*(\d+)', re.IGNORECASE))
                if chapter_text:
                    text_match = re.search(r'chapter\s*(\d+)', chapter_text, re.IGNORECASE)
                    if text_match:
                        chapter_number = text_match.group(1)
                        try:
                            chapter_number = int(chapter_number)
                        except ValueError:
                            pass

        # Create a dictionary with the chapter information
        chapter_data = {
            'manga_id': ObjectId(manga_id) if manga_id else None,
            'chapter_url': chapter_url,
            'title': chapter_title,
            'chapter_id': chapter_id,
            'chapter_number': chapter_number,
            'chapter_index': chapter_index,
            'content': paragraphs,
            'paragraph_count': len(paragraphs),
            'date_extracted': time.time()
        }

        # Insert chapter data into MongoDB
        result = chapters_collection.insert_one(chapter_data)
        chapter_id = result.inserted_id
        
        # Update manga document to mark this chapter as extracted
        if manga_id:
            manga_collection.update_one(
                {"_id": ObjectId(manga_id), "chapters.url": chapter_url},
                {"$set": {"chapters.$.content_extracted": True}}
            )
        
        print(f"Chapter '{chapter_title}' saved to database with ID: {chapter_id}")
        
        # Return chapter data with ID
        chapter_data["_id"] = str(chapter_id)
        return chapter_data

    except Exception as e:
        print(f"Error extracting content from {chapter_url}: {str(e)}")
        return {
            'url': chapter_url,
            'error': str(e)
        }

def extract_all_chapters_for_manga(manga_id, limit=None):
    try:
        db, manga_collection, chapters_collection = get_database_connection()
        
        # Get manga document
        manga = manga_collection.find_one({"_id": ObjectId(manga_id)})
        if not manga:
            print(f"No manga found with ID {manga_id}")
            return None
            
        chapters = manga.get("chapters", [])
        print(f"Found {len(chapters)} chapters for manga '{manga['manga_title']}'")
        
        if limit and limit < len(chapters):
            print(f"Limiting extraction to {limit} chapters")
            chapters = chapters[:limit]
        
        success_count = 0
        failure_count = 0
        
        for i, chapter in enumerate(chapters):
            if chapter.get("content_extracted"):
                print(f"Chapter '{chapter['title']}' already extracted. Skipping.")
                continue
                
            print(f"[{i+1}/{len(chapters)}] Extracting content for '{chapter['title']}'...")
            result = extract_and_store_chapter_content(manga_id, chapter["url"], i)
            
            if result and 'error' not in result:
                success_count += 1
            else:
                failure_count += 1
                
            # Add a delay to avoid overloading the server
            time.sleep(2)
                
        print(f"Extraction complete: {success_count} chapters successful, {failure_count} chapters failed.")
        return {"success_count": success_count, "failure_count": failure_count}
        
    except Exception as e:
        print(f"Error extracting chapters: {str(e)}")
        return None

# Flask API setup
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/api/manga', methods=['GET'])
def get_all_manga():
    try:
        db, manga_collection, _ = get_database_connection()
        
        # Get all manga with limited fields (don't return all chapter data)
        manga_list = list(manga_collection.find({}, {"manga_title": 1, "total_chapters": 1, "manga_url": 1, "last_updated": 1,"cover_image_alt":1,"cover_image_url":1}))
        
        # Convert ObjectId to string for JSON serialization
        for manga in manga_list:
            manga["_id"] = str(manga["_id"])
            
        return jsonify({"status": "success", "count": len(manga_list), "data": manga_list})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/manga/<manga_id>', methods=['GET'])
def get_manga_details(manga_id):
    try:
        db, manga_collection, _ = get_database_connection()
        
        manga = manga_collection.find_one({"_id": ObjectId(manga_id)})
        if not manga:
            return jsonify({"status": "error", "message": "Manga not found"}), 404
            
        # Convert ObjectId to string for JSON serialization
        manga["_id"] = str(manga["_id"])
            
        return jsonify({"status": "success", "data": manga})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/manga/<manga_id>/chapters', methods=['GET'])
def get_manga_chapters(manga_id):
    try:
        db, manga_collection, _ = get_database_connection()
        
        manga = manga_collection.find_one({"_id": ObjectId(manga_id)})
        if not manga:
            return jsonify({"status": "error", "message": "Manga not found"}), 404
            
        chapters = manga.get("chapters", [])
            
        return jsonify({
            "status": "success", 
            "manga_title": manga["manga_title"],
            "total_chapters": len(chapters),
            "chapters": chapters
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/chapter/<chapter_id>', methods=['GET'])
def get_chapter_content(chapter_id):
    try:
        _, _, chapters_collection = get_database_connection()
        
        chapter = chapters_collection.find_one({"_id": ObjectId(chapter_id)})
        if not chapter:
            return jsonify({"status": "error", "message": "Chapter not found"}), 404
            
        # Convert ObjectId to string for JSON serialization
        chapter["_id"] = str(chapter["_id"])
        if chapter.get("manga_id"):
            chapter["manga_id"] = str(chapter["manga_id"])
            
        return jsonify({"status": "success", "data": chapter})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/manga/scrape', methods=['POST'])
def scrape_manga():
    try:
        data = request.json
        url = data.get('url')
        
        if not url:
            return jsonify({"status": "error", "message": "URL is required"}), 400
            
        manga_data = scrape_and_store_manga_data(url)
        
        if manga_data:
            # Convert ObjectId to string for JSON serialization
            manga_data["_id"] = str(manga_data["_id"])
            return jsonify({"status": "success", "data": manga_data})
        else:
            return jsonify({"status": "error", "message": "Failed to scrape manga"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
# Add this new route to the existing Flask app

# Add these new POST routes to the existing Flask app

@app.route('/api/chapter/lookup', methods=['POST'])
def lookup_chapter():
    try:
        data = request.json
        _, _, chapters_collection = get_database_connection()
        
        # Get parameters from request body
        chapter_url = data.get('url')
        manga_id = data.get('manga_id')
        chapter_number = data.get('chapter_number')
        
        # Build the query
        query = {}
        if chapter_url:
            query['chapter_url'] = chapter_url
        if manga_id:
            query['manga_id'] = ObjectId(manga_id)
        if chapter_number is not None:  # Allow 0 as valid chapter number
            try:
                query['chapter_number'] = int(chapter_number)
            except (ValueError, TypeError):
                # If it's not an integer, try as string
                query['chapter_number'] = chapter_number
        
        if not query:
            return jsonify({"status": "error", "message": "At least one search parameter is required"}), 400
            
        # Find chapter
        chapter = chapters_collection.find_one(query)
        if not chapter:
            return jsonify({"status": "error", "message": "Chapter not found"}), 404
            
        # Convert ObjectId to string for JSON serialization
        chapter["_id"] = str(chapter["_id"])
        if chapter.get("manga_id"):
            chapter["manga_id"] = str(chapter["manga_id"])
            
        return jsonify({"status": "success", "data": chapter})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Add a POST route to get chapter ID only (more lightweight)
@app.route('/api/chapter/get_id', methods=['POST'])
def get_chapter_id():
    try:
        data = request.json
        _, _, chapters_collection = get_database_connection()
        
        # Get parameters from request body
        chapter_url = data.get('url')
        manga_id = data.get('manga_id')
        chapter_number = data.get('chapter_number')
        
        # Build the query
        query = {}
        if chapter_url:
            query['chapter_url'] = chapter_url
        if manga_id:
            query['manga_id'] = ObjectId(manga_id)
        if chapter_number is not None:  # Allow 0 as valid chapter number
            try:
                query['chapter_number'] = int(chapter_number)
            except (ValueError, TypeError):
                query['chapter_number'] = chapter_number
        
        if not query:
            return jsonify({"status": "error", "message": "At least one search parameter is required"}), 400
            
        # Find chapter but only return the ID
        chapter = chapters_collection.find_one(query, {"_id": 1})
        if not chapter:
            return jsonify({"status": "error", "message": "Chapter not found"}), 404
            
        return jsonify({
            "status": "success", 
            "chapter_id": str(chapter["_id"])
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Also add a POST route to get multiple chapter IDs at once
@app.route('/api/manga/chapter_ids', methods=['POST'])
def get_manga_chapter_ids():
    try:
        data = request.json
        manga_id = data.get('manga_id')
        
        if not manga_id:
            return jsonify({"status": "error", "message": "manga_id is required"}), 400
            
        _, _, chapters_collection = get_database_connection()
        
        # Additional optional filters
        filters = {"manga_id": ObjectId(manga_id)}
        
        # Add optional chapter range filter if provided
        if data.get('min_chapter') is not None:
            if 'chapter_number' not in filters:
                filters['chapter_number'] = {}
            filters['chapter_number']['$gte'] = int(data.get('min_chapter'))
            
        if data.get('max_chapter') is not None:
            if 'chapter_number' not in filters:
                filters['chapter_number'] = {}
            filters['chapter_number']['$lte'] = int(data.get('max_chapter'))
        
        # Find all chapters for this manga with filters
        chapters = chapters_collection.find(
            filters, 
            {"_id": 1, "chapter_number": 1, "title": 1, "chapter_url": 1}
        ).sort("chapter_number", 1)  # Sort by chapter number
        
        result = []
        for chapter in chapters:
            result.append({
                "chapter_id": str(chapter["_id"]),
                "chapter_number": chapter.get("chapter_number"),
                "title": chapter.get("title"),
                "url": chapter.get("chapter_url")
            })
            
        return jsonify({
            "status": "success",
            "count": len(result),
            "data": result
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/chapter/url/v1', methods=['POST'])
def get_chapter_by_url():
    try:
        data = request.json
        _, _, chapters_collection = get_database_connection()
        
        # Get parameters from request body
        chapter_url = data.get('url')
        manga_id = data.get('manga_id')
        
        # Validate required parameters
        if not chapter_url:
            return jsonify({"status": "error", "message": "Chapter URL is required"}), 400
            
        # Build the query
        query = {"chapter_url": chapter_url}
        if manga_id:
            query['manga_id'] = ObjectId(manga_id)
            
        # Find chapter
        chapter = chapters_collection.find_one(query)
        if not chapter:
            return jsonify({"status": "error", "message": "Chapter not found"}), 404
            
        # Convert ObjectId to string for JSON serialization
        chapter["_id"] = str(chapter["_id"])
        if chapter.get("manga_id"):
            chapter["manga_id"] = str(chapter["manga_id"])
            
        return jsonify({"status": "success", "data": chapter})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/chapter/extract', methods=['POST'])
def extract_chapter():
    try:
        data = request.json
        manga_id = data.get('manga_id')
        chapter_url = data.get('chapter_url')
        
        if not manga_id or not chapter_url:
            return jsonify({"status": "error", "message": "manga_id and chapter_url are required"}), 400
            
        chapter_data = extract_and_store_chapter_content(manga_id, chapter_url)
        
        if chapter_data:
            # Convert ObjectId to string for JSON serialization
            if '_id' in chapter_data:
                chapter_data['_id'] = str(chapter_data['_id'])
            if 'manga_id' in chapter_data:
                chapter_data['manga_id'] = str(chapter_data['manga_id'])
                
            return jsonify({"status": "success", "data": chapter_data})
        else:
            return jsonify({"status": "error", "message": chapter_data.get('error', 'Unknown error')}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/manga/<manga_id>/extract_all', methods=['POST'])
def extract_all_chapters(manga_id):
    try:
        data = request.json
        limit = data.get('limit')  # Optional parameter
        
        result = extract_all_chapters_for_manga(manga_id, limit)
        
        if result:
            return jsonify({"status": "success", "data": result})
        else:
            return jsonify({"status": "error", "message": "Failed to extract chapters"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def main():
    print("Manga Database and API Tool")
    print("===========================")
    print("1. Scrape and store a new manga")
    print("2. Extract content for a manga's chapters")
    print("3. Start the API server")
    print("4. Exit")
    
    choice = input("Enter your choice (1-4): ")
    
    if choice == "1":
        url = input("Enter the manga URL: ")
        manga_data = scrape_and_store_manga_data(url)
        if manga_data:
            print(f"Success! Manga ID: {manga_data['_id']}")
        else:
            print("Failed to scrape manga data.")
    
    elif choice == "2":
        manga_id = input("Enter the manga ID: ")
        limit_input = input("Limit number of chapters to extract (press Enter for all): ")
        limit = int(limit_input) if limit_input.strip() else None
        
        result = extract_all_chapters_for_manga(manga_id, limit)
        if result:
            print(f"Extraction completed: {result['success_count']} successful, {result['failure_count']} failed")
        else:
            print("Failed to extract chapters.")
    
    elif choice == "3":
        print("Starting API server...")
        # Install flask-cors if not already installed
        try:
            import flask_cors
        except ImportError:
            print("Installing flask-cors...")
            os.system("pip install flask-cors")
        app.run(debug=True, host='0.0.0.0', port=3001)
    
    elif choice == "4":
        print("Exiting...")
        return
    
    else:
        print("Invalid choice.")
    
    # Recursive call to show menu again
    main()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nServer shutdown requested.")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")