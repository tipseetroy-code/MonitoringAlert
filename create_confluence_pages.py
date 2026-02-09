#!/usr/bin/env python3
import requests
import json
from requests.auth import HTTPBasicAuth

CONFLUENCE_USER = "porselvi.baskar@in.ey.com"
CONFLUENCE_API_TOKEN = "ATATT3xFfGF0-WHOBSYuutVqq3IqCmK-8JfHOPb4-7t8SsugMHS3sTH1KFkRFlTStkN3q83yLGCqLdUA5CT-KQWpIO3PozMRODm_2duyA4XzkUN1SLAY9iz6oGNaNF-ZiZtvcEFH9iQIN60yQFiyk8vxeSXLTbskdASYlxUk7G9XqAm1cYU5fqI=06ACD07B"
CONFLUENCE_BASE_URL = "https://teammeenakshi.atlassian.net"

# App1 content
APP1_CONTENT = """<h1>Trading Platform</h1>
<p><strong>Tags:</strong> trading, stock, investment, real-time, analytics</p>
<h2>Overview</h2>
<p>Real-time stock trading application designed for active traders and investment professionals.</p>
<h2>Key Features</h2>
<ul>
<li>Real-time Stock Quotes: Access live market data for 5,000+ stocks with 15-minute delay</li>
<li>Advanced Charting: Technical analysis tools with 20+ indicators (MA, RSI, MACD, Bollinger Bands)</li>
<li>Trade Execution: Place market, limit, and stop-loss orders instantly</li>
<li>Portfolio Management: Track positions, monitor P&amp;L, and view asset allocation</li>
<li>News Integration: Curated financial news and earnings announcements</li>
<li>Alerts &amp; Notifications: Set custom price alerts and news notifications</li>
<li>Research Tools: Fundamental analysis, ratio comparisons, and peer benchmarking</li>
</ul>
<h2>Technical Stack</h2>
<ul>
<li>Frontend: React 18, TypeScript, Redux</li>
<li>Backend: Python FastAPI with async processing</li>
<li>Database: PostgreSQL with real-time data replication</li>
<li>Message Queue: RabbitMQ for order processing</li>
<li>Cache: Redis for quote caching (1-second TTL)</li>
<li>APIs: IEX Cloud, Alpha Vantage, Finnhub for market data</li>
</ul>
<h2>Performance Specifications</h2>
<ul>
<li>Quote Latency: &lt;100ms for top 100 stocks</li>
<li>Order Execution: &lt;500ms from click to confirmation</li>
<li>Concurrent Users: Supports 10,000+ concurrent traders</li>
<li>Uptime SLA: 99.9% during market hours (9:30 AM - 4:00 PM EST)</li>
</ul>
<h2>Support</h2>
<ul>
<li>Status Page: https://status.trading-platform.io</li>
<li>Support Contact: support@trading-platform.io</li>
</ul>"""

# App2 content
APP2_CONTENT = """<h1>Stock Portfolio Manager</h1>
<p><strong>Tags:</strong> trading, stocks, portfolio, investment, wealth-management</p>
<h2>Overview</h2>
<p>Intelligent portfolio tracking and optimization platform for long-term investors and financial advisors.</p>
<h2>Key Features</h2>
<ul>
<li>Multi-Account Tracking: Consolidate holdings across brokerages</li>
<li>Portfolio Analytics: Asset allocation, risk metrics, diversification analysis</li>
<li>Performance Reporting: Detailed returns analysis with benchmarking</li>
<li>Tax Optimization: Tax-loss harvesting recommendations and reporting</li>
<li>Rebalancing Tools: Automated or manual portfolio rebalancing</li>
<li>Goal Planning: Track progress toward financial goals</li>
<li>Advisor Collaboration: Multi-user access for financial advisors</li>
<li>Dividend Tracking: Monitor dividend payments and reinvestment</li>
</ul>
<h2>Technical Stack</h2>
<ul>
<li>Frontend: Vue.js 3, TypeScript, Vuex store</li>
<li>Backend: Python Django REST Framework</li>
<li>Database: MongoDB for flexible portfolio schemas</li>
<li>Real-time Updates: WebSockets for live price updates</li>
<li>Analytics: Apache Spark for batch processing</li>
<li>Reporting: Jasper Reports for PDF generation</li>
<li>Integration: OAuth 2.0 with major brokerages</li>
</ul>
<h2>Performance Specifications</h2>
<ul>
<li>Portfolio Load Time: &lt;2 seconds for 100+ holdings</li>
<li>Report Generation: &lt;30 seconds for annual reports</li>
<li>Data Refresh: Every 30 seconds during market hours</li>
<li>Concurrent Users: 5,000+ simultaneous users</li>
<li>Uptime SLA: 99.95% availability</li>
</ul>
<h2>Integration Capabilities</h2>
<ul>
<li>Brokerage APIs: Schwab, Fidelity, E*TRADE, Coinbase</li>
<li>Data Providers: IEX Cloud, Morningstar, Bloomberg</li>
<li>Banking: Plaid for account aggregation</li>
<li>Export Formats: CSV, Excel, PDF reports</li>
</ul>
<h2>Support</h2>
<ul>
<li>Knowledge Base: https://help.portfolio-manager.io</li>
<li>Support Email: support@portfolio-manager.io</li>
</ul>"""

def create_page(space_key, title, content):
    """Create a new Confluence page"""
    try:
        url = f"{CONFLUENCE_BASE_URL}/rest/api/content"
        payload = {
            "type": "page",
            "title": title,
            "space": {"key": space_key},
            "body": {
                "storage": {
                    "value": content,
                    "representation": "storage"
                }
            }
        }
        
        response = requests.post(
            url,
            auth=HTTPBasicAuth(CONFLUENCE_USER, CONFLUENCE_API_TOKEN),
            headers={"Content-Type": "application/json"},
            json=payload
        )
        response.raise_for_status()
        
        page_data = response.json()
        page_id = page_data['id']
        print(f"✅ Created '{title}' - Page ID: {page_id}")
        return page_id
        
    except Exception as e:
        print(f"❌ Error creating '{title}': {e}")
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            print(f"   Response: {e.response.text[:300]}")
        return None

def main():
    # Try different space keys that might exist
    possible_spaces = ["CONF", "CONFLUENCE", "APP", "DOC", "DOCS", "WIKI", "~KF879ZY"]
    
    print("Attempting to create Confluence pages...\n")
    
    success_space = None
    for space_key in possible_spaces:
        print(f"Trying space key: {space_key}")
        page_id = create_page(space_key, "App1 - Trading Platform", APP1_CONTENT)
        if page_id:
            success_space = space_key
            print(f"Successfully created in space: {space_key}\n")
            
            # Create App2 in same space
            create_page(space_key, "App2 - Stock Portfolio Manager", APP2_CONTENT)
            break
    
    if not success_space:
        print("\n⚠️  Could not create pages in any space.")
        print("Please:")
        print("1. Create pages manually in Confluence:")
        print("   - App1: 'App1 - Trading Platform'")
        print("   - App2: 'App2 - Stock Portfolio Manager'")
        print("2. Note the page IDs and update frontend/app.py with the correct IDs")
        print("3. Or provide the correct space key and page IDs")

if __name__ == "__main__":
    main()
