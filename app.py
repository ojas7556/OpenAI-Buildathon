# app.py
import os
import json
import re
from io import BytesIO
from typing import List, Dict
from dotenv import load_dotenv
import streamlit as st
from fpdf import FPDF
from openai import OpenAI
from unidecode import unidecode   # transliterate unicode -> ascii (avoids latin-1 issues)

# -----------------------
# Config
# -----------------------
# -------- robust startup & secrets handling (replace existing top-of-file logic) ----------
import os
import traceback

# Optional: show full tracebacks in the app only while debugging.
# Remove or set DEBUG=False in production.
DEBUG = True

try:
    # Try imports that may fail on Cloud
    from dotenv import load_dotenv
    from openai import OpenAI
    # If you rely on load_dotenv locally, call it
    if os.getenv("STREAMLIT_RUNTIME") is None:  # naive check; adjust if you prefer
        load_dotenv()
except Exception:
    if DEBUG:
        st.error("Startup import error — see details below.")
        st.text(traceback.format_exc())
    raise

# Load key: prefer Streamlit secrets (Cloud) but fall back to environment variables (local)
OPENAI_API_KEY = None
try:
    OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY")  # safe .get() avoids KeyError
except Exception:
    # if st.secrets isn't available for any reason, ignore and fall back
    OPENAI_API_KEY = None

if not OPENAI_API_KEY:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o")

if not OPENAI_API_KEY:
    st.error(
        "OpenAI API key not found.\n\n"
        "• For Streamlit Cloud: Manage app → Settings → Secrets → add:\n"
        "    OPENAI_API_KEY = \"sk-...\"\n"
        "• For local dev: create .streamlit/secrets.toml or set env var OPENAI_API_KEY\n\n"
        "After adding the secret, redeploy or restart the app."
    )
    st.stop()

# create client
client = OpenAI(api_key=OPENAI_API_KEY)
# ---------------------------------------------------------------------------------------

# -----------------------
# DALL-E Image Generation
# -----------------------
def generate_image_with_dalle(prompt: str, size: str = "1024x1024", quality: str = "standard") -> str:
    """Generate an image using DALL-E API. Returns image URL or error message."""
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=size,
            quality=quality,
            n=1,
        )
        return response.data[0].url
    except Exception as e:
        return f"Error generating image: {str(e)}"

def generate_multiple_images_with_dalle(topic: str, num_images: int = 3, context: str = "") -> List[str]:
    """Generate multiple images for different aspects of a topic."""
    image_urls = []
    
    # Create different prompts for different aspects
    aspects = [
        f"Overview diagram for {topic}",
        f"Detailed process flow for {topic}",
        f"Key concepts illustration for {topic}",
        f"Examples and applications of {topic}",
        f"Advanced topics in {topic}"
    ]
    
    for i in range(min(num_images, len(aspects))):
        prompt = create_image_prompt_from_topic(aspects[i], context)
        image_url = generate_image_with_dalle(prompt)
        if not image_url.startswith("Error"):
            image_urls.append(image_url)
        else:
            st.warning(f"Failed to generate image {i+1}: {image_url}")
    
    return image_urls


def extract_table_of_contents(md_text: str) -> str:
    """Extract and format table of contents from markdown text."""
    lines = md_text.split('\n')
    toc_items = []
    
    for line in lines:
        if line.startswith('#'):
            level = len(line) - len(line.lstrip('#'))
            title = line.lstrip('# ').strip()
            if title:
                indent = "  " * (level - 1)
                toc_items.append(f"{indent}- {title}")
    
    if toc_items:
        return "## 📋 Table of Contents\n\n" + "\n".join(toc_items) + "\n\n---\n\n"
    return ""

