# backend/integrations/tableau_client.py
"""
Tableau Server Client - Authenticates and fetches vulnerability data from Tableau
Supports both Personal Access Token (PAT) and username/password authentication
"""

import os
import logging
from typing import List, Dict, Optional
import tableauserverclient as TSC
import pandas as pd

logger = logging.getLogger(__name__)


class TableauVulnerabilityClient:
    """Client for fetching vulnerability data from Tableau Server/Cloud"""
    
    def __init__(self):
        self.server_url = os.getenv("TABLEAU_SERVER", "https://prod-in-a.online.tableau.com")
        self.site_id = os.getenv("TABLEAU_SITE_ID", "porselvibaskar-51e402764b")
        self.username = os.getenv("TABLEAU_USERNAME", "")
        self.password = os.getenv("TABLEAU_PASSWORD", "")
        self.pat_name = os.getenv("TABLEAU_PAT_NAME", "")
        self.pat_value = os.getenv("TABLEAU_PAT_VALUE", "")
        
        self.server = None
        self.auth = None
        
    def authenticate(self) -> bool:
        """
        Authenticate with Tableau Server using PAT (preferred) or username/password
        Returns True if successful, False otherwise
        """
        try:
            # Create server object
            tableau_auth = TSC.TableauAuth(
                username=self.username,
                password=self.password,
                site_id=self.site_id
            )
            
            # Use PAT if available (more secure)
            if self.pat_name and self.pat_value:
                logger.info("🔐 Authenticating with Tableau using Personal Access Token")
                tableau_auth = TSC.PersonalAccessTokenAuth(
                    token_name=self.pat_name,
                    personal_access_token=self.pat_value,
                    site_id=self.site_id
                )
            else:
                logger.info("🔐 Authenticating with Tableau using username/password")
            
            self.server = TSC.Server(self.server_url, use_server_version=True)
            self.server.auth.sign_in(tableau_auth)
            
            logger.info(f"✅ Successfully authenticated with Tableau: {self.server_url}")
            logger.info(f"📊 Site: {self.site_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Tableau authentication failed: {e}")
            return False
    
    def sign_out(self):
        """Sign out from Tableau Server"""
        if self.server:
            try:
                self.server.auth.sign_out()
                logger.info("🔓 Signed out from Tableau")
            except Exception as e:
                logger.error(f"Error signing out: {e}")
    
    def fetch_view_data(self, view_name: str = None, workbook_name: str = None) -> List[Dict]:
        """
        Fetch data from a Tableau view/workbook
        Returns list of vulnerability dictionaries
        """
        vulnerabilities = []
        
        try:
            if not self.server:
                if not self.authenticate():
                    logger.error("❌ Cannot fetch data - authentication failed")
                    return vulnerabilities
            
            # Get all workbooks
            all_workbooks, pagination = self.server.workbooks.get()
            logger.info(f"📚 Found {pagination.total_available} workbooks")
            
            # Find the vulnerability workbook
            target_workbook = None
            for wb in all_workbooks:
                logger.info(f"Workbook: {wb.name} (ID: {wb.id})")
                if workbook_name and workbook_name.lower() in wb.name.lower():
                    target_workbook = wb
                    break
                # If no workbook name specified, use first one or look for 'vulnerability' in name
                if not workbook_name and ('vulnerability' in wb.name.lower() or 'vuln' in wb.name.lower()):
                    target_workbook = wb
                    break
            
            if not target_workbook and all_workbooks:
                # Default to first workbook if nothing found
                target_workbook = all_workbooks[0]
                logger.info(f"Using default workbook: {target_workbook.name}")
            
            if not target_workbook:
                logger.warning("⚠️ No workbooks found")
                return vulnerabilities
            
            logger.info(f"📊 Using workbook: {target_workbook.name}")
            
            # Get views from the workbook
            self.server.workbooks.populate_views(target_workbook)
            
            if not target_workbook.views:
                logger.warning(f"⚠️ No views found in workbook {target_workbook.name}")
                return vulnerabilities
            
            # Use the first view or specified view
            target_view = None
            for view in target_workbook.views:
                logger.info(f"View: {view.name} (ID: {view.id})")
                if view_name and view_name.lower() in view.name.lower():
                    target_view = view
                    break
            
            if not target_view:
                target_view = target_workbook.views[0]
                logger.info(f"Using default view: {target_view.name}")
            
            # Download view data as CSV
            logger.info(f"📥 Downloading data from view: {target_view.name}")
            self.server.views.populate_csv(target_view)
            
            # Parse CSV data
            if hasattr(target_view, 'csv'):
                import io
                csv_data = io.StringIO(target_view.csv.decode('utf-8'))
                df = pd.read_csv(csv_data)
                
                # Convert DataFrame to list of dictionaries
                vulnerabilities = df.to_dict('records')
                logger.info(f"✅ Fetched {len(vulnerabilities)} vulnerabilities from Tableau")
            else:
                logger.warning("⚠️ No CSV data available from view")
            
        except Exception as e:
            logger.error(f"❌ Error fetching Tableau data: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            self.sign_out()
        
        return vulnerabilities
    
    def update_vulnerability_status(self, cve_id: str, status: str) -> bool:
        """
        Update vulnerability status in Tableau
        Note: Tableau doesn't support direct data updates via API
        This would require using Tableau's Data API or updating the underlying datasource
        """
        logger.warning("⚠️ Tableau API doesn't support direct data updates")
        logger.info(f"To update {cve_id} to {status}, you need to:")
        logger.info("1. Update the underlying database/datasource")
        logger.info("2. Refresh the extract in Tableau")
        logger.info("3. Use Tableau's Hyper API for direct updates")
        
        # For now, return True and log the update
        # In production, implement using Tableau Hyper API or database update
        return False


# Singleton instance
_tableau_client = None

def get_tableau_client() -> TableauVulnerabilityClient:
    """Get or create Tableau client singleton"""
    global _tableau_client
    if _tableau_client is None:
        _tableau_client = TableauVulnerabilityClient()
    return _tableau_client
