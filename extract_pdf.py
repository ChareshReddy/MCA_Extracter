from pypdf import PdfReader
reader = PdfReader('App Setup & User Manual_2.0.pdf')
text = '\n'.join([page.extract_text() for page in reader.pages])
with open('pdf_output.txt', 'w', encoding='utf-8') as f:
    f.write(text)