def generate_enhanced_references(topic: str) -> str:
    """Generate comprehensive references including web links, YouTube videos, and model information."""
    references_prompt = f"""
    Generate comprehensive references for the topic: {topic}
    
    Include the following categories with specific examples:
    
    1. **Academic Resources**
       - Research papers with DOI links
       - University course materials
       - Academic journals and publications
    
    2. **YouTube Educational Content**
       - Specific video recommendations with channel names
       - Educational series and playlists
       - Tutorial channels and expert content creators
    
    3. **Web Resources**
       - Official documentation and guides
       - Interactive tutorials and courses
       - Community forums and discussion platforms
    
    4. **Books and Publications**
       - Textbooks with ISBN numbers
       - E-books and online publications
       - Industry reports and white papers
    
    5. **Tools and Software**
       - Relevant software applications
       - Online tools and platforms
       - Development environments and frameworks
    
    6. **Professional Development**
       - Certification programs
       - Online courses and MOOCs
       - Professional associations and communities
    
    Format as a structured markdown list with descriptions and links where applicable.
    Focus on high-quality, authoritative sources that would be valuable for learning this topic.
    """
    
    try:
        references = call_openai(references_prompt, user_input=topic, temperature=0.3, max_output_tokens=2000)
        return references if not references.startswith("__ERROR__") else "Error generating references"
    except Exception as e:
        return f"Error generating references: {str(e)}"

def create_image_prompt_from_topic(topic: str, context: str = "") -> str:
    """Create an optimized prompt for DALL-E based on the topic and context."""
    # Clean and enhance the topic for better image generation
    clean_topic = topic.strip()
    
    # Add context if available
    if context:
        prompt = f"Educational illustration for the topic: {clean_topic}. Context: {context[:200]}. Style: clean, professional, educational diagram or illustration suitable for learning materials."
    else:
        prompt = f"Educational illustration for the topic: {clean_topic}. Style: clean, professional, educational diagram or illustration suitable for learning materials."
    
    return prompt

