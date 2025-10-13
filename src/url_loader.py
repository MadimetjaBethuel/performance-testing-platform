import json
import os

def load_urls_from_json(file_path="data/input.json"):
    """Load URLs from JSON file and return as a list."""
    try:
        # Handle both local and Lambda environments
        if not os.path.exists(file_path):
            # Try alternative paths
            alt_paths = [
                "input.json",
                "../data/input.json",
                os.path.join(os.path.dirname(__file__), "../data/input.json")
            ]
            
            for alt_path in alt_paths:
                if os.path.exists(alt_path):
                    file_path = alt_path
                    break
            else:
                raise FileNotFoundError(f"Could not find input.json in any expected location")
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Extract URLs from the JSON structure
        if isinstance(data, list):
            urls = []
            for item in data:
                if isinstance(item, dict) and 'url' in item:
                    urls.append(item['url'])
                elif isinstance(item, str):
                    urls.append(item)
            return urls
        else:
            raise ValueError("JSON file must contain a list of URL objects")
            
    except FileNotFoundError as e:
        print(f"Error loading URLs: {e}")
        # Fallback to default URLs
        return get_default_urls()
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        return get_default_urls()

def get_default_urls():
    """Fallback URLs if JSON file is not available."""
    return [
        "https://gpglook.gauteng.gov.za:443/Pages/wall-of-history.aspx",
        "https://gpglook.gauteng.gov.za:443/Pages/videos.aspx",
        "https://gpglook.gauteng.gov.za:443/Pages/test-page.aspx",
        "https://gpglook.gauteng.gov.za:443/Pages/speeches.aspx",
        "https://gpglook.gauteng.gov.za:443/Pages/services.aspx",
        "https://gpglook.gauteng.gov.za:443/Pages/search-box.aspx",
    ]

def validate_urls(urls):
    """Basic URL validation."""
    valid_urls = []
    for url in urls:
        if url.startswith(('http://', 'https://')):
            valid_urls.append(url)
        else:
            print(f"Skipping invalid URL: {url}")
    return valid_urls