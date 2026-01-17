# 🏥 OpenClinical AI: Local C-CDA Analyst

**A private, offline-first tool for analyzing clinical patient records (C-CDA XML) using Local LLMs.**

![License](https://img.shields.io/badge/license-MIT-green) ![Python](https://img.shields.io/badge/python-3.11-blue) ![Ollama](https://img.shields.io/badge/AI-Ollama-orange)

## 📖 What is this?
OpenClinical AI is a workstation tool designed to solve the "Needle in a Haystack" problem for medical records. It takes standard **C-CDA XML** files (commonly exported from EHRs like Epic or Cerner), parses them into human-readable text, and uses a local Large Language Model (Mistral-Nemo) to answer questions about the patient's history.

**Key Architecture:**
* **Privacy First:** 100% offline. No data is sent to OpenAI, Google, or the cloud.
* **Zero Hallucination Retrieval:** Uses **SQLite** for deterministic patient lookup (no vector database guessing).
* **Noise Filtering:** Includes a custom XML parser that strips 90% of HL7 syntax noise, ensuring the AI sees the actual clinical data (meds, allergies, encounters) without getting confused.

---

## 🛠️ Prerequisites
You need two things installed on your computer:

1.  **Python 3.10+**: [Download Here](https://www.python.org/downloads/)
2.  **Ollama** (The AI Engine): [Download Here](https://ollama.com/)

After installing Ollama, open your terminal and download the medical model:
```bash
ollama pull mistral-nemo

---

# 🏥 OpenClinical AI

A private, local tool for analyzing C-CDA patient records using SQLite and Mistral-Nemo.

## 🚀 How to Run
1. **Install Requirements:**
   `pip install -r requirements.txt`
2. **Add Data:**
   Create a folder named `data` and put your XML files there.
3. **Build Database:**
   `python build_db.py`
4. **Run App:**
   `python -m streamlit run app.py`

## 🔒 Privacy
This tool runs 100% offline. No patient data leaves your machine.