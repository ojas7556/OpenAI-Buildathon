📘 OpenAI Notes & Quiz Generator

An interactive Streamlit application powered by OpenAI GPT-4o and DALL·E 3 that generates:

📝 In-depth study notes in Markdown & PDF

🖼️ Educational images and diagrams

📚 Enhanced references (papers, videos, web resources, books)

🎯 Quizzes with solutions in multiple difficulty levels

📥 Downloadable PDFs for notes, quizzes, and answer keys


A perfect tool for learners, educators, and content creators who want structured study material on any topic.


---

📑 Table of Contents

Features

Demo

Installation

Configuration

Usage

Dependencies

Examples

Troubleshooting

Contributors

License



---

✨ Features

🔍 Expand Outline – Generate a structured syllabus for any topic.

📚 In-depth Notes – Comprehensive Markdown notes (exportable as PDF).

🖼️ AI-Generated Images – DALL·E illustrations tailored to the topic.

📚 Enhanced References – Curated links to academic papers, YouTube videos, tutorials, and books.

📝 Quizzes & Answer Keys – 10 MCQs (Easy/Medium/Hard) with downloadable PDFs.

📥 One-Click Downloads – Export study notes, quizzes, and answer keys.

⚡ Robust Error Handling – Retries and fallbacks for API/JSON parsing issues.



---

🚀 Demo
Try the live app here: [OpenAI Notes & Quiz Generator]
(https://openai-buildathon.streamlit.app/)


---

🛠️ Installation

Clone the repository:

git clone https://github.com/your-username/OpenAI-Buildathon.git
cd OpenAI-Buildathon

Create a virtual environment (recommended):

python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

Install dependencies:

pip install -r requirements.txt

Run the app:

streamlit run app.py


---

⚙️ Configuration

The app requires an OpenAI API key.

🔑 Local Development

Create a .env file in the project root:

OPENAI_API_KEY=sk-your-key-here
MODEL_NAME=gpt-4o

Or export variables directly:

export OPENAI_API_KEY="sk-your-key-here"
export MODEL_NAME="gpt-4o"

☁️ Streamlit Cloud

Add your secrets under
Manage app → Settings → Secrets:

OPENAI_API_KEY = "sk-your-key-here"
MODEL_NAME = "gpt-4o"


---

📦 Dependencies

From requirements.txt:

streamlit>=1.24.0
openai>=1.0.0
python-dotenv>=1.0.0
fpdf<=1.7.2
requests>=2.28.0
unidecode>=1.3.6


---

📖 Usage

1. Launch with streamlit run app.py.


2. Enter your topic in the input field.


3. Click Expand Outline to preview the structure.


4. Confirm to generate:

📚 Notes (Markdown & PDF)

🖼️ Images (DALL·E 3)

📚 References & resources

📝 Quiz & answer key



5. Download results as PDF.




---

📂 Examples

Example: Machine Learning

Outline covers basics → models → applications.

Notes include prerequisites, objectives, advanced topics.

Images: process diagrams & concept illustrations.

Quiz: 10 questions with difficulty levels.


Example: Python Programming

Produces beginner-to-advanced notes.

Includes code snippets, references, exercises.



---

❗ Troubleshooting

API Key not found → Check .env file or Streamlit secrets.

Unicode errors in PDFs → Handled with unidecode (transliteration).

Quiz JSON parse error → App retries or falls back to deterministic quiz.

Image generation fails → Retry via “Regenerate Images” button.



---

👥 Contributors
-Ojas Wankhede
([ojas7556] [ https://github.com/ojas7556] )
-Gurpratap Singh Sandhu
([GurpratapSingh06] [https://github.com/GurpratapSingh06]



---

📜 License

This project is licensed under the MIT License.


---
