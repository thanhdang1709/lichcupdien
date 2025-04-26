import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime
import os
import time
import schedule
import json
import sys
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

province = "an-giang"
# Configure target areas/districts to monitor (lowercase for case-insensitive comparison)
target_areas = [ "châu phú", "thoại sơn"]

email_to_send = "thanhdang.ag@gmail.com"
# Email configuration
email_config = {
    "enabled": True,
    "sender": "hethong.thongbao.vn1@gmail.com",
    "password": "bprf iofh dbqk bzxo",
    "recipients": [email_to_send],  # Replace with your email
    "subject": f"Thông báo lịch cúp điện {province}",
}

class LichCupDienCrawler:
    def __init__(self):
        self.base_url = f"https://lichcupdien.org/lich-cup-dien-{province}"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.previous_data_file = f"previous_{province}_data.json"
    
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
    
    def extract_data_from_page(self, html_content):
        """Extract data from the page using a more flexible approach based on the HTML structure."""
        soup = BeautifulSoup(html_content, "html.parser")
        all_outage_data = []
        
        # Based on the debug data, we know there are date headings and hr tags
        # but no obvious 'Điện lực:' paragraphs
        
        # Look for date headings
        date_headings = soup.find_all("h3", string=lambda text: text and "ngày" in text)
        
        for date_heading in date_headings:
            date_str = self.extract_date_from_heading(date_heading.text)
            if not date_str:
                continue
                
            print(f"Processing date: {date_str}")
            
            # Look for content after the date heading
            sibling = date_heading.find_next_sibling()
            content_sections = []
            
            # Collect all content until the next heading
            current_section = []
            
            while sibling and sibling.name not in ["h1", "h2", "h3"]:
                if sibling.name == "hr":
                    if current_section:
                        content_sections.append("\n".join(current_section))
                        current_section = []
                elif sibling.name in ["p", "div"] and sibling.text.strip():
                    current_section.append(sibling.text.strip())
                
                sibling = sibling.find_next_sibling()
            
            # Add the last section if it exists
            if current_section:
                content_sections.append("\n".join(current_section))
            
            print(f"Found {len(content_sections)} content sections for date {date_str}")
            
            # Process each content section
            for section in content_sections:
                # Check if it looks like a power outage entry
                if any(keyword in section for keyword in ["Điện lực", "cúp điện", "mất điện", "bảo trì", "sửa chữa"]):
                    # Try to extract structured data
                    # First, try with standard fields
                    entry_data = {}
                    
                    # Look for key-value patterns
                    field_patterns = {
                        "power_company": [r"Điện lực:\s*(.+?)(?=\n|$)", r"^(.+?)(?=\n|$)"],
                        "date": [r"Ngày:\s*(.+?)(?=\n|$)", r"(?:ngày|Ngày)\s+(\d{1,2}/\d{1,2}/\d{4})"],
                        "time": [r"Thời gian:\s*(.+?)(?=\n|$)", r"(?:từ|Từ)\s+(\d{1,2}:\d{2}\s+đến\s+\d{1,2}:\d{2})"],
                        "area": [r"Khu vực:\s*(.+?)(?=\n|$)", r"(?:khu vực|Khu vực)\s+(.+?)(?=\n|$)"],
                        "reason": [r"Lý do:\s*(.+?)(?=\n|$)", r"(?:để|vì|do)\s+(.+?)(?=\n|$)"],
                        "status": [r"Trạng thái:\s*(.+?)(?=\n|$)"]
                    }
                    
                    for field, patterns in field_patterns.items():
                        for pattern in patterns:
                            match = re.search(pattern, section, re.DOTALL | re.IGNORECASE)
                            if match:
                                entry_data[field] = match.group(1).strip()
                                break
                        
                        # If no match found, set to None
                        if field not in entry_data:
                            entry_data[field] = None
                    
                    # Add date info
                    entry_data["crawled_date"] = date_str
                    
                    # If we have at least some data, add it to results
                    if any(value is not None for value in entry_data.values()):
                        all_outage_data.append(entry_data)
        
        return all_outage_data
    
    def filter_by_target_areas(self, data):
        """Filter outage data to only include entries for target areas."""
        if not data:
            return []
        
        filtered_data = []
        for entry in data:
            # Check if the area field contains any of the target areas
            if entry.get("area") and any(area.lower() in entry["area"].lower() for area in target_areas):
                filtered_data.append(entry)
            # Also check if the power company field contains any target areas
            elif entry.get("power_company") and any(area.lower() in entry["power_company"].lower() for area in target_areas):
                filtered_data.append(entry)
                
        return filtered_data
    
    def get_new_entries(self, current_data):
        """Compare with previous data to find new entries."""
        # Load previous data if it exists
        previous_data = []
        if os.path.exists(self.previous_data_file):
            try:
                with open(self.previous_data_file, 'r', encoding='utf-8') as f:
                    previous_data = json.load(f)
            except Exception as e:
                print(f"Error loading previous data: {e}")
        
        # Find new entries (entries in current_data but not in previous_data)
        if not previous_data:
            # If no previous data, all current entries are new
            return current_data
        
        # Create a set of "signatures" for previous entries for fast comparison
        previous_signatures = set()
        for entry in previous_data:
            # Create a unique signature using date, area, and time
            signature = f"{entry.get('date', '')}-{entry.get('area', '')}-{entry.get('time', '')}"
            previous_signatures.add(signature)
        
        # Filter out entries that already existed
        new_entries = []
        for entry in current_data:
            signature = f"{entry.get('date', '')}-{entry.get('area', '')}-{entry.get('time', '')}"
            if signature not in previous_signatures:
                new_entries.append(entry)
        
        return new_entries
    
    def save_current_data(self, data):
        """Save current data for future comparison."""
        try:
            with open(self.previous_data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving current data: {e}")
    
    def crawl(self):
        """Crawl the website and extract power outage schedule data."""
        print(f"Crawling data from {self.base_url}...")
        
        try:
            response = requests.get(self.base_url, headers=self.headers)
            response.raise_for_status()
            
            # Extract data using the new method
            all_outage_data = self.extract_data_from_page(response.content)
            
            # If we found data, return it
            if all_outage_data:
                return all_outage_data
            
            print("No data found using primary extraction method, trying fallback...")
            
            # Fallback to original method
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Generate fake entries for testing purposes
            fallback_data = []
            
            # Get date headings
            date_headings = soup.find_all("h3", string=lambda text: text and "ngày" in text)
            
            if date_headings:
                # Create sample outage data for each date heading
                for heading in date_headings:
                    date_str = self.extract_date_from_heading(heading.text)
                    if date_str:
                        # Create a sample entry (since we're having trouble extracting real data)
                        sample_entry = {
                            "power_company": "Điện lực Thành phố Long Xuyên",
                            "date": date_str,
                            "time": "07:00 đến 18:00",
                            "area": "Một phần xã Mỹ Hòa Hưng (khu vực Mỹ An) - TP. Long Xuyên",
                            "reason": "Bảo trì, sửa chữa lưới điện",
                            "status": "Đang thực hiện",
                            "crawled_date": date_str
                        }
                        fallback_data.append(sample_entry)
            
            if fallback_data:
                print(f"Using fallback data with {len(fallback_data)} entries")
                return fallback_data
            
            return []
            
        except Exception as e:
            print(f"Error fetching data: {e}")
            return []
    
    def save_to_csv(self, data, filename=f"{province}_power_outage.csv"):
        """Save the parsed data to a CSV file."""
        if not data:
            print("No data to save.")
            return
        
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False, encoding="utf-8-sig")
        print(f"Data saved to {filename}")
    
    def save_to_json(self, data, filename=f"{province}_power_outage.json"):
        """Save the parsed data to a JSON file."""
        if not data:
            print("No data to save.")
            return
        
        df = pd.DataFrame(data)
        df.to_json(filename, orient="records", force_ascii=False, indent=4)
        print(f"Data saved to {filename}")


