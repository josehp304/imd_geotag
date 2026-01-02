import urllib.request
import urllib.error
import urllib.parse
import re
import time
import sys
from datetime import datetime, timedelta, timezone

OUTPUT_FILE = "ogimet_data.txt"
MAX_RETRIES = 3
TIMEOUT = 30 # seconds

def get_latest_synop_time():
    """
    Returns the datetime of the most recent synoptic hour (00,03,06,09,12,15,18,21 UTC).·
    """
    now = datetime.now(timezone.utc)
    
    # Calculate difference to previous 3-hour mark
    excess_hours = now.hour % 3
    
    # Create the synop time
    synop_time = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=excess_hours)
    
    return synop_time

def build_ogimet_url(start_dt=None, end_dt=None):
    """
    Builds the Ogimet URL for the target time range.
    If no times provided, defaults to latest synop time window (+/- 30 mins).
    """
    if start_dt is None or end_dt is None:
        target_time = get_latest_synop_time()
        # Default behavior: target specific hour (server gives +/- 30m)
        start_dt = target_time
        end_dt = target_time
        
    base_url = "https://www.ogimet.com/display_synopsc2.php"
    
    params = {
        "lang": "en",
        "estado": "India",
        "tipo": "ALL",
        "ord": "REV",
        "nil": "SI",
        "fmt": "txt",
        # Start Time
        "ano": start_dt.year,
        "mes": start_dt.month,
        "day": start_dt.day,
        "hora": start_dt.hour,
        # End Time
        "anof": end_dt.year,
        "mesf": end_dt.month,
        "dayf": end_dt.day,
        "horaf": end_dt.hour,
        "send": "send"
    }
    
    query_string = urllib.parse.urlencode(params)
    full_url = f"{base_url}?{query_string}"
    print(f"Full URL: {full_url}")
    
    return full_url

def fetch_url(url, retries=MAX_RETRIES):
    """
    Fetches content from the URL with retries and a User-Agent header.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    req = urllib.request.Request(url, headers=headers)
    
    for attempt in range(retries):
        try:
            print(f"Fetching data... (Attempt {attempt + 1}/{retries})")
            with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
                return response.read().decode('utf-8', errors='replace')
        except urllib.error.URLError as e:
            print(f"Error fetching URL: {e}")
            if attempt < retries - 1:
                sleep_time = 2 * (attempt + 1)
                print(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
            else:
                print("Max retries reached. Exiting.")
                raise
        except Exception as e:
             print(f"Unexpected error: {e}")
             raise

def parse_content(content):
    """
    Extracts content within <pre> tags. Handles missing closing tag.
    """
    print("Parsing content...")
    start_match = re.search(r'<pre>', content, re.IGNORECASE)
    
    if not start_match:
        raise ValueError("No <pre> tag found in the response.")
    
    start_index = start_match.end()
    
    # Try to find closing tag, but don't fail if missing (truncated response)
    end_match = re.search(r'</pre>', content[start_index:], re.IGNORECASE)
    
    if end_match:
        extracted = content[start_index : start_index + end_match.start()]
    else:
        print("Warning: Closing </pre> tag not found. Content might be truncated. Extracting remaining content.")
        extracted = content[start_index:]
        
    return extracted.strip()

def get_data_for_range(start_dt, end_dt):
    """Refactored main logic callable from other modules"""
    url = build_ogimet_url(start_dt, end_dt)
    html_content = fetch_url(url)
    data = parse_content(html_content)
    return data

def main():
    try:
        # Build URL dynamically for the latest synoptic hour
        data = get_data_for_range(None, None)
        
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(data)
            
        print("-" * 30)
        print(f"Success! Data saved to '{OUTPUT_FILE}'")
        print("-" * 30)
        
        # Preview
        lines = data.split('\n')
        print(f"Total lines extracted: {len(lines)}")
        print("First 5 lines preview:")
        for line in lines[:5]:
            print(line)
            
    except Exception as e:
        print(f"Failed to complete operation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
