
AI-powered analyzer for U.S. visa applications (J1, DS-160). Upload documents, assess risks, get recommendations. Built with Flask + OpenRouter (Qwen-23B).

# VisaAssist — US Visa Risk & Feedback Analyzer 🇺🇸🛂

VisaAssist is a Flask-based web app designed to **analyze US visa applications** (especially **J1**, **DS-160**) and provide:
- Rejection probability estimates
- Honest assessment of strengths and weaknesses
- Actionable advice to improve the application

It uses:
- **OpenRouter AI** (Qwen 3 235B model) for deep natural language analysis
- **Custom rules engine** for base risk scoring (incl. logic for countries like Uzbekistan)
- **PDF parsing** for extracting content from uploaded visa documents

---

## 🔧 Features

- Upload and process visa-related PDFs (financial docs, DS-160, etc.)
- Smart extraction and formatting of applicant data
- Chat-style prompt to a large language model for analysis
- HTML-formatted AI feedback (clear, structured, and exportable)
- Dynamic rejection probability calculator based on real-world logic

---

## 🚀 Getting Started

### 1. Clone this repo

```bash
git clone https://github.com/fromgodd/US-Visa-Agent.git
cd US-Visa-Agent
```

### 2. Set up your environment

Create a `.env` file with:

```
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

> Get your free API key at https://openrouter.ai/

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the app

```bash
python app.py
```

Visit [http://localhost:5000](http://localhost:5000) to access the web interface.

---

## 📈 Visa Rejection Logic

The app uses a country-based baseline risk (e.g., **Uzbekistan ~ 64.41%**) and applies weighted risk factors like:

- Weak ties to home country
- Poor financials
- Lack of interview prep
- Incomplete documents
- Previous visa issues

Each factor increases the final probability (capped at 95%).

---

## 🧠 AI Model

We use the free `qwen/qwen3-235b-a22b:free` model from OpenRouter API for feedback generation.

---

## 🗂 Tech Stack

- Python + Flask
- HTML (Jinja2 templating)
- OpenRouter AI (Qwen 3 model)
- PyPDF2 for PDF parsing
- RESTful JSON API communication

---

## 📜 License

MIT License. Do whatever you want, just don’t blame us if you get rejected at the embassy 💀

---

## 🙋‍♂️ Author

Made with love and skepticism by a math-loving Rust-enjoyer named Valera 🇺🇿🛠️

```diff
+ Pull requests are welcome
+ TODO - Fine tune for better results!
- Dumb visa denials are not
```
## Screenshots

![{66832B7A-7974-4074-9028-6DBAA896F38D}](https://github.com/user-attachments/assets/dd97aec2-1da9-4f10-a944-7ebada1abaa2)

![{B552203C-D188-4A83-B706-BA5BFC40F3A5}](https://github.com/user-attachments/assets/6ad86c48-cadb-4db1-8b56-cc2bea7524f5)

