import os
import re
import json
import math
import tempfile
from flask import Flask, request, render_template, jsonify
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import requests
import PyPDF2
import uuid

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "qwen/qwen3-235b-a22b:free"

VISA_SYSTEM_PROMPT = """
You are VisaAssist, an AI specialist in US visa applications, particularly J1 and DS-160 forms.
Your purpose is to analyze visa application information and provide honest feedback on:
1. Application completeness and consistency
2. Potential red flags or concerns in the application
3. Calculating approximate rejection probability
4. Providing specific recommendations to improve chances of approval

Important guidelines:
- Be factual and precise in your analysis
- Identify inconsistencies or missing critical information
- Focus particularly on financial documentation, ties to home country, and purpose of visit
- Provide a numerical rejection risk assessment from 0-100%
- Your analysis should reference actual US visa policies and common grounds for rejection
- Clearly explain your reasoning for each point of feedback
- Be professional but honest about application weaknesses
- Format using HTML tags (<strong>, <em>, <h3>, <ul>, <li>) instead of markdown

For J1 visas specifically, pay special attention to:
- Program eligibility requirements
- DS-2019 form details and sponsorship information
- Cultural exchange objectives and relevant background
- Evidence of intent to return to home country
- Financial support documentation
"""

def extract_text_from_pdf(file_path):
    text = ""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page_num in range(len(pdf_reader.pages)):
                text += pdf_reader.pages[page_num].extract_text()
    except Exception as e:
        text = f"Error extracting text from PDF: {str(e)}"
    return text

def calculate_rejection_probability(application_data):
    # Detect base rate based on citizenship
    citizenship = application_data.get("citizenship", "").lower()
    if citizenship == "uzbekistan":
        base_probability = 64.41
    else:
        base_probability = 20.0  # Default base rate for others

    # Factors affecting probability
    factors = {
        "insufficient_funds": {
            "weight": 15.0,
            "present": False,
            "description": "Insufficient financial documentation or funds"
        },
        "sponsor_issues": {
            "weight": 10.0,
            "present": False,
            "description": "Issues with sponsor documentation or eligibility"
        },
        "weak_home_ties": {
            "weight": 20.0,
            "present": False,
            "description": "Weak ties to home country (job, property, family)"
        },
        "unclear_purpose": {
            "weight": 12.0,
            "present": False,
            "description": "Unclear or inconsistent purpose of visit"
        },
        "missing_documents": {
            "weight": 8.0,
            "present": False,
            "description": "Missing or incomplete required documents"
        },
        "poor_travel_history": {
            "weight": 5.0,
            "present": False,
            "description": "Problematic travel history or visa violations"
        },
        "interview_preparation": {
            "weight": 7.0,
            "present": False,
            "description": "Poor interview preparation"
        },
        "high_refusal_country": {
            "weight": 10.0,
            "present": False,
            "description": "Applicant from country with high visa refusal rate"
        }
    }

    # Financial check
    if application_data.get("financial_support") in ["minimal", "none", "unclear"]:
        factors["insufficient_funds"]["present"] = True

    # Home country ties
    home_ties_score = 0
    if application_data.get("has_job_in_home_country"):
        home_ties_score += 1
    if application_data.get("owns_property_in_home_country"):
        home_ties_score += 1
    if application_data.get("has_family_in_home_country"):
        home_ties_score += 1
    if home_ties_score < 2:
        factors["weak_home_ties"]["present"] = True

    # Purpose clarity
    if not application_data.get("clear_purpose_statement"):
        factors["unclear_purpose"]["present"] = True

    if application_data.get("missing_documents"):
        factors["missing_documents"]["present"] = True

    if application_data.get("previous_visa_rejections") or application_data.get("visa_violations"):
        factors["poor_travel_history"]["present"] = True

    if application_data.get("interview_practice") in ["minimal", "none"]:
        factors["interview_preparation"]["present"] = True

    high_refusal_countries = [
        "afghanistan", "bangladesh", "belarus", "cuba", "eritrea", "iran", "iraq", 
        "libya", "nigeria", "north korea", "pakistan", "somalia", "sudan", "syria", "yemen"
    ]
    if citizenship in high_refusal_countries:
        factors["high_refusal_country"]["present"] = True

    final_probability = base_probability
    present_factors = []

    for factor_key, factor_data in factors.items():
        if factor_data["present"]:
            final_probability += factor_data["weight"]
            present_factors.append({
                "factor": factor_key,
                "description": factor_data["description"],
                "weight": factor_data["weight"]
            })

    final_probability = min(final_probability, 95.0)

    formula = "P(rejection) = BaseRate + Σ(Factor_i × Weight_i)"

    return {
        "probability": round(final_probability, 1),
        "formula": formula,
        "factors": present_factors,
        "base_rate": base_probability
    }