# -----------------------
# OpenAI wrapper (Responses API)
# -----------------------
def call_openai(instructions: str, user_input: str = "", temperature: float = 0.0, max_output_tokens: int = 1400) -> str:
    """Call Responses API. Returns text or '__ERROR__:' prefix on exception."""
    try:
        resp = client.responses.create(
            model=MODEL_NAME,
            instructions=instructions,
            input=user_input,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        # Prefer high-level output_text if present
        if hasattr(resp, "output_text") and resp.output_text:
            return resp.output_text.strip()
        # Fallback: assemble from resp.output
        parts = []
        for item in getattr(resp, "output", []) or []:
            if isinstance(item, dict):
                content = item.get("content")
                if isinstance(content, list):
                    for c in content:
                        if isinstance(c, dict) and c.get("type") == "output_text":
                            parts.append(c.get("text", ""))
                elif isinstance(content, str):
                    parts.append(content)
        return "\n".join(parts).strip()
    except Exception as exc:
        return f"__ERROR__:{exc}"

# -----------------------
# Prompts
# -----------------------
OUTLINE_PROMPT = (
    "You are an expert instructor. Given a syllabus/topic, produce a concise numbered outline "
    "(4-8 top-level bullets) of what a comprehensive course/documentation should cover. Output as a plain numbered list. Topic:"
)

NOTES_PROMPT = (
    "You are an expert educator and technical writer. Produce a comprehensive, in-depth documentation-style "
    "learning module for the given Topic in Markdown. The document must include (in this order):\n\n"
    "1) **Title + Executive Summary** (2-3 paragraphs with key insights)\n"
    "2) **Prerequisites** (detailed list with explanations)\n"
    "3) **Learning Objectives** (5-10 specific, measurable goals)\n"
    "4) **Table of Contents** (auto-generated from headings)\n"
    "5) **Core Concepts** (fundamental principles with detailed explanations)\n"
    "6) **Detailed Sections** for each subtopic including:\n"
    "   - Comprehensive explanations with real-world context\n"
    "   - Step-by-step walkthroughs with examples\n"
    "   - Code snippets, diagrams descriptions, and practical applications\n"
    "   - Best practices and industry standards\n"
    "   - Performance considerations and optimization tips\n"
    "7) **Advanced Topics** (deeper dive into complex aspects)\n"
    "8) **Common Pitfalls and Misconceptions** (with explanations and how to avoid them)\n"
    "9) **Real-World Applications** (case studies and practical examples)\n"
    "10) **Study Plan** (structured learning path over 2-4 weeks)\n"
    "11) **Exercises & Projects** (15 problems with difficulty progression: Beginner, Intermediate, Advanced)\n"
    "12) **Answers Section** (detailed solutions with explanations)\n"
    "13) **Further Reading and Resources** including:\n"
    "    - Academic papers and research articles with DOI links\n"
    "    - YouTube educational channels and specific video recommendations\n"
    "    - Web resources, tutorials, and documentation\n"
    "    - Books and e-books with ISBN references\n"
    "    - Online courses and certification programs\n"
    "    - Community forums and discussion groups\n"
    "    - Tools and software related to the topic\n"
    "14) **Glossary of Key Terms** (comprehensive definitions)\n"
    "15) **Quick Reference Guide** (cheat sheet format)\n\n"
    "Output valid Markdown using headings (#, ##, ###), lists (-), code fences (```), tables, and callout boxes. "
    "Make it extremely comprehensive and detailed. Aim for 4000-6000 words total. "
    "Write in an engaging, professional tone suitable for both self-study and reference. "
    "Include practical examples, analogies, and visual descriptions for complex concepts. Topic:"
)

QUIZ_PROMPT = (
    "You are an assessment generator. Create EXACTLY 10 multiple-choice questions for the Topic in STRICT JSON format.\n"
    "Constraints:\n"
    "- Exactly 10 questions.\n"
    "- Exactly 4 options per question.\n"
    "- Include a 'difficulty' field with values 'Easy','Medium','Hard'.\n"
    "- Use this exact JSON form (answer is zero-based index):\n"
    "[\n"
    "  {\"question\":\"...\",\"options\":[\"optA\",\"optB\",\"optC\",\"optD\"], \"answer\": 0, \"difficulty\":\"Easy\"},\n"
    "  ...  (10 items total)\n"
    "]\n"
    "Split difficulties: 4 Easy, 3 Medium, 3 Hard (any order). DO NOT output any commentary outside the JSON. Topic:"
)

# -----------------------
# Robust JSON extractor + retry
# -----------------------
def extract_json(text: str):
    """Try multiple ways to parse JSON from model output."""
    if not text:
        raise ValueError("Empty text")
    if text.startswith("__ERROR__"):
        raise ValueError(text)
    # Direct
    try:
        return json.loads(text)
    except Exception:
        pass
    # Between first [ and last ]
    s = text.find("[")
    e = text.rfind("]")
    if s != -1 and e != -1 and e > s:
        chunk = text[s:e+1]
        try:
            return json.loads(chunk)
        except Exception:
            pass
    # Try JSON inside <JSON>...</JSON> tags (if model wrapped)
    m = re.search(r"<JSON>(.*)</JSON>", text, flags=re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except Exception:
            pass
    # Try single->double quote sanitize
    try:
        cand = text.strip().replace("\n", " ")
        cand = re.sub(r"(\w)'(\w)", r"\1’\2", cand)
        cand = cand.replace("'", '"')
        return json.loads(cand)
    except Exception as exc:
        raise ValueError("Could not parse JSON from model output: " + str(exc))

def generate_quiz_with_retries(topic: str, attempts: int = 2) -> List[Dict]:
    """Try to generate & parse quiz JSON with 1-2 attempts, using different instructions if needed."""
    # first attempt: normal strict prompt
    prompt = QUIZ_PROMPT
    for i in range(attempts):
        raw = call_openai(prompt, user_input=topic, temperature=0.0, max_output_tokens=1400)
        try:
            parsed = extract_json(raw)
            # validate structure
            if not isinstance(parsed, list) or len(parsed) != 10:
                raise ValueError("Parsed JSON not length 10")
            normalized = []
            for item in parsed:
                if not isinstance(item, dict):
                    raise ValueError("Invalid item")
                q = item.get("question")
                opts = item.get("options")
                ans = item.get("answer")
                diff = item.get("difficulty", "Medium")
                if not q or not isinstance(opts, list) or len(opts) != 4 or ans not in [0,1,2,3]:
                    raise ValueError("Invalid question format")
                normalized.append({
                    "question": q.strip(),
                    "options": [str(x).strip() for x in opts],
                    "answer": int(ans),
                    "difficulty": diff
                })
            return normalized
        except Exception as e:
            # second attempt: ask model to wrap JSON with <JSON>...</JSON> and nothing else
            if i == 0:
                prompt = "IMPORTANT: Output ONLY the JSON array. If you add comments, wrap the JSON inside <JSON> ... </JSON> tags. " + QUIZ_PROMPT
                continue
            # else fallback to raising and let caller fallback
            raise

# -----------------------
# PDF helpers (using fpdf, but transliterate unicode -> ascii with unidecode)
# -----------------------
def markdown_to_pdf_with_images(md_text: str, title: str = "Study Notes", image_urls: List[str] = None) -> BytesIO:
    """Convert markdown to PDF with embedded images."""
    # sanitize: transliterate unicode to ascii
    safe_text = unidecode(md_text)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, title, ln=True)
    pdf.ln(4)

    in_code = False
    image_count = 0
    
    for raw in safe_text.splitlines():
        line = raw.rstrip()

        # code fence
        if line.strip().startswith("```"):
            if not in_code:
                in_code = True
                pdf.set_font("Courier", size=9)
                pdf.ln(2)
                continue
            else:
                in_code = False
                pdf.set_font("Arial", size=11)
                pdf.ln(2)
                continue

        if in_code:
            pdf.multi_cell(0, 6, line)
            continue

        # headers
        if line.startswith("# "):
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 8, line[2:], ln=True)
            continue
        if line.startswith("## "):
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 7, line[3:], ln=True)
            continue
        if line.startswith("### "):
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 6, line[4:], ln=True)
            continue

        # bold/italic
        if line.startswith("**") and line.endswith("**"):
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 6, line[2:-2], ln=True)
            continue

        # lists
        if re.match(r"^\s*([-*])\s+", line):
            bullet = re.sub(r"^\s*([-*])\s+", "- ", line)
            pdf.multi_cell(0, 6, bullet)
            continue

        # numbered lists
        if re.match(r"^\s*\d+\.\s+", line):
            pdf.multi_cell(0, 6, line)
            continue

        # normal paragraph
        if line.strip() == "":
            pdf.ln(2)
        else:
            pdf.set_font("Arial", size=11)
            pdf.multi_cell(0, 6, line)

    # Add images if available
    if image_urls:
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 8, "Generated Educational Images", ln=True)
        pdf.ln(4)
        
        for i, image_url in enumerate(image_urls):
            try:
                # Add image placeholder text since we can't embed URLs directly
                pdf.set_font("Arial", size=10)
                pdf.cell(0, 6, f"Image {i+1}: {image_url}", ln=True)
                pdf.ln(2)
            except Exception as e:
                pdf.cell(0, 6, f"Image {i+1}: [Image could not be embedded]", ln=True)

    # finalize -- use dest='S' to get bytes (string), then encode latin-1 (safe after unidecode)
    out_str = pdf.output(dest="S")
    result_bytes = out_str.encode("latin-1", errors="ignore")
    bio = BytesIO(result_bytes)
    bio.seek(0)
    return bio