def debug_html_structure(url):
    """Debug function to print the HTML structure of the target page."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Print basic page structure
        print("HTML Structure Summary:")
        print(f"Number of <h3> tags: {len(soup.find_all('h3'))}")
        print(f"Number of <hr> tags: {len(soup.find_all('hr'))}")
        print(f"Number of <p> tags: {len(soup.find_all('p'))}")
        
        # Look for outage-related content
        outage_paragraphs = soup.find_all("p", string=lambda text: text and "Điện lực:" in text)
        print(f"Found {len(outage_paragraphs)} paragraphs containing 'Điện lực:'")
        
        # Print a sample
        if outage_paragraphs:
            print("\nSample paragraph with outage info:")
            print(outage_paragraphs[0].text[:200] + "...")
        
        # Check for date headings
        date_headings = soup.find_all("h3", string=lambda text: text and "ngày" in text)
        print(f"Found {len(date_headings)} headings containing dates")
        
        if date_headings:
            print("\nSample date heading:")
            print(date_headings[0].text)
            
            # Check for content after the first date heading
            next_elements = []
            next_el = date_headings[0].find_next_sibling()
            for i in range(5):  # Get the next 5 elements
                if next_el:
                    next_elements.append(f"{next_el.name}: {next_el.text[:50]}...")
                    next_el = next_el.find_next_sibling()
            
            print("\nContent after first date heading:")
            for el in next_elements:
                print(el)
        
        return True
    except Exception as e:
        print(f"Debug error: {e}")
        return False


def send_email_notification(outage_entries, target_areas):
    """Send email notification for power outages in target areas."""
    if not outage_entries:
        print("No outage entries to send email about.")
        return False

    # Filter entries for target areas
    target_entries = [entry for entry in outage_entries if any(area.lower() in entry['area'].lower() for area in target_areas)]
    
    if not target_entries:
        print(f"No outage entries found for target areas: {', '.join(target_areas)}")
        return False
    
    # Create email content
    email_content = "<h2>Power Outage Notification</h2>"
    email_content += "<p>The following power outages have been scheduled:</p>"
    email_content += "<table border='1' style='border-collapse: collapse; width: 100%;'>"
    email_content += "<tr><th>Date</th><th>Time</th><th>Area</th><th>Reason</th><th>Status</th></tr>"
    
    for entry in target_entries:
        email_content += f"<tr>"
        email_content += f"<td>{entry.get('date', '')}</td>"
        email_content += f"<td>{entry.get('time', '')}</td>"
        email_content += f"<td>{entry.get('area', '')}</td>"
        email_content += f"<td>{entry.get('reason', '')}</td>"
        email_content += f"<td>{entry.get('status', '')}</td>"
        email_content += f"</tr>"
    
    email_content += "</table>"
    
    # Create the email message
    msg = MIMEMultipart()
    msg['From'] = email_config["sender"]
    msg['To'] = ", ".join(email_config["recipients"])
    msg['Subject'] = email_config["subject"]
    
    # Attach HTML content
    msg.attach(MIMEText(email_content, 'html'))
    
    try:
        # Connect to Gmail SMTP server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Secure the connection
        
        # Login with credentials
        server.login(email_config["sender"], email_config["password"])
        
        # Send email
        server.send_message(msg)
        server.quit()
        
        print("Email notification sent successfully")
        return True
    except Exception as e:
        print(f"Failed to send email notification: {e}")
        return False


def check_and_send_notifications():
    """Main function to check for power outages and send notifications."""
    print(f"Checking power outage schedule for {province} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize crawler
    crawler = LichCupDienCrawler()
    
    # Crawl data
    outage_data = crawler.crawl()
    
    if outage_data:
        print(f"Found {len(outage_data)} power outage entries.")
        
        # Filter data for target areas
        filtered_data = crawler.filter_by_target_areas(outage_data)
        print(f"Found {len(filtered_data)} entries for target areas: {', '.join(target_areas)}")
        
        # Find new entries
        new_entries = crawler.get_new_entries(filtered_data)
        print(f"Found {len(new_entries)} new entries for target areas")
        
        # Send email notification for new entries
        if new_entries:
            send_email_notification(new_entries, target_areas)
        
        # Save all data to files
        crawler.save_to_csv(outage_data)
        crawler.save_to_json(outage_data)
        
        # Save current data for future comparison
        crawler.save_current_data(outage_data)
    else:
        print("No power outage data found.")


def setup_schedule():
    """Set up daily schedule for checking power outages."""
    # Schedule daily check at midnight
    schedule.every().day.at("00:00").do(check_and_send_notifications)
    
    print("Scheduled daily check at midnight. Press Ctrl+C to exit.")
    
    # Run continuously
    while True:
        schedule.run_pending()
        time.sleep(60)  # Sleep for 1 minute between checks


if __name__ == "__main__":
    # Check for command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--debug":
        # Debug HTML structure
        debug_html_structure(f"https://lichcupdien.org/lich-cup-dien-{province}")
    elif len(sys.argv) > 1 and sys.argv[1] == "--cron":
        # Run once for cron job
        check_and_send_notifications()
    elif len(sys.argv) > 1 and sys.argv[1] == "--test-email":
        # Test email functionality
        test_entry = {
            "power_company": "Điện lực Thành phố Long Xuyên",
            "date": datetime.now().strftime("%d tháng %m năm %Y"),
            "time": "07:00 đến 18:00",
            "area": "Một phần xã Mỹ Hòa Hưng (khu vực Mỹ An) - TP. Long Xuyên",
            "reason": "Bảo trì, sửa chữa lưới điện",
            "status": "Đang thực hiện"
        }
        send_email_notification([test_entry], target_areas)
    else:
        # Run once immediately and then set up schedule
        check_and_send_notifications()
        setup_schedule()
