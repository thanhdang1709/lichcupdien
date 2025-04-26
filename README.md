# Lịch Cúp Điện Crawler

This project crawls power outage schedule data from lichcupdien.org for provinces in Vietnam.

## Features

- Extracts power outage schedule data including:
  - Power company information
  - Outage date and time
  - Affected areas
  - Reason for the outage
  - Status of the outage
- Saves data in both CSV and JSON formats
- Provides three crawler implementations:
  - Regular HTTP requests using requests + BeautifulSoup (app.py)
  - Selenium-based crawler for JavaScript-rendered content (selenium_crawler.py)
  - Multi-province crawler to extract data from multiple provinces (multi_province_crawler.py)
- Data visualization tools to analyze outage patterns (visualize_data.py)

## Requirements

- Python 3.8+
- Required packages (see requirements.txt)
- Chrome browser (for Selenium crawler)
- ChromeDriver (for Selenium crawler)

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/lichcupdien-crawler.git
cd lichcupdien-crawler
```

2. Install the required packages:
```bash
pip install -r requirements.txt
```

3. For the Selenium crawler, ensure you have Chrome browser installed and the appropriate ChromeDriver version matching your Chrome version.

## Usage

### Using the Basic Crawler (An Giang province)

To use the basic crawler (which uses requests and BeautifulSoup):

```bash
python app.py
```

### Using the Selenium Crawler (An Giang province)

To use the Selenium-based crawler (better for JavaScript-rendered content):

```bash
python selenium_crawler.py
```

### Using the Multi-Province Crawler

To see a list of available provinces:

```bash
python multi_province_crawler.py --list
```

To crawl a specific province or provinces:

```bash
python multi_province_crawler.py --provinces "An Giang" "Cần Thơ"
```

To crawl all available provinces:

```bash
python multi_province_crawler.py
```

To specify a custom output filename:

```bash
python multi_province_crawler.py --output my_custom_filename
```

### Visualizing the Data

After collecting data with one of the crawlers, you can visualize it using the visualization tool:

```bash
python visualize_data.py power_outage_data.csv
```

Or if you want to specify a custom output directory for the visualizations:

```bash
python visualize_data.py power_outage_data.csv --output my_visualizations
```

The visualization tool generates the following charts:
- Number of power outages by province (if available)
- Top reasons for power outages
- Power outages by status
- Power outages by date
- Top power companies with outages

## Output

The crawlers will generate the following output files:

- `an_giang_power_outage.csv` and `an_giang_power_outage.json` (for the basic crawler)
- `an_giang_power_outage_selenium.csv` and `an_giang_power_outage_selenium.json` (for the Selenium crawler)
- `power_outage_data.csv` and `power_outage_data.json` (for the multi-province crawler, unless custom filename specified)

The visualization tool will create a directory named `visualizations` (or a custom name if specified) containing PNG images of the charts.

## Data Structure

The output data includes the following fields:

- `power_company`: The power company responsible for the outage
- `date`: The date of the outage
- `time`: The time range of the outage
- `area`: The affected areas
- `reason`: The reason for the outage
- `status`: The status of the outage (e.g., "Đang thực hiện")
- `crawled_date`: The date extracted from the heading
- `province`: The province name (only in multi-province crawler output)

## Notes

- The website structure may change over time, requiring updates to the crawler.
- The Selenium crawler is more robust for handling JavaScript-rendered content but requires additional setup.
- To run the Selenium crawler in headless mode (no browser UI), the default setting is `headless=True`. You can change this by modifying the code.
- The multi-province crawler includes a delay between requests to be respectful of the website's server.
- The visualization tool may need adjustments based on the actual data format received from the website.

## License

MIT

## Disclaimer

This tool is for educational purposes only. Please be respectful of the website's terms of service and robots.txt file. 