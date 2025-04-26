import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
from datetime import datetime
import os
import sys

def load_data(file_path):
    """Load data from CSV or JSON file."""
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' does not exist.")
        return None
    
    if file_path.endswith('.csv'):
        return pd.read_csv(file_path)
    elif file_path.endswith('.json'):
        return pd.read_json(file_path)
    else:
        print(f"Error: Unsupported file format. Please provide CSV or JSON.")
        return None

def generate_visualizations(data, output_dir='visualizations'):
    """Generate visualizations from the power outage data."""
    if data is None or data.empty:
        print("No data to visualize.")
        return
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Set the style
    sns.set(style="whitegrid")
    plt.rcParams.update({'figure.figsize': (12, 8)})
    
    # 1. Count outages by province (if province column exists)
    if 'province' in data.columns:
        plt.figure(figsize=(14, 8))
        province_counts = data['province'].value_counts()
        sns.barplot(x=province_counts.index, y=province_counts.values)
        plt.title('Number of Power Outages by Province', fontsize=16)
        plt.xlabel('Province', fontsize=14)
        plt.ylabel('Number of Outages', fontsize=14)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(f"{output_dir}/outages_by_province.png")
        plt.close()
    
    # 2. Count outages by reason
    plt.figure(figsize=(14, 8))
    reason_counts = data['reason'].value_counts().head(10)  # Top 10 reasons
    sns.barplot(x=reason_counts.values, y=reason_counts.index)
    plt.title('Top Reasons for Power Outages', fontsize=16)
    plt.xlabel('Number of Outages', fontsize=14)
    plt.ylabel('Reason', fontsize=14)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/outages_by_reason.png")
    plt.close()
    
    # 3. Count outages by status
    plt.figure(figsize=(12, 6))
    status_counts = data['status'].value_counts()
    sns.barplot(x=status_counts.index, y=status_counts.values)
    plt.title('Power Outages by Status', fontsize=16)
    plt.xlabel('Status', fontsize=14)
    plt.ylabel('Number of Outages', fontsize=14)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(f"{output_dir}/outages_by_status.png")
    plt.close()
    
    # 4. Extract date information for time-based analysis
    # Try to convert date column to datetime if it exists
    if 'date' in data.columns:
        try:
            # Extract dates from various formats
            dates = []
            for date_str in data['date']:
                if pd.isna(date_str):
                    dates.append(None)
                    continue
                    
                # Try different date formats
                date_formats = [
                    "%d tháng %m năm %Y",  # Example: "26 tháng 4 năm 2025"
                    "%d/%m/%Y",            # Example: "26/04/2025"
                ]
                
                parsed_date = None
                for fmt in date_formats:
                    try:
                        parsed_date = datetime.strptime(date_str, fmt)
                        break
                    except (ValueError, TypeError):
                        continue
                
                dates.append(parsed_date)
            
            # Create a new column with extracted dates
            data['parsed_date'] = dates
            
            # Count outages by date
            date_counts = data['parsed_date'].dropna().dt.date.value_counts().sort_index()
            
            if not date_counts.empty:
                plt.figure(figsize=(14, 8))
                plt.bar(date_counts.index, date_counts.values)
                plt.title('Power Outages by Date', fontsize=16)
                plt.xlabel('Date', fontsize=14)
                plt.ylabel('Number of Outages', fontsize=14)
                plt.xticks(rotation=45, ha='right')
                plt.tight_layout()
                plt.savefig(f"{output_dir}/outages_by_date.png")
                plt.close()
        except Exception as e:
            print(f"Error processing dates: {e}")
    
    # 5. Analyze power companies
    if 'power_company' in data.columns:
        plt.figure(figsize=(14, 8))
        company_counts = data['power_company'].value_counts().head(10)  # Top 10 companies
        sns.barplot(x=company_counts.values, y=company_counts.index)
        plt.title('Top Power Companies with Outages', fontsize=16)
        plt.xlabel('Number of Outages', fontsize=14)
        plt.ylabel('Power Company', fontsize=14)
        plt.tight_layout()
        plt.savefig(f"{output_dir}/outages_by_company.png")
        plt.close()
    
    print(f"Visualizations have been saved to the '{output_dir}' directory.")

def main():
    parser = argparse.ArgumentParser(description="Visualize power outage data")
    parser.add_argument("file", help="Path to the CSV or JSON file containing power outage data")
    parser.add_argument("--output", default="visualizations", help="Output directory for visualizations")
    
    args = parser.parse_args()
    
    data = load_data(args.file)
    if data is not None:
        print(f"Loaded data with {len(data)} entries.")
        print("Generating visualizations...")
        generate_visualizations(data, args.output)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main() 