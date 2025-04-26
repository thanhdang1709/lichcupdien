import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime
import os

class LichCupDienSeleniumCrawler:
    def __init__(self, headless=True):
        self.base_url = "https://lichcupdien.org/lich-cup-dien-an-giang"
        
        # Setup Chrome options
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # User agent to appear as a regular browser
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        # Initialize the Chrome driver
        self.driver = webdriver.Chrome(options=chrome_options)
    
    def extract_date_from_heading(self, text):
        """Extract date from heading text using regex."""
        date_pattern = r"ngày (\d{1,2}/\d{1,2}/\d{4})"
        match = re.search(date_pattern, text)
        if match:
            date_str = match.group(1)
            try:
                return datetime.strptime(date_str, "%d/%m/%Y").strftime("%Y-%m-%d")
            except ValueError:
                return None
        return None
    
    def parse_outage_entry(self, entry_text):
        """Parse a single outage entry text into structured data."""
        entry_data = {}
        
        # Extract fields using regex patterns
        patterns = {
            "power_company": r"Điện lực:\s*(.+?)(?=Ngày:|$)",
            "date": r"Ngày:\s*(.+?)(?=Thời gian:|$)",
            "time": r"Thời gian:\s*(.+?)(?=Khu vực:|$)",
            "area": r"Khu vực:\s*(.+?)(?=Lý do:|$)",
            "reason": r"Lý do:\s*(.+?)(?=Trạng thái:|$)",
            "status": r"Trạng thái:\s*(.+?)(?=$)"
        }
        
        for field, pattern in patterns.items():
            match = re.search(pattern, entry_text, re.DOTALL)
            if match:
                entry_data[field] = match.group(1).strip()
            else:
                entry_data[field] = None
                
        return entry_data
    
    def crawl(self):
        """Crawl the website using Selenium and extract power outage schedule data."""
        print(f"Crawling data from {self.base_url} using Selenium...")
        
        try:
            # Navigate to the target URL
            self.driver.get(self.base_url)
            
            # Wait for the page to load completely
            time.sleep(5)
            
            # Extract the page source after JavaScript execution
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, "html.parser")
            
            # Find all date section headings
            date_headings = soup.find_all("h3", string=lambda text: text and "Lịch cúp điện An Giang ngày" in text)
            
            all_outage_data = []
            
            for heading in date_headings:
                date_str = self.extract_date_from_heading(heading.text)
                print(f"Processing outage data for date: {date_str}")
                
                # Find all elements after the heading up to the next heading
                next_sibling = heading.find_next_sibling()
                
                entry_texts = []
                current_entry = ""
                
                while next_sibling and next_sibling.name != "h3":
                    if next_sibling.name == "hr":
                        if current_entry.strip():
                            entry_texts.append(current_entry.strip())
                            current_entry = ""
                    elif next_sibling.name == "p":
                        current_entry += next_sibling.text + "\n"
                    
                    next_sibling = next_sibling.find_next_sibling()
                
                # Add the last entry if it exists
                if current_entry.strip():
                    entry_texts.append(current_entry.strip())
                
                # Parse each entry text
                for entry_text in entry_texts:
                    if "Điện lực:" in entry_text:
                        entry_data = self.parse_outage_entry(entry_text)
                        entry_data["crawled_date"] = date_str
                        all_outage_data.append(entry_data)
            
            return all_outage_data
            
        except Exception as e:
            print(f"Error during crawling: {e}")
            return []
        finally:
            # Always close the browser
            self.driver.quit()
    
    def save_to_csv(self, data, filename="an_giang_power_outage_selenium.csv"):
        """Save the parsed data to a CSV file."""
        if not data:
            print("No data to save.")
            return
        
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False, encoding="utf-8-sig")
        print(f"Data saved to {filename}")
    
    def save_to_json(self, data, filename="an_giang_power_outage_selenium.json"):
        """Save the parsed data to a JSON file."""
        if not data:
            print("No data to save.")
            return
        
        df = pd.DataFrame(data)
        df.to_json(filename, orient="records", force_ascii=False, indent=4)
        print(f"Data saved to {filename}")


if __name__ == "__main__":
    crawler = LichCupDienSeleniumCrawler(headless=True)
    outage_data = crawler.crawl()
    
    if outage_data:
        print(f"Found {len(outage_data)} power outage entries.")
        crawler.save_to_csv(outage_data)
        crawler.save_to_json(outage_data)
    else:
        print("No power outage data found.") 