def markdown_to_pdf_bytes(md_text: str, title: str = "Study Notes") -> BytesIO:
    """
    Simple Markdown-to-PDF using fpdf.
    To avoid latin-1 encoding errors, we first transliterate Unicode to ASCII using unidecode.
    This preserves readability and avoids encoding exceptions reliably.
    """
    # sanitize: transliterate unicode to ascii
    safe_text = unidecode(md_text)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, title, ln=True)
    pdf.ln(4)

    in_code = False
    for raw in safe_text.splitlines():
        line = raw.rstrip()

        # code fence
        if line.strip().startswith("```"):
            if not in_code:
                in_code = True
                pdf.set_font("Courier", size=9)
                pdf.ln(2)
                continue
            else:
                in_code = False
                pdf.set_font("Arial", size=11)
                pdf.ln(2)
                continue

        if in_code:
            pdf.set_font("Courier", size=9)
            pdf.multi_cell(0, 6, line)
            continue

        # Headings
        if line.startswith("# "):
            pdf.set_font("Arial", "B", 14)
            pdf.multi_cell(0, 8, line.replace("# ", "").strip())
            pdf.set_font("Arial", size=11)
            pdf.ln(1)
            continue
        if line.startswith("## "):
            pdf.set_font("Arial", "B", 12)
            pdf.multi_cell(0, 7, line.replace("## ", "").strip())
            pdf.set_font("Arial", size=11)
            continue
        if line.startswith("### "):
            pdf.set_font("Arial", "B", 11)
            pdf.multi_cell(0, 6, line.replace("### ", "").strip())
            pdf.set_font("Arial", size=11)
            continue

        # lists
        if re.match(r"^\s*([-*])\s+", line):
            bullet = re.sub(r"^\s*([-*])\s+", "- ", line)
            pdf.multi_cell(0, 6, bullet)
            continue

        # numbered lists
        if re.match(r"^\s*\d+\.\s+", line):
            pdf.multi_cell(0, 6, line)
            continue

        # normal paragraph
        if line.strip() == "":
            pdf.ln(2)
        else:
            pdf.set_font("Arial", size=11)
            pdf.multi_cell(0, 6, line)

    # finalize -- use dest='S' to get bytes (string), then encode latin-1 (safe after unidecode)
    out_str = pdf.output(dest="S")
    result_bytes = out_str.encode("latin-1", errors="ignore")
    bio = BytesIO(result_bytes)
    bio.seek(0)
    return bio

