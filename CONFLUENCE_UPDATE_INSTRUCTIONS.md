# Instructions: Adding SSL/Vault SOP to Confluence

## Option 1: Manual Copy-Paste (Easiest)

### Steps:
1. Open Confluence: https://teammeenakshi.atlassian.net/wiki/x/AgAH
2. Click **Edit** button (top right)
3. Go to end of page content
4. Add a new section by clicking **{+}** or pressing Enter
5. Copy content from `CONFLUENCE_SOP_TEMPLATE.md`
6. Paste into Confluence
7. Click **Publish**

---

## Option 2: Using Python Script (Automated)

### Prerequisites:
1. Confluence API Token
   - Go to: https://id.atlassian.com/manage-profile/security/api-tokens
   - Create new token
   - Copy the token

2. Set environment variable:
   ```bash
   export CONFLUENCE_API_TOKEN="your_token_here"
   ```

### Steps:
1. Update `update_confluence_sop.py` with correct page ID:
   ```python
   CONFLUENCE_PAGE_ID = "123456"  # Get from Confluence page URL
   ```

2. Get your page ID:
   - Open page in Confluence
   - Look at URL: `...?pageId=123456`
   - Copy the `pageId` value

3. Run the script:
   ```bash
   python update_confluence_sop.py
   ```

### Script Output:
```
============================================================
SSL/Vault SOP - Confluence Update Script
============================================================

1. Retrieving current page...
✅ Current version: 5

2. Reading SOP content...
✅ SOP content loaded (12500 chars)

3. Converting to Confluence format...
✅ Format converted

4. Updating Confluence page...
✅ Update completed!

📖 Page URL: https://teammeenakshi.atlassian.net/wiki/spaces/AgAH/pages/123456
```

---

## Option 3: Direct HTML/Confluence Format

### If you want to manually format in Confluence:

1. Create new section on page
2. Add heading: **SSL & Vault Management - Standard Operating Procedures**
3. Copy each section from the SOP template
4. Use Confluence formatting:
   - `h1` for main headings
   - `h2` for sub-headings  
   - `code` blocks for shell commands
   - `tables` for troubleshooting

---

## Verification

After adding to Confluence:

1. ✅ Navigate to: https://teammeenakshi.atlassian.net/wiki/x/AgAH
2. ✅ Verify all sections appear:
   - SSL Certificate Renewal SOP
   - Certificate Vaulting SOP (HashiCorp Vault)
   - Quick Reference
3. ✅ Test links work
4. ✅ Verify code blocks are properly formatted
5. ✅ Check table formatting

---

## Files Involved

- **CONFLUENCE_SOP_TEMPLATE.md** - Complete SOP documentation
- **update_confluence_sop.py** - Automated update script
- **CONFLUENCE_UPDATE_INSTRUCTIONS.md** - This file

---

## Next Steps

After SOP is in Confluence:

1. Update all app references to point to the new full page:
   ```
   https://teammeenakshi.atlassian.net/wiki/x/AgAH
   ```

2. Both apps will now link to the full SOP:
   - ✅ Main app: Self Healing tab → SSL Management section
   - ✅ SSL/Vault POC: All tabs reference SOP

3. Team can access complete procedures from Confluence directly

---

## Support

If you need help:
- Confluence API docs: https://developer.atlassian.com/cloud/confluence/rest/v3/
- Contact: devops@example.com
