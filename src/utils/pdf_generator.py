import os
from fpdf import FPDF
from datetime import datetime

class FinancialReportPDF(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 12)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, "FinFlow AI - Financial Analysis Report", align="R", ln=True)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def chapter_title(self, label):
        # Check if there is enough space for the title and at least some body text
        if self.get_y() > 250:
            self.add_page()
        self.set_font("helvetica", "B", 16)
        self.set_text_color(0, 51, 102)  # Dark blue
        self.cell(0, 15, label, ln=True, align="L")
        self.ln(5)

    def chapter_body(self, body):
        self.set_font("helvetica", "", 11)
        self.set_text_color(0, 0, 0)
        # Use latin-1 to be more inclusive than ascii but still safe
        clean_body = body.encode('latin-1', 'replace').decode('latin-1')
        self.multi_cell(0, 7, clean_body)
        self.ln()

    def references_section(self, text):
        if self.get_y() > 250:
            self.add_page()
        self.set_font("helvetica", "B", 14)
        self.set_text_color(0, 51, 102)
        self.cell(0, 15, "References", ln=True, align="L")
        self.set_font("helvetica", "I", 10)
        self.set_text_color(50, 50, 50)
        clean_text = text.encode('latin-1', 'replace').decode('latin-1')
        self.multi_cell(0, 6, clean_text)
        self.ln()


def generate_pdf_from_markdown(markdown_text: str, ticker: str, output_dir: str = "reports"):
    """
    Converts markdown text to a professional PDF.
    Simple implementation: parses headers and body.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    pdf = FinancialReportPDF()
    pdf.add_page()

    # Title Page
    pdf.set_font("helvetica", "B", 28)
    pdf.set_text_color(0, 51, 102)
    pdf.ln(40)
    pdf.cell(0, 20, "Financial Analysis Report", ln=True, align="C")
    pdf.set_font("helvetica", "", 20)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 20, f"Ticker: {ticker}", ln=True, align="C")
    pdf.ln(20)
    pdf.set_font("helvetica", "I", 12)
    pdf.cell(0, 10, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align="C")
    pdf.ln(30)

    # Parse Markdown
    lines = markdown_text.split('\n')
    current_section_title = ""
    current_section_body = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith("## "):
            # If we were already building a section, save it
            if current_section_title:
                if current_section_title.lower() == "references":
                    pdf.references_section("\n".join(current_section_body))
                else:
                    pdf.chapter_title(current_section_title)
                    pdf.chapter_body("\n".join(current_section_body))
            
            current_section_title = line.replace("## ", "")
            current_section_body = []
        elif line.startswith("# "):
            # Main title (already handled on title page, but let's be safe)
            current_section_title = line.replace("# ", "")
            current_section_body = []
        else:
            # It's body text
            # Preserve the line structure for lists
            clean_line = line.replace("**", "")
            current_section_body.append(clean_line)

    # Add the last section
    if current_section_title:
        if current_section_title.lower() == "references":
            pdf.references_section("\n".join(current_section_body))
        else:
            pdf.chapter_title(current_section_title)
            pdf.chapter_body("\n".join(current_section_body))
    elif current_section_body:
        pdf.chapter_body("\n".join(current_section_body))

    filename = f"report_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join(output_dir, filename)
    pdf.output(filepath)
    return filepath