def quiz_pdf_bytes(quiz_list: List[Dict], title: str = "Quiz") -> BytesIO:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, title, ln=True)
    pdf.ln(6)
    pdf.set_font("Arial", size=12)
    for i, q in enumerate(quiz_list, start=1):
        pdf.multi_cell(0, 8, f"Q{i}. ({q.get('difficulty','')}) {q['question']}")
        for idx, opt in enumerate(q.get("options", [])):
            pdf.multi_cell(0, 8, f"   {chr(65+idx)}) {opt}")
        pdf.ln(2)
    out = pdf.output(dest="S").encode("latin-1")
    return BytesIO(out)

def answer_key_pdf_bytes(quiz_list: List[Dict], title: str = "Answer Key") -> BytesIO:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, title, ln=True)
    pdf.ln(6)
    pdf.set_font("Arial", size=12)
    for i, q in enumerate(quiz_list, start=1):
        ans_idx = q.get("answer")
        pdf.multi_cell(0, 8, f"Q{i}. {q['question']}")
        pdf.multi_cell(0, 8, f"Correct: {chr(65+ans_idx)}) {q['options'][ans_idx]}")
        pdf.ln(2)
    out = pdf.output(dest="S").encode("latin-1")
    return BytesIO(out)

# -----------------------
# Streamlit UI (outline -> confirm -> generate)
# -----------------------
st.set_page_config(page_title="OpenAI Notes & Quiz (gpt-4o)", layout="wide")
st.title("📘 OpenAI — In-depth Notes & Quiz (gpt-4o)")


with st.sidebar:
    st.markdown("### 📋 Instructions")
    st.markdown("1. Enter your topic below")
    st.markdown("2. Click 'Expand' to see outline")
    st.markdown("3. Click 'Confirm' to generate content")
    st.markdown(f"**Model:** {MODEL_NAME}")
    
    st.markdown("---")
    st.subheader("⚙️ Settings")
    num_images = st.slider("Number of images:", min_value=1, max_value=5, value=3)
    st.session_state['num_images'] = num_images
    
    st.markdown("---")
    st.subheader("🛠️ Quick Tools")
    
    # Quick image generation
    with st.expander("🖼️ Generate Single Image"):
        image_topic = st.text_input("Topic:", placeholder="e.g., Machine Learning", key="quick_image")
        if st.button("Generate", key="btn_image"):
            if image_topic.strip():
                with st.spinner("Generating..."):
                    image_prompt = create_image_prompt_from_topic(image_topic)
                    image_url = generate_image_with_dalle(image_prompt)
                    if not image_url.startswith("Error"):
                        st.image(image_url, caption=f"Generated for: {image_topic}", use_column_width=True)
                        st.success("✅ Generated!")
                    else:
                        st.error(f"❌ Failed: {image_url}")
            else:
                st.warning("⚠️ Enter a topic")
    
    # Quick references generation
    with st.expander("📚 Generate References"):
        ref_topic = st.text_input("Topic:", placeholder="e.g., Machine Learning", key="quick_refs")
        if st.button("Generate", key="btn_refs"):
            if ref_topic.strip():
                with st.spinner("Generating..."):
                    refs_result = generate_enhanced_references(ref_topic)
                    if not refs_result.startswith("Error"):
                        st.markdown("**Generated References:**")
                        st.markdown(refs_result)
                        st.success("✅ Generated!")
                    else:
                        st.error(f"❌ Failed: {refs_result}")
            else:
                st.warning("⚠️ Enter a topic")

