import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime
import os
import time
import argparse

class LichCupDienMultiCrawler:
    def __init__(self):
        self.base_url = "https://lichcupdien.org"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.province_urls = {}
    
    def get_province_list(self):
        """Get list of available provinces from the website."""
        try:
            response = requests.get(self.base_url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Look for province links in the footer
            footer_links = soup.select('a[href^="/lich-cup-dien-"]')
            
            for link in footer_links:
                province_name = link.text.strip()
                province_url = link['href']
                if province_name and province_url:
                    self.province_urls[province_name] = self.base_url + province_url if not province_url.startswith("http") else province_url
            
            return self.province_urls
        except requests.exceptions.RequestException as e:
            print(f"Error fetching province list: {e}")
            return {}
    
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
    
    def crawl_province(self, province_url, province_name):
        """Crawl a specific province's page."""
        print(f"Crawling data for {province_name} from {province_url}...")
        
        try:
            response = requests.get(province_url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Find all date section headings - adapt for different naming conventions
            date_headings = soup.find_all("h3", string=lambda text: text and f"Lịch cúp điện {province_name} ngày" in text)
            if not date_headings:
                # Try different pattern if specific province pattern not found
                date_headings = soup.find_all("h3", string=lambda text: text and "Lịch cúp điện" in text and "ngày" in text)
            
            all_outage_data = []
            
            for heading in date_headings:
                date_str = self.extract_date_from_heading(heading.text)
                
                # Find the next section with outage entries
                next_element = heading.find_next_sibling()
                
                # The outage entries are typically separated by <hr> tags
                entry_texts = []
                current_entry = ""
                
                while next_element and next_element.name != "h3":
                    if next_element.name == "hr":
                        if current_entry.strip():
                            entry_texts.append(current_entry.strip())
                            current_entry = ""
                    elif next_element.name == "p":
                        current_entry += next_element.text + "\n"
                    
                    next_element = next_element.find_next_sibling()
                
                # Add the last entry if it exists
                if current_entry.strip():
                    entry_texts.append(current_entry.strip())
                
                # Parse each entry
                for entry_text in entry_texts:
                    if "Điện lực:" in entry_text:
                        entry_data = self.parse_outage_entry(entry_text)
                        entry_data["crawled_date"] = date_str
                        entry_data["province"] = province_name
                        all_outage_data.append(entry_data)
            
            return all_outage_data
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data for {province_name}: {e}")
            return []
    
    def crawl_multiple_provinces(self, province_names=None):
        """Crawl multiple provinces."""
        if not self.province_urls:
            self.get_province_list()
        
        all_data = []
        provinces_to_crawl = {}
        
        # If specific provinces are provided, only crawl those
        if province_names:
            for name in province_names:
                for prov_name, url in self.province_urls.items():
                    if name.lower() in prov_name.lower():
                        provinces_to_crawl[prov_name] = url
                        break
        else:
            provinces_to_crawl = self.province_urls
        
        for province_name, url in provinces_to_crawl.items():
            print(f"Processing {province_name}...")
            province_data = self.crawl_province(url, province_name)
            if province_data:
                all_data.extend(province_data)
                print(f"Found {len(province_data)} entries for {province_name}")
            else:
                print(f"No data found for {province_name}")
            
            # Add delay between requests to be polite
            time.sleep(2)
        
        return all_data
    
    def save_to_csv(self, data, filename="power_outage_data.csv"):
        """Save the parsed data to a CSV file."""
        if not data:
            print("No data to save.")
            return
        
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False, encoding="utf-8-sig")
        print(f"Data saved to {filename}")
    
    def save_to_json(self, data, filename="power_outage_data.json"):
        """Save the parsed data to a JSON file."""
        if not data:
            print("No data to save.")
            return
        
        df = pd.DataFrame(data)
        df.to_json(filename, orient="records", force_ascii=False, indent=4)
        print(f"Data saved to {filename}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crawl power outage data from lichcupdien.org")
    parser.add_argument("--provinces", nargs="+", help="Specific provinces to crawl (e.g. 'An Giang' 'Cần Thơ')")
    parser.add_argument("--list", action="store_true", help="List available provinces")
    parser.add_argument("--output", default="power_outage_data", help="Output filename prefix (without extension)")
    
    args = parser.parse_args()
    
    crawler = LichCupDienMultiCrawler()
    
    if args.list:
        provinces = crawler.get_province_list()
        print("Available provinces:")
        for province in provinces.keys():
            print(f"- {province}")
        exit(0)
    
    if args.provinces:
        print(f"Crawling data for provinces: {', '.join(args.provinces)}")
        data = crawler.crawl_multiple_provinces(args.provinces)
    else:
        print("Crawling data for all provinces...")
        data = crawler.crawl_multiple_provinces()
    
    if data:
        print(f"Found {len(data)} total power outage entries.")
        crawler.save_to_csv(data, f"{args.output}.csv")
        crawler.save_to_json(data, f"{args.output}.json")
    else:
        print("No power outage data found.") 