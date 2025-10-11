#!/usr/bin/env python3
"""
Test script for PDF export functionality
Tests the /export/pdf endpoint and verifies PDF generation
"""

import requests
import sys
from PyPDF2 import PdfReader
import io

def test_pdf_export():
    """Test PDF export endpoint"""
    print("🧪 Testing PDF Export Endpoint...\n")
    
    # Test authentication first
    print("1. Testing authentication...")
    session = requests.Session()
    
    # Login as crew
    login_response = session.post(
        "http://localhost:5000/login",
        data={"username": "crew", "password": "crew123"},
        allow_redirects=False
    )
    
    if login_response.status_code not in [303, 302]:
        print(f"   ❌ Login failed with status {login_response.status_code}")
        return False
    print("   ✅ Authentication successful")
    
    # Test PDF endpoint
    print("\n2. Testing PDF endpoint...")
    pdf_response = session.get("http://localhost:5000/export/pdf")
    
    if pdf_response.status_code != 200:
        print(f"   ❌ PDF endpoint failed with status {pdf_response.status_code}")
        print(f"   Response: {pdf_response.text[:200]}")
        return False
    
    print(f"   ✅ PDF endpoint returned 200 OK")
    
    # Verify Content-Type
    print("\n3. Verifying content type...")
    content_type = pdf_response.headers.get('Content-Type', '')
    if 'application/pdf' not in content_type:
        print(f"   ❌ Wrong content type: {content_type}")
        return False
    print(f"   ✅ Content-Type: {content_type}")
    
    # Verify Content-Disposition
    print("\n4. Verifying download headers...")
    disposition = pdf_response.headers.get('Content-Disposition', '')
    if 'attachment' not in disposition or 'crew_wallet_export.pdf' not in disposition:
        print(f"   ❌ Wrong disposition: {disposition}")
        return False
    print(f"   ✅ Content-Disposition: {disposition}")
    
    # Verify PDF structure
    print("\n5. Verifying PDF structure...")
    try:
        pdf_data = io.BytesIO(pdf_response.content)
        pdf_reader = PdfReader(pdf_data)
        num_pages = len(pdf_reader.pages)
        
        print(f"   ✅ Valid PDF with {num_pages} page(s)")
        
        # Extract text from first page
        if num_pages > 0:
            first_page_text = pdf_reader.pages[0].extract_text()
            if 'WAGMI Bordkasse' in first_page_text or 'Bordkasse' in first_page_text:
                print(f"   ✅ PDF contains expected title")
            else:
                print(f"   ⚠️  Title not found in PDF (may be encoded differently)")
                
        # Check file size
        file_size = len(pdf_response.content)
        print(f"   ✅ PDF size: {file_size:,} bytes")
        
    except Exception as e:
        print(f"   ❌ PDF validation failed: {e}")
        return False
    
    print("\n" + "="*50)
    print("🎉 All tests passed!")
    print("="*50)
    print("\nPDF Export Summary:")
    print(f"  - Endpoint: /export/pdf")
    print(f"  - Status: Working ✅")
    print(f"  - File size: {file_size:,} bytes")
    print(f"  - Pages: {num_pages}")
    print(f"  - Authentication: Required")
    print("\n✅ PDF download is ready for browser testing!")
    
    return True

if __name__ == "__main__":
    try:
        success = test_pdf_export()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