st.markdown("---")
st.markdown("### 📝 Enter Your Topic")
topic = st.text_input("", placeholder="e.g., Machine Learning, Python Programming, Data Structures...", label_visibility="collapsed")

col_left, col_right = st.columns([2,1])

# Expand outline
col_btn1, col_btn2 = st.columns([1, 4])
with col_btn1:
    if st.button("🔍 Expand Outline", type="primary", use_container_width=True):
        if not topic.strip():
            st.warning("⚠️ Please enter a topic first.")
        else:
            with st.spinner("🔄 Generating outline..."):
                out_raw = call_openai(OUTLINE_PROMPT, user_input=topic, temperature=0.0, max_output_tokens=300)
            if out_raw.startswith("__ERROR__"):
                st.error("❌ Error generating outline: " + out_raw)
            else:
                st.session_state['outline'] = out_raw
                st.success("✅ Outline ready! Review and confirm to generate content.")

# show outline and confirm
if 'outline' in st.session_state:
    st.markdown("---")
    with col_left:
        st.subheader("📋 Generated Outline")
        with st.container():
            st.markdown(st.session_state['outline'])
    with col_right:
        st.subheader("🚀 Ready to Generate")
        if st.button("✅ Confirm & Generate Content", type="primary", use_container_width=True):
            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Generate notes
            status_text.text("📚 Generating comprehensive notes...")
            progress_bar.progress(20)
            notes_md = call_openai(NOTES_PROMPT, user_input=topic, temperature=0.0, max_output_tokens=6000)
            if notes_md.startswith("__ERROR__"):
                st.error("❌ Error generating notes: " + notes_md)
            else:
                st.session_state['notes_md'] = notes_md
                progress_bar.progress(40)
                
            # Generate multiple images with DALL-E
            status_text.text("🖼️ Generating educational images...")
            progress_bar.progress(60)
            num_images = st.session_state.get('num_images', 3)
            image_urls = generate_multiple_images_with_dalle(topic, num_images, notes_md[:500])
            if image_urls:
                st.session_state['generated_images'] = image_urls
                st.session_state['image_prompts'] = [create_image_prompt_from_topic(f"Aspect {i+1} of {topic}", notes_md[:200]) for i in range(len(image_urls))]
                progress_bar.progress(80)
            else:
                st.warning("⚠️ Failed to generate images")
            
            # Generate enhanced references
            status_text.text("📚 Generating references...")
            enhanced_refs = generate_enhanced_references(topic)
            if not enhanced_refs.startswith("Error"):
                st.session_state['enhanced_references'] = enhanced_refs
                progress_bar.progress(90)
            else:
                st.warning("⚠️ Failed to generate references")

            # Generate quiz
            status_text.text("📝 Generating quiz questions...")
            progress_bar.progress(95)
            try:
                quiz_list = generate_quiz_with_retries(topic, attempts=2)
                st.session_state['quiz'] = quiz_list
                st.session_state['answers'] = [None] * len(quiz_list)
                st.session_state['show_key'] = False
                progress_bar.progress(100)
                status_text.text("✅ Content generation complete!")
                st.success("🎉 All content generated successfully!")
            except Exception as e:
                st.error("❌ Quiz generation failed: " + str(e))
                st.info("🔄 Falling back to deterministic quiz...")
                # deterministic fallback
                base = st.session_state.get('notes_md', topic)
                lines = [ln.strip() for ln in base.splitlines() if ln.strip()]
                fallback = []
                for i in range(10):
                    snippet = lines[i % len(lines)] if lines else f"Fact about {topic}"
                    qtext = f"Which statement about the topic is true? ({snippet[:80]})"
                    opts = [f"{snippet} (true)", "Incorrect option A", "Incorrect option B", "Incorrect option C"]
                    diff = "Easy" if i < 4 else ("Medium" if i < 7 else "Hard")
                    fallback.append({"question": qtext, "options": opts, "answer": 0, "difficulty": diff})
                st.session_state['quiz'] = fallback
                st.session_state['answers'] = [None]*len(fallback)
                st.session_state['show_key'] = False
                progress_bar.progress(100)
                status_text.text("✅ Content generation complete!")
                st.success("🎉 Content generated with fallback quiz!")

