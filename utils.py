import os
from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

# ------------------- LLM -------------------

llm = ChatGroq(
    temperature=0.2,
    groq_api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama-3.3-70b-versatile"
)

# ------------------- PDF -------------------

def extract_text(pdf):
    text = ""
    reader = PdfReader(pdf)
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

# ------------------- VECTOR STORE -------------------

def create_vector_store(text):
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)
    chunks = splitter.split_text(text)

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    return FAISS.from_texts(chunks, embeddings)

# ------------------- RAG -------------------

def get_context(vectorstore, concept, k=3):
    if vectorstore is None:
        return ""
    docs = vectorstore.similarity_search(concept, k=k)
    return "\n\n".join([doc.page_content for doc in docs])

# ------------------- CONCEPT EXTRACTION -------------------

def extract_concepts(text):
    prompt = f"""
    Extract key learning concepts from this text.
    Keep them SHORT and SIMPLE.

    Text:
    {text[:3000]}
    """
    result = llm.invoke(prompt).content

    concepts = [c.strip() for c in result.split("\n") if c.strip()]
    return concepts

# ------------------- EXPLAINER -------------------

def explain_and_question(concept, context):
    prompt = f"""
    Use ONLY this context. Do NOT add outside knowledge.

    CONTEXT:
    {context}

    Explain simply (Feynman style) and ask ONE question.

    FORMAT:
    Explanation: ...
    Question: ...
    """

    result = llm.invoke(prompt).content

    explanation, question = "", ""

    if "Question:" in result:
        parts = result.split("Question:")
        explanation = parts[0].replace("Explanation:", "").strip()
        question = parts[1].strip()
    else:
        explanation = result.strip()

    return explanation, question

# ------------------- EVALUATOR -------------------

def evaluate_answer(answer, context):
    if answer.strip() == "":
        return "Score: 0/10\nReason: Empty answer"

    prompt = f"""
    STRICT evaluation based ONLY on context:

    RULES:
    - "I don't know" → 0
    - Irrelevant → 0
    - Vague → <=3
    - Correct → 7+

    CONTEXT:
    {context}

    ANSWER:
    {answer}

    OUTPUT:
    Score: X/10
    Reason:
    """

    return llm.invoke(prompt).content

# ------------------- SCORE -------------------

def extract_score(result):
    try:
        line = [l for l in result.split("\n") if "Score" in l][0]
        score = int(line.split("/")[0].split(":")[1].strip())
        return score
    except:
        return 0

# ------------------- CORRECT ANSWER -------------------

def generate_correct_answer(context):
    prompt = f"""
    Based ONLY on this context, give a clear correct answer in 3-4 lines.

    CONTEXT:
    {context}
    """
    return llm.invoke(prompt).content