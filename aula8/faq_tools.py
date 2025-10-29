from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv
import os

load_dotenv()

PDF_PATH = os.path.join(os.path.dirname(__file__), "FAQ_assessor_v1.1.pdf")

loader = PyPDFLoader(PDF_PATH)
docs = loader.load()

splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=150)
chunks = splitter.split_documents(docs)


api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("❌ GEMINI_API_KEY não encontrada no .env")

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004",
    google_api_key=api_key,
    transport="rest"
)

db = FAISS.from_documents(chunks, embeddings)

def get_faq_context(question: str, k: int = 6):
    results = db.similarity_search(question, k=k)
    context = "\n\n".join([doc.page_content for doc in results])
    return context