# Display notes & download
if 'notes_md' in st.session_state:
    with col_left:
        
        st.header("📚 In-Depth Notes")
        
        # Display table of contents in an expandable section
        toc = extract_table_of_contents(st.session_state['notes_md'])
        if toc:
            with st.expander("📋 Table of Contents", expanded=True):
                st.markdown(toc)
        
        # Display the full notes
        st.markdown(st.session_state['notes_md'])
        
        # Display generated images if available
        if 'generated_images' in st.session_state and st.session_state['generated_images']:
            st.subheader("🖼️ Generated Educational Images")
            
            # Display images in a grid
            images = st.session_state['generated_images']
            cols = st.columns(min(len(images), 3))  # Max 3 columns
            
            for i, image_url in enumerate(images):
                with cols[i % 3]:
                    st.image(image_url, caption=f"Educational illustration {i+1}", use_column_width=True)
            
            # Show the prompts used for image generation
            with st.expander("View image generation prompts"):
                prompts = st.session_state.get('image_prompts', [])
                for i, prompt in enumerate(prompts):
                    st.text(f"Image {i+1}: {prompt}")
                
            # Option to regenerate all images
            if st.button("🔄 Regenerate All Images"):
                with st.spinner("Generating new images..."):
                    num_images = st.session_state.get('num_images', 3)
                    new_image_urls = generate_multiple_images_with_dalle(topic, num_images, st.session_state.get('notes_md', '')[:500])
                    if new_image_urls:
                        st.session_state['generated_images'] = new_image_urls
                        st.success(f"Generated {len(new_image_urls)} new images!")
                        st.rerun()
                    else:
                        st.error("Failed to regenerate images.")
        
        
        # Display enhanced references if available
        if 'enhanced_references' in st.session_state and st.session_state['enhanced_references']:
            st.subheader("📚 Enhanced References & Resources")
            st.markdown(st.session_state['enhanced_references'])
            
            # Option to regenerate references
            if st.button("🔄 Regenerate References"):
                with st.spinner("Generating new references..."):
                    new_refs = generate_enhanced_references(topic)
                    if not new_refs.startswith("Error"):
                        st.session_state['enhanced_references'] = new_refs
                        st.success("New references generated!")
                        st.rerun()
                    else:
                        st.error("Failed to regenerate references.")
        # build PDF bytes (transliteration inside function)
        notes_pdf = markdown_to_pdf_bytes(st.session_state['notes_md'], title=f"Notes: {topic}")
        st.download_button("📥 Download Notes (PDF)", notes_pdf, file_name="notes.pdf", mime="application/pdf")

