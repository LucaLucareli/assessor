from prompt_agentes import (
    prompt_roteador,
    prompt_financeiro,
    prompt_agenda,
    prompt_academia,
    prompt_alimentacao,
    prompt_orquestrador
)
from langchain.memory import ChatMessageHistory
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.chat_models import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from pg_tools import TOOLS
import unicodedata
import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8")
load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.7,
    top_p=0.95,
    google_api_key=os.getenv("GEMINI_API_KEY"),
)

llm_fast = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0,
    google_api_key=os.getenv("GEMINI_API_KEY"),
)

agent_roteador = create_tool_calling_agent(llm_fast, prompt=prompt_roteador)
executor_roteador = AgentExecutor(agent=agent_roteador, verbose=False)

agent_financeiro = create_tool_calling_agent(llm, TOOLS, prompt=prompt_financeiro)
executor_financeiro = AgentExecutor(agent=agent_financeiro, tools=TOOLS, verbose=False)

agent_agenda = create_tool_calling_agent(llm, TOOLS, prompt=prompt_agenda)
executor_agenda = AgentExecutor(agent=agent_agenda, tools=TOOLS, verbose=False)

agent_academia = create_tool_calling_agent(llm, TOOLS, prompt=prompt_academia)
executor_academia = AgentExecutor(agent=agent_academia, tools=TOOLS, verbose=False)

agent_alimentacao = create_tool_calling_agent(llm, TOOLS, prompt=prompt_alimentacao)
executor_alimentacao = AgentExecutor(agent=agent_alimentacao, tools=TOOLS, verbose=False)

agent_orquestrador = create_tool_calling_agent(llm_fast, prompt=prompt_orquestrador)
executor_orquestrador = AgentExecutor(agent=agent_orquestrador, verbose=False)

store = {}
def get_session_history(session_id: str) -> ChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

def sanitize_input(text: str) -> str:
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )

while True:
    try:
        user_input = input("Digite uma pergunta (ou 'sair' para encerrar): ")
        if user_input.lower() == "sair":
            print("Encerrando o assistente...")
            break

        # Sanitizar entrada para evitar caracteres que quebrem o decode no Windows
        safe_input = sanitize_input(user_input)

        # resposta = chain.invoke(
        #     {"input": safe_input},
        #     config={"configurable": {"session_id": "Qualquer coisa"}}
        # )

        # Garantir que a saída seja string UTF-8 válida
        # raw_output = resposta.get('output', '')
        # if isinstance(raw_output, bytes):
        #     output_text = raw_output.decode('utf-8', errors='replace')
        # else:
        #     output_text = str(raw_output)

        # print(output_text)

    except Exception as e:
        print("Erro ao consumir a API:", e)
