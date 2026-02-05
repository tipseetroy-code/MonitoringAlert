#!/usr/bin/env python3
"""
Script to add SSL/Vault SOP documentation to Confluence page
"""

import requests
import json
import os
from base64 import b64encode

# Confluence Configuration
CONFLUENCE_URL = "https://teammeenakshi.atlassian.net"
CONFLUENCE_SPACE = "AgAH"  # Extract from URL path
CONFLUENCE_PAGE_ID = os.getenv("CONFLUENCE_PAGE_ID", "458754")  # Update with actual page ID
CONFLUENCE_USER = "porselvi.baskar@in.ey.com"
CONFLUENCE_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN", "your_token_here")

def get_page_content(page_id):
    """Retrieve current page content"""
    url = f"{CONFLUENCE_URL}/rest/api/3/pages/{page_id}"
    
    auth = b64encode(f"{CONFLUENCE_USER}:{CONFLUENCE_API_TOKEN}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "Accept": "application/json"
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error retrieving page: {response.status_code}")
        print(response.text)
        return None

def update_page_content(page_id, title, content, version):
    """Update Confluence page with new content"""
    url = f"{CONFLUENCE_URL}/rest/api/3/pages/{page_id}"
    
    auth = b64encode(f"{CONFLUENCE_USER}:{CONFLUENCE_API_TOKEN}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    payload = {
        "id": page_id,
        "type": "page",
        "title": title,
        "space": {"key": CONFLUENCE_SPACE},
        "body": {
            "storage": {
                "value": content,
                "representation": "storage"
            }
        },
        "version": {
            "number": version + 1
        }
    }
    
    response = requests.put(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        print("✅ Page updated successfully!")
        return True
    else:
        print(f"❌ Error updating page: {response.status_code}")
        print(response.text)
        return False

def markdown_to_confluence_storage(markdown_content):
    """
    Convert markdown to Confluence storage format (simplified version)
    Note: For production, use a proper markdown to Confluence converter
    """
    # Read the markdown file
    with open("CONFLUENCE_SOP_TEMPLATE.md", "r") as f:
        content = f.read()
    
    # Simple conversion (you may want to use a library like "md2cf")
    # For now, we'll return the content wrapped in a code block
    storage_content = f"""
<ac:structured-macro ac:name="code">
  <ac:parameter ac:name="language">markdown</ac:parameter>
  <ac:parameter ac:name="title">SSL Certificate & Vault Management SOP</ac:parameter>
  <ac:plain-text-body><![CDATA[
{content}
]]></ac:plain-text-body>
</ac:structured-macro>
"""
    
    return storage_content

def main():
    print("=" * 60)
    print("SSL/Vault SOP - Confluence Update Script")
    print("=" * 60)
    
    print("\n1. Retrieving current page...")
    page = get_page_content(CONFLUENCE_PAGE_ID)
    
    if not page:
        print("❌ Failed to retrieve page")
        return
    
    current_version = page.get("version", {}).get("number", 0)
    print(f"✅ Current version: {current_version}")
    
    print("\n2. Reading SOP content...")
    with open("CONFLUENCE_SOP_TEMPLATE.md", "r") as f:
        sop_content = f.read()
    print(f"✅ SOP content loaded ({len(sop_content)} chars)")
    
    print("\n3. Converting to Confluence format...")
    confluence_content = markdown_to_confluence_storage(sop_content)
    print("✅ Format converted")
    
    print("\n4. Updating Confluence page...")
    page_title = "SSL Certificate & Vault Management SOP"
    
    if update_page_content(CONFLUENCE_PAGE_ID, page_title, confluence_content, current_version):
        print("✅ Update completed!")
        print(f"\n📖 Page URL: {CONFLUENCE_URL}/wiki/spaces/{CONFLUENCE_SPACE}/pages/{CONFLUENCE_PAGE_ID}")
    else:
        print("❌ Update failed")

if __name__ == "__main__":
    main()