# Display quiz & interactions
if 'quiz' in st.session_state:
    quiz = st.session_state['quiz']
    with col_right:
        st.header("📝 Quiz (10 Questions)")
        order = ["Easy", "Medium", "Hard"]
        grouped = {k: [] for k in order}
        for idx, q in enumerate(quiz):
            diff = q.get('difficulty', 'Medium')
            grouped.setdefault(diff, []).append(idx)

        answers = st.session_state.get('answers', [None]*len(quiz))
        progress = int((sum(1 for a in answers if a is not None) / len(quiz)) * 100) if len(quiz) else 0
        st.progress(progress)

        for diff in order:
            idxs = grouped.get(diff, [])
            if not idxs:
                continue
            with st.expander(f"{diff} — {len(idxs)} Qs", expanded=(diff == "Easy")):
                for idx in idxs:
                    q = quiz[idx]
                    st.markdown(f"**Q{idx+1}.** {q['question']}")
                    opts_with_placeholder = ["— Select an option —"] + q['options']
                    key = f"q_{idx}"
                    prev = st.session_state['answers'][idx]
                    default_index = (prev + 1) if prev is not None else 0
                    if default_index < 0 or default_index >= len(opts_with_placeholder):
                        default_index = 0
                    selected = st.radio("Select your answer:", opts_with_placeholder, key=key, index=default_index, label_visibility="collapsed")
                    if selected == "— Select an option —":
                        st.session_state['answers'][idx] = None
                    else:
                        try:
                            sel_idx = q['options'].index(selected)
                        except ValueError:
                            sel_idx = opts_with_placeholder.index(selected) - 1
                        st.session_state['answers'][idx] = int(sel_idx)
                    st.markdown("---")

        # Submit button and answer key access
        col1, col2 = st.columns([1, 1])
        
        with col1:
            all_ans = all(a is not None for a in st.session_state.get('answers', []))
            if not all_ans:
                st.warning("Answer all questions to submit the quiz.")
                submit_disabled = True
            else:
                submit_disabled = False
                
            if st.button("📝 Submit Quiz", disabled=submit_disabled, type="primary"):
                st.session_state['quiz_submitted'] = True
                st.session_state['show_key'] = True
                st.success("Quiz submitted! Check your results below.")
                st.rerun()
        
        with col2:
            if st.button("🔍 View Answer Key", help="View answers without submitting"):
                st.session_state['show_key'] = True
                st.info("Answer key revealed. Your answers are not submitted.")
        
        # Reset quiz option
        if st.session_state.get('quiz_submitted', False) or st.session_state.get('show_key', False):
            if st.button("🔄 Reset Quiz", help="Start the quiz over"):
                # Reset quiz state
                st.session_state['answers'] = [None] * len(quiz)
                st.session_state['show_key'] = False
                st.session_state['quiz_submitted'] = False
                st.success("Quiz reset! You can now take it again.")
                st.rerun()

        if st.session_state.get('show_key'):
            answers = st.session_state['answers']
            score = 0
            lines = []
            
            # Calculate score and prepare results
            for i, q in enumerate(quiz):
                user_idx = answers[i]
                correct_idx = q['answer']
                if user_idx == correct_idx:
                    score += 1
                user_label = chr(65 + user_idx) if user_idx is not None else "N/A"
                correct_label = chr(65 + correct_idx)
                lines.append(f"Q{i+1}. ({q.get('difficulty','')}) {q['question']}\nCorrect: {correct_label}) {q['options'][correct_idx]}\nYour answer: {user_label}) {q['options'][user_idx] if user_idx is not None else ''}\n{'✅ Correct' if user_idx==correct_idx else '❌ Wrong'}\n")
            
            # Display results with submission status
            percentage = score/len(quiz)*100
            if st.session_state.get('quiz_submitted', False):
                st.subheader(f"📊 Quiz Results: {score}/{len(quiz)} ({percentage:.1f}%)")
                st.success("🎉 Quiz submitted successfully!")
            else:
                st.subheader(f"📊 Answer Key Preview: {score}/{len(quiz)} ({percentage:.1f}%)")
                st.info("💡 This is a preview. Submit the quiz to record your score.")
            
            # Performance feedback
            if percentage >= 90:
                st.success("🌟 Excellent work! You've mastered this topic!")
            elif percentage >= 80:
                st.success("👍 Great job! You have a solid understanding.")
            elif percentage >= 70:
                st.warning("📚 Good effort! Review the incorrect answers to improve.")
            elif percentage >= 60:
                st.warning("📖 Keep studying! Focus on the areas you missed.")
            else:
                st.error("📚 More study needed. Review the material and try again.")
            
            st.subheader("🔑 Detailed Answer Key")
            for block in lines:
                st.code(block)

            # downloads
            st.subheader("📥 Downloads")
            quiz_pdf = quiz_pdf_bytes(quiz, title=f"Quiz: {topic}")
            ans_pdf = answer_key_pdf_bytes(quiz, title=f"Answer Key: {topic}")
            st.download_button("📥 Download Quiz (PDF)", quiz_pdf, file_name="quiz.pdf", mime="application/pdf")
            st.download_button("📥 Download Answer Key (PDF)", ans_pdf, file_name="answer_key.pdf", mime="application/pdf")

st.caption("If parsing sometimes fails, press Confirm → Generate again. We try a second parsing attempt automatically before falling back.")
