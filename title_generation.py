import os
import openai
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from docx import Document
import PyPDF2
from dotenv import load_dotenv
import json
import re

load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

app = FastAPI()

def extract_text_from_pdf(file) -> str:
    reader = PyPDF2.PdfReader(file)
    return "\n".join(page.extract_text() for page in reader.pages if page.extract_text())

def extract_text_from_docx(file) -> str:
    doc = Document(file)
    return "\n".join([para.text for para in doc.paragraphs])

def extract_text(file: UploadFile) -> str:
    ext = file.filename.lower().split('.')[-1]
    if ext == "pdf":
        return extract_text_from_pdf(file.file)
    elif ext == "docx":
        return extract_text_from_docx(file.file)
    elif ext == "txt":
        return file.file.read().decode('utf-8')
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format")

def get_title_from_doc(doc_text: str) -> dict:
    prompt = f"""
    You are a precise data extraction assistant. Your task is to extract a person's full name and date of birth from the provided document text.

    EXTRACTION RULES:
    1. Look for full names (first name + last name at minimum)
    2. Look for dates that represent birth dates (could be labeled as DOB, Date of Birth, Born, Birth Date, etc.)
    3. Be flexible with date formats but standardize the output
    4. Only extract information that is clearly identifiable

    EXAMPLES OF VALID EXTRACTIONS:
    - Name: "John Michael Smith" → "John Michael Smith"
    - Name: "JANE DOE" → "Jane Doe" (proper case)

    - DOB: "01/15/1985" → "01/15/1985"
    - DOB: "January 15, 1985" → "01/15/1985"
    - DOB: "15-Jan-1985" → "01/15/1985"
    - DOB: "1985-01-15" → "01/15/1985"

    EXAMPLES OF WHAT TO IGNORE:
    - Company names, organization names
    - Addresses, phone numbers
    - Random dates that aren't birth dates
    - Partial names or single words

    OUTPUT FORMAT:
    You must respond with ONLY a valid JSON object in this exact format:
    {{
        "name": "First Last",
        "dob": "MM/DD/YYYY"
    }}

    If name is not found: {{"name": null, "dob": "MM/DD/YYYY"}}
    If dob is not found: {{"name": "First Last", "dob": null}}
    If neither found: {{"name": null, "dob": null}}

    DOCUMENT TEXT:
    \"\"\"{doc_text[:2000]}\"\"\"

    JSON Response:"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,  
            max_tokens=150,   
        )

        content = response['choices'][0]['message']['content'].strip()
        
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            result = json.loads(json_str)
            
            if not isinstance(result, dict) or not all(key in result for key in ['name', 'dob']):
                return {"name": None, "dob": None}
            
            # name = clean_name(result.get('name'))
            # dob = clean_dob(result.get('dob'))
            name = result.get('name')
            dob = result.get('dob')
            return {"name": name, "dob": dob}
        else:
            return {"name": None, "dob": None}
            
    except (json.JSONDecodeError, KeyError, Exception) as e:
        print(f"Error processing OpenAI response: {e}")
        return {"name": None, "dob": None}

# def clean_name(name):
#     """Clean and validate extracted name"""
#     if not name or not isinstance(name, str):
#         return None
    
#     # Remove extra whitespace and convert to proper case
#     name = ' '.join(name.strip().split())
    
#     # Basic validation - should have at least first and last name
#     if len(name.split()) < 2:
#         return None
    
#     # Remove common titles
#     titles = ['dr.', 'mr.', 'mrs.', 'ms.', 'prof.', 'dr', 'mr', 'mrs', 'ms', 'prof']
#     words = name.lower().split()
#     cleaned_words = [word for word in name.split() if word.lower().rstrip('.') not in titles]
    
#     if len(cleaned_words) >= 2:
#         return ' '.join(cleaned_words).title()
    
#     return None

# def clean_dob(dob):
#     """Clean and validate extracted date of birth"""
#     if not dob or not isinstance(dob, str):
#         return None
    
#     # Remove extra whitespace
#     dob = dob.strip()
    
#     # Try to match MM/DD/YYYY format
#     if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', dob):
#         return dob
    
#     # Try to parse other common formats and convert to MM/DD/YYYY
#     date_patterns = [
#         (r'(\d{1,2})-(\d{1,2})-(\d{4})', r'\1/\2/\3'),  # MM-DD-YYYY
#         (r'(\d{4})-(\d{1,2})-(\d{1,2})', r'\2/\3/\1'),  # YYYY-MM-DD
#         (r'(\d{1,2})\.(\d{1,2})\.(\d{4})', r'\1/\2/\3'), # MM.DD.YYYY
#     ]
    
#     for pattern, replacement in date_patterns:
#         match = re.match(pattern, dob)
#         if match:
#             return re.sub(pattern, replacement, dob)
    
#     return None

@app.post("/extract")
async def extract_info(file: UploadFile = File(...)):
    """
    Extract name and date of birth from uploaded document.
    Supported formats: PDF, DOCX, TXT
    Returns: JSON with extracted name and dob
    """
    try:
        text = extract_text(file)
        
        if not text.strip():
            raise HTTPException(status_code=400, detail="No text could be extracted from the file")
        
        result = get_title_from_doc(text)
        
        return JSONResponse(content={
            "success": True,
            "extracted_info": result,
            "filename": file.filename
        })
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Extraction error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