def call_openrouter_api(messages, temperature=0.2, max_tokens=2000):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    try:
        response = requests.post(OPENROUTER_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error calling OpenRouter API: {str(e)}"

def analyze_visa_application(application_data, pdf_texts=None):
    context = f"""
Application Analysis Request:

Applicant Information:
- Name: {application_data.get('full_name', 'Not provided')}
- Citizenship: {application_data.get('citizenship', 'Not provided')}
- Age: {application_data.get('age', 'Not provided')}
- Current Occupation: {application_data.get('occupation', 'Not provided')}

Visa Details:
- Visa Type: {application_data.get('visa_type', 'Not provided')}
- Purpose of Visit: {application_data.get('purpose', 'Not provided')}
- Intended Length of Stay: {application_data.get('length_of_stay', 'Not provided')}
- Previous US Visits: {application_data.get('previous_visits', 'No')}
- Previous Visa Denials: {application_data.get('previous_denials', 'No')}

Financial Information:
- Monthly Income: {application_data.get('monthly_income', 'Not provided')}
- Savings Available: {application_data.get('savings', 'Not provided')}
- Financial Support Documentation: {application_data.get('financial_documentation', 'Not provided')}

Ties to Home Country:
- Job in Home Country: {application_data.get('job_home_country', 'Not provided')}
- Property Ownership: {application_data.get('property_ownership', 'Not provided')}
- Family Ties: {application_data.get('family_ties', 'Not provided')}

J1 Specific (if applicable):
- Program Category: {application_data.get('program_category', 'Not provided')}
- Sponsoring Organization: {application_data.get('sponsor', 'Not provided')}
- DS-2019 Issued: {application_data.get('ds2019_issued', 'Not provided')}
"""

    if pdf_texts:
        context += "\n\nExtracted Information from Uploaded Documents:\n"
        for doc_name, doc_text in pdf_texts.items():
            preview = doc_text[:3000] + "..." if len(doc_text) > 3000 else doc_text
            context += f"\n--- {doc_name} ---\n{preview}\n"

    probability_data = calculate_rejection_probability(application_data)

    prompt = f"""
{context}

Please analyze this visa application thoroughly and provide the following:

1. OVERALL ASSESSMENT: A concise summary evaluating the application's strengths and weaknesses.

2. KEY CONCERNS: Identify potential red flags or issues that might lead to visa denial.

3. STRENGTHS: Highlight positive aspects of the application that support approval.

4. REJECTION RISK FACTORS: Our internal algorithm estimates a {probability_data['probability']}% chance of rejection based on the following identified risk factors:
{json.dumps([f["description"] for f in probability_data['factors']], indent=2) if probability_data['factors'] else "No significant risk factors identified."}

5. RECOMMENDATIONS: Provide 3-5 concrete suggestions to improve the application.

Please format your response with clear headings and be both honest and constructive in your feedback. Important: Use simple HTML formatting instead of markdown. Use <strong> for bold, <em> for italics, <h3> for section headings, <ul> and <li> for lists.
"""

    messages = [
        {"role": "system", "content": VISA_SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]

    analysis = call_openrouter_api(messages, temperature=0.2, max_tokens=2000)

    return {
        "analysis": analysis,
        "rejection_probability": probability_data
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    form_data = request.form.to_dict()
    pdf_texts = {}
    if 'documents' in request.files:
        files = request.files.getlist('documents')
        for file in files:
            if file.filename != '':
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{uuid.uuid4()}_{filename}")
                file.save(file_path)

                if filename.lower().endswith('.pdf'):
                    extracted_text = extract_text_from_pdf(file_path)
                    pdf_texts[filename] = extracted_text

                try:
                    os.remove(file_path)
                except:
                    pass

    result = analyze_visa_application(form_data, pdf_texts)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
