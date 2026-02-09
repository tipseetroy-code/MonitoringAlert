#!/usr/bin/env python3
import requests
from requests.auth import HTTPBasicAuth

CONFLUENCE_USER = "porselvi.baskar@in.ey.com"
CONFLUENCE_API_TOKEN = "ATATT3xFfGF0-WHOBSYuutVqq3IqCmK-8JfHOPb4-7t8SsugMHS3sTH1KFkRFlTStkN3q83yLGCqLdUA5CT-KQWpIO3PozMRODm_2duyA4XzkUN1SLAY9iz6oGNaNF-ZiZtvcEFH9iQIN60yQFiyk8vxeSXLTbskdASYlxUk7G9XqAm1cYU5fqI=06ACD07B"
CONFLUENCE_BASE_URL = "https://teammeenakshi.atlassian.net"

# Get all spaces
try:
    url = f"{CONFLUENCE_BASE_URL}/rest/api/space"
    response = requests.get(
        url,
        auth=HTTPBasicAuth(CONFLUENCE_USER, CONFLUENCE_API_TOKEN),
        headers={"Content-Type": "application/json"}
    )
    response.raise_for_status()
    
    spaces = response.json()
    print("Available Spaces:")
    for space in spaces.get('results', []):
        print(f"  - {space['name']} (Key: {space['key']})")
    
    # Get pages from first space
    if spaces.get('results'):
        space_key = spaces['results'][0]['key']
        print(f"\nFetching pages from space: {space_key}")
        
        url = f"{CONFLUENCE_BASE_URL}/rest/api/content?spaceKey={space_key}&limit=50"
        response = requests.get(
            url,
            auth=HTTPBasicAuth(CONFLUENCE_USER, CONFLUENCE_API_TOKEN),
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        
        pages = response.json()
        print(f"\nPages in {space_key}:")
        for page in pages.get('results', []):
            print(f"  - ID: {page['id']}, Title: {page.get('title', 'N/A')}")
            
except Exception as e:
    print(f"Error: {e}")
    if hasattr(e, 'response') and hasattr(e.response, 'text'):
        print(f"Response: {e.response.text[:500]}")
