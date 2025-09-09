# 📘 OpenAI Notes & Quiz Generator  

An interactive **Streamlit application** powered by **OpenAI GPT-4o** and **DALL·E 3** that generates:  

📝 In-depth study notes (Markdown & PDF)  
🖼️ Educational images and diagrams  
📚 Enhanced references (papers, videos, tutorials, books)  
🎯 Quizzes with solutions in multiple difficulty levels  
📥 Downloadable PDFs for notes, quizzes, and answer keys  

A perfect tool for **learners, educators, and content creators** who want structured study material on any topic.  

---

## 🚀 Demo  
👉 [**Try the Live App Here**](https://openai-buildathon.streamlit.app/)  

---

## ✨ Features  

- 🔍 **Expand Outline** – Generate a structured syllabus for any topic  
- 📚 **In-depth Notes** – Comprehensive Markdown notes (exportable as PDF)  
- 🖼️ **AI-Generated Images** – DALL·E illustrations tailored to the topic  
- 📚 **Enhanced References** – Curated links to papers, videos, tutorials, and books  
- 📝 **Quizzes & Answer Keys** – 10 MCQs (Easy/Medium/Hard) with downloadable PDFs  
- 📥 **One-Click Downloads** – Export study notes, quizzes, and answer keys  
- ⚡ **Robust Error Handling** – Retries and fallbacks for API/JSON parsing issues  

---

## 📂 Examples  

**Example: Machine Learning**  
- Outline covers basics → models → applications  
- Notes include prerequisites, objectives, and advanced topics  
- Images: process diagrams & concept illustrations  
- Quiz: 10 questions with difficulty levels  

**Example: Python Programming**  
- Produces beginner-to-advanced notes  
- Includes code snippets, references, and exercises  

---

## ❗ Troubleshooting  

- **API Key not found** → Check Streamlit secrets  
- **Unicode errors in PDFs** → Handled with `unidecode` (transliteration)  
- **Quiz JSON parse error** → App retries or falls back to deterministic quiz  
- **Image generation fails** → Retry via *Regenerate Images* button  

---

## 👥 Contributors  

- [**Ojas Wankhede**](https://github.com/ojas7556)  
- [**Gurpratap Singh Sandhu**](https://github.com/GurpratapSingh06)  
