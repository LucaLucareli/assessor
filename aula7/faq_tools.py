from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import GoogleGenerativeAIEmbedding
from langchain.document_loaders import PyPDFLoader
from langchain.vectorstores import FAISS
import os

PDF_PATH = "./FAQ_assessor_v1.1.pdf"

loader = PyPDFLoader(PDF_PATH)
docs = loader.load()

splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=150)
chunks = splitter.split_documents(docs)

embedding = GoogleGenerativeAIEmbedding(
    model="model/text-embedding-004",
    google_gemini_api=os.getenv("GEMINI_API_KEY"),
    transport="rest"
)

db = FAISS.from_documents(chunks, embedding)

def get_faq_context(question: str, k: int = 6):
    results = db.similarity_search(question, k=k)
    context = "\n\n".join([doc.page_content for doc in results])
    return context
