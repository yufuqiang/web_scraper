import requests
from bs4 import BeautifulSoup
import csv
import time
import random
import logging
import argparse
import os
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# Configure logging
def setup_logging():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_file = os.path.join(script_dir, "scraper.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

class BookScraper:
    BASE_URL = "http://books.toscrape.com/"
    
    def __init__(self, output_file='books_enhanced.csv', max_pages=1, workers=5):
        self.output_file = output_file
        self.max_pages = max_pages
        self.workers = workers
        
        # Determine paths
        # Project root for this specific project is the directory containing this script
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(self.script_dir, 'data')
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.books_data = []

    def get_soup(self, url):
        """Helper to fetch a URL and return a BeautifulSoup object."""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except requests.RequestException as e:
            logging.error(f"Failed to fetch {url}: {e}")
            return None

    def scrape_detail_page(self, book_url):
        """Scrapes detailed info from a specific book page."""
        soup = self.get_soup(book_url)
        if not soup:
            return None

        try:
            # Extract Description
            product_description_header = soup.find('div', id='product_description')
            description = product_description_header.find_next_sibling('p').text if product_description_header else "No description available."
            
            # Extract Category
            breadcrumb = soup.find('ul', class_='breadcrumb')
            category = breadcrumb.find_all('li')[2].text.strip() if breadcrumb else "Unknown"
            
            # Extract UPC and other table data
            table = soup.find('table', class_='table table-striped')
            upc = table.find('td').text if table else "N/A"

            return {
                'Description': description,
                'Category': category,
                'UPC': upc
            }
        except Exception as e:
            logging.warning(f"Error parsing detail page {book_url}: {e}")
            return None

    def scrape_catalogue_page(self, url):
        """Scrapes a single catalogue page for book links and basic info."""
        soup = self.get_soup(url)
        if not soup:
            return [], None

        books_on_page = []
        articles = soup.find_all('article', class_='product_pod')
        
        for article in articles:
            try:
                title = article.h3.a['title']
                price = article.find('p', class_='price_color').text
                availability = article.find('p', class_='instock availability').text.strip()
                
                # Relative URL to absolute URL
                relative_url = article.h3.a['href']
                # Handle cases where relative url might contain 'catalogue/' or not
                if 'catalogue/' not in relative_url:
                     book_url = urljoin(self.BASE_URL, 'catalogue/' + relative_url)
                else:
                     book_url = urljoin(self.BASE_URL, relative_url)

                books_on_page.append({
                    'Title': title,
                    'Price': price,
                    'Availability': availability,
                    'URL': book_url
                })
            except Exception as e:
                logging.error(f"Error parsing book card: {e}")

        # Find next page
        next_button = soup.find('li', class_='next')
        next_url = None
        if next_button:
            next_relative = next_button.a['href']
            # Correctly join the next url relative to the current page url is tricky with urljoin if not careful
            # But here the structure is usually catalogue/page-X.html
            # Let's simple check if we are at root or subdir
            if "catalogue" in url:
                parent = url.rsplit('/', 1)[0]
                next_url = f"{parent}/{next_relative}"
            else:
                next_url = urljoin(self.BASE_URL, next_relative)
                
        return books_on_page, next_url

    def run(self):
        """Main execution logic."""
        logging.info("Starting scraper...")
        current_url = self.BASE_URL
        pages_scraped = 0
        all_book_listings = []

        # Step 1: Scrape Catalogue Pages
        with tqdm(total=self.max_pages, desc="Scraping Catalogue Pages", unit="page") as pbar:
            while current_url and pages_scraped < self.max_pages:
                logging.info(f"Scraping page: {current_url}")
                books, next_url = self.scrape_catalogue_page(current_url)
                all_book_listings.extend(books)
                
                pages_scraped += 1
                pbar.update(1)
                
                current_url = next_url
                # Polite delay
                time.sleep(random.uniform(0.5, 1.5))

        logging.info(f"Found {len(all_book_listings)} books. Starting detail extraction with {self.workers} workers.")

        # Step 2: Scrape Detail Pages concurrently
        final_data = []
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            # Create a dictionary to map future to book info
            future_to_book = {executor.submit(self.scrape_detail_page, book['URL']): book for book in all_book_listings}
            
            for future in tqdm(as_completed(future_to_book), total=len(all_book_listings), desc="Fetching Details", unit="book"):
                book_basic = future_to_book[future]
                try:
                    details = future.result()
                    if details:
                        # Merge basic info with details
                        full_book_data = {**book_basic, **details}
                        final_data.append(full_book_data)
                    else:
                        # Keep basic info if detail fetch fails
                        final_data.append(book_basic)
                except Exception as e:
                    logging.error(f"Worker exception for {book_basic['Title']}: {e}")
                    final_data.append(book_basic)

        self.save_to_csv(final_data)
        logging.info("Scraping finished successfully.")

    def save_to_csv(self, data):
        if not data:
            logging.warning("No data to save.")
            return

        # Determine all possible keys (fields)
        keys = set()
        for item in data:
            keys.update(item.keys())
        # Sort keys for consistent output, prioritize Title/Price
        fieldnames = ['Title', 'Price', 'Availability', 'Category', 'UPC', 'Description', 'URL']
        # Ensure all found keys are in fieldnames
        for k in keys:
            if k not in fieldnames:
                fieldnames.append(k)

        # Construct full output path
        # If output_file is just a filename, put it in data_dir
        # If it's a path (contains separator), use it as is
        if os.path.sep in self.output_file or '/' in self.output_file:
            output_path = self.output_file
        else:
            output_path = os.path.join(self.data_dir, self.output_file)

        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                dict_writer = csv.DictWriter(f, fieldnames=fieldnames)
                dict_writer.writeheader()
                dict_writer.writerows(data)
            logging.info(f"Saved {len(data)} items to {output_path}")
        except IOError as e:
            logging.error(f"Error saving file: {e}")

if __name__ == "__main__":
    setup_logging()
    parser = argparse.ArgumentParser(description="Advanced Web Scraper Demo")
    parser.add_argument("--pages", type=int, default=1, help="Number of catalogue pages to scrape")
    parser.add_argument("--workers", type=int, default=5, help="Number of concurrent threads")
    parser.add_argument("--output", type=str, default="books_enhanced.csv", help="Output filename")
    
    args = parser.parse_args()
    
    scraper = BookScraper(output_file=args.output, max_pages=args.pages, workers=args.workers)
    scraper.run()
