# Advanced E-commerce Web Scraper

This project demonstrates a production-grade web scraper built with Python, designed to extract comprehensive product data from e-commerce websites.

It targets [Books to Scrape](http://books.toscrape.com/), a sandbox environment for web scraping, but the architecture is applicable to real-world scenarios like Amazon, eBay, or Shopify stores.

## Key Features

*   **Multi-Page Traversal**: Automatically detects and follows pagination links to scrape multiple catalogue pages.
*   **Nested Data Extraction**: Visits each product's detail page to fetch in-depth information (e.g., Description, UPC, Category) that isn't available on the listing page.
*   **Concurrency**: Uses `ThreadPoolExecutor` to fetch product details in parallel, significantly speeding up the scraping process compared to a sequential approach.
*   **Robust Error Handling**: Includes try/catch blocks for network requests and parsing logic to ensure the scraper doesn't crash on a single bad element.
*   **Politeness**: Implements random delays between page requests to mimic human behavior and avoid rate limits.
*   **Logging & Progress Bars**: Provides real-time feedback using `tqdm` progress bars and detailed logs saved to `scraper.log`.
*   **CLI Interface**: Fully configurable via command-line arguments.

## Prerequisites

*   Python 3.7+
*   pip

## Installation

1.  Navigate to the project directory:
    ```bash
    cd web_scraper
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

Run the scraper with default settings (scrapes 1 page, uses 5 threads):

```bash
python scraper.py
```

### Customizing the Run

You can control the number of pages to scrape, the number of concurrent workers, and the output filename using CLI arguments:

```bash
# Scrape 3 pages, use 10 threads for speed, and save to my_books.csv
python scraper.py --pages 3 --workers 10 --output my_books.csv
```

### Output

The script generates a CSV file (default: `books_enhanced.csv`) containing:
*   Title
*   Price
*   Availability
*   Category (from detail page)
*   UPC (from detail page)
*   Description (from detail page)
*   URL

## Technical Highlights for Clients

*   **Scalability**: The modular design allows for easy addition of new fields or adaptation to different site structures.
*   **Performance**: The use of multithreading demonstrates the ability to handle large datasets efficiently.
*   **Code Quality**: Follows PEP 8 standards, uses Type Hinting (implicit), and includes comprehensive docstrings.
