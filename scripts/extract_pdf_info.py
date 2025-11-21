#!/usr/bin/env python3
"""
PDF Information Extractor for RCA Analysis

This script helps extract key information from the As-Built Report PDF
for use in Root Cause Analysis documentation.

Usage:
    python3 extract_pdf_info.py <pdf_path>
"""

import sys
import re
from pathlib import Path


def extract_text_simple(pdf_path):
    """
    Attempt to extract text from PDF using available libraries.
    """
    text_content = []

    # Try pdfplumber first
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            print(f"Total pages: {len(pdf.pages)}")
            for i, page in enumerate(pdf.pages[:10]):  # First 10 pages
                text = page.extract_text()
                if text:
                    text_content.append(f"\n=== Page {i+1} ===\n{text}")
        return "\n".join(text_content)
    except ImportError:
        pass

    # Try PyMuPDF (fitz)
    try:
        import fitz
        doc = fitz.open(pdf_path)
        print(f"Total pages: {len(doc)}")
        for i in range(min(10, len(doc))):  # First 10 pages
            page = doc[i]
            text = page.get_text()
            if text:
                text_content.append(f"\n=== Page {i+1} ===\n{text}")
        doc.close()
        return "\n".join(text_content)
    except ImportError:
        pass

    # Try PyPDF2
    try:
        import PyPDF2
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            print(f"Total pages: {len(reader.pages)}")
            for i, page in enumerate(reader.pages[:10]):  # First 10 pages
                text = page.extract_text()
                if text:
                    text_content.append(f"\n=== Page {i+1} ===\n{text}")
        return "\n".join(text_content)
    except ImportError:
        pass

    return None


def extract_key_info(text):
    """
    Extract key information from PDF text for RCA analysis.
    """
    info = {
        'cluster_name': None,
        'report_date': None,
        'dboxes': [],
        'dnodes': [],
        'firmware_versions': [],
        'hardware_models': [],
    }

    if not text:
        return info

    # Extract cluster name
    cluster_match = re.search(r'Cluster[:\s]+([A-Z0-9\-]+)', text, re.IGNORECASE)
    if cluster_match:
        info['cluster_name'] = cluster_match.group(1)

    # Extract date
    date_match = re.search(r'(\d{4}[-/]\d{2}[-/]\d{2})', text)
    if date_match:
        info['report_date'] = date_match.group(1)

    # Extract DBox information
    dbox_pattern = r'DBox[:\s]+([A-Z0-9\-]+)|dbox[:\s]+([A-Z0-9\-]+)'
    dbox_matches = re.findall(dbox_pattern, text, re.IGNORECASE)
    for match in dbox_matches:
        dbox_id = match[0] or match[1]
        if dbox_id and dbox_id not in info['dboxes']:
            info['dboxes'].append(dbox_id)

    # Extract DNode information
    dnode_pattern = r'DNode[:\s]+([A-Z0-9\-]+)|dnode[:\s]+([A-Z0-9\-]+)'
    dnode_matches = re.findall(dnode_pattern, text, re.IGNORECASE)
    for match in dnode_matches:
        dnode_id = match[0] or match[1]
        if dnode_id and dnode_id not in info['dnodes']:
            info['dnodes'].append(dnode_id)

    # Extract firmware versions
    fw_pattern = r'[Ff]irmware[:\s]+([0-9.]+)|Version[:\s]+([0-9.]+)'
    fw_matches = re.findall(fw_pattern, text)
    for match in fw_matches:
        version = match[0] or match[1]
        if version and version not in info['firmware_versions']:
            info['firmware_versions'].append(version)

    return info


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 extract_pdf_info.py <pdf_path>")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)

    print(f"Extracting information from: {pdf_path}")
    print("=" * 60)

    # Extract text
    text = extract_text_simple(pdf_path)

    if text:
        print("\nExtracted Text (first 2000 characters):")
        print("-" * 60)
        print(text[:2000])
        print("\n" + "=" * 60)

        # Extract key information
        info = extract_key_info(text)

        print("\nKey Information Extracted:")
        print("-" * 60)
        print(f"Cluster Name: {info['cluster_name']}")
        print(f"Report Date: {info['report_date']}")
        print(f"DBoxes Found: {len(info['dboxes'])}")
        if info['dboxes']:
            print(f"  {', '.join(info['dboxes'][:10])}")
        print(f"DNodes Found: {len(info['dnodes'])}")
        if info['dnodes']:
            print(f"  {', '.join(info['dnodes'][:10])}")
        print(f"Firmware Versions: {', '.join(info['firmware_versions'])}")

        # Save full text to file
        output_file = pdf_path.parent / f"{pdf_path.stem}_extracted_text.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"\nFull extracted text saved to: {output_file}")
    else:
        print("\nError: Could not extract text from PDF.")
        print("Please install one of the following PDF libraries:")
        print("  - pdfplumber: pip install pdfplumber")
        print("  - PyMuPDF: pip install pymupdf")
        print("  - PyPDF2: pip install PyPDF2")


if __name__ == "__main__":
    main()
