#!/usr/bin/env python3
"""
Simple Markdown to PDF Converter
Converts markdown files to HTML first, then to PDF using system print function
"""

import sys
import os
import markdown
import subprocess
from pathlib import Path

def markdown_to_html(md_file):
    """Convert markdown to styled HTML"""

    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # Convert markdown to HTML
    html_content = markdown.markdown(md_content, extensions=['tables', 'fenced_code', 'codehilite'])

    # Add CSS styling for print
    styled_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Interview Guide</title>
    <style>
        @page {{
            size: A4 landscape;
            margin: 0.5cm;
        }}

        body {{
            font-family: 'Courier New', 'Consolas', monospace;
            font-size: 9pt;
            line-height: 1.4;
            color: #333;
            max-width: none;
            margin: 0;
            padding: 20px;
        }}

        h1 {{
            color: #2c3e50;
            font-size: 16pt;
            font-weight: bold;
            margin-top: 30px;
            margin-bottom: 15px;
            page-break-before: always;
            border-bottom: 2px solid #3498db;
            padding-bottom: 5px;
        }}

        h2 {{
            color: #34495e;
            font-size: 13pt;
            font-weight: bold;
            margin-top: 20px;
            margin-bottom: 10px;
        }}

        h3 {{
            color: #555;
            font-size: 11pt;
            font-weight: bold;
            margin-top: 15px;
            margin-bottom: 8px;
        }}

        pre {{
            background-color: #f5f5f5;
            border: 1px solid #ddd;
            border-radius: 3px;
            padding: 10px;
            overflow-x: auto;
            font-size: 8pt;
            line-height: 1.3;
            page-break-inside: avoid;
        }}

        code {{
            font-family: 'Courier New', 'Consolas', monospace;
            background-color: #f0f0f0;
            padding: 2px 5px;
            border-radius: 3px;
            font-size: 8pt;
        }}

        pre code {{
            background-color: transparent;
            padding: 0;
        }}

        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
            font-size: 8pt;
            page-break-inside: avoid;
        }}

        table td, table th {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}

        table th {{
            background-color: #3498db;
            color: white;
            font-weight: bold;
        }}

        table tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}

        ul, ol {{
            margin: 10px 0;
            padding-left: 25px;
        }}

        li {{
            margin: 5px 0;
        }}

        blockquote {{
            border-left: 4px solid #3498db;
            padding-left: 15px;
            margin: 15px 0;
            color: #555;
            font-style: italic;
        }}

        strong {{
            font-weight: bold;
            color: #2c3e50;
        }}

        .section-divider {{
            border-top: 3px solid #3498db;
            margin: 30px 0;
        }}

        @media print {{
            body {{
                print-color-adjust: exact;
                -webkit-print-color-adjust: exact;
            }}

            h1 {{
                page-break-after: avoid;
            }}

            pre, table, blockquote {{
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
{html_content}
</body>
</html>
"""

    return styled_html

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 md_to_pdf.py <markdown_file>")
        print("Example: python3 md_to_pdf.py YouTube_Complete_Interview_Guide.md")
        sys.exit(1)

    md_file = sys.argv[1]

    if not os.path.exists(md_file):
        print(f"❌ Error: File not found: {md_file}")
        sys.exit(1)

    print(f"📄 Converting: {md_file}")

    # Generate HTML
    html_content = markdown_to_html(md_file)

    # Save HTML file
    html_file = md_file.replace('.md', '_print.html')
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"✅ HTML created: {html_file}")
    print(f"\n📖 To create PDF:")
    print(f"1. Open {html_file} in Chrome/Safari")
    print(f"2. Press Cmd+P (Print)")
    print(f"3. Select 'Save as PDF'")
    print(f"4. Choose 'Landscape' orientation")
    print(f"5. Save to: {md_file.replace('.md', '.pdf')}")

    # Open HTML in browser
    subprocess.run(['open', html_file])

if __name__ == '__main__':
    main()
