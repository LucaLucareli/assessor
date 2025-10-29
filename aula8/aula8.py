from prompt_agentes import (
    prompt_roteador,
    prompt_financeiro,
    prompt_agenda,
    prompt_academia,
    prompt_alimentacao,
    prompt_orquestrador,
    prompt_faq,
)
from langchain_core.runnables import RunnableWithMessageHistory, RunnablePassthrough
from langchain.agents import create_tool_calling_agent
from langchain.agents import AgentExecutor
from langchain_google_genai.chat_models import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
from langchain_community.chat_message_histories import ChatMessageHistory
from faq_tools import get_faq_context
from operator import itemgetter
from dotenv import load_dotenv
from pg_tools import TOOLS
import unicodedata
import os
import sys
import io
import re
from langgraph.graph import StateGraph, START, END

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8")
load_dotenv()

store = {}
def get_session_history(session_id: str) -> ChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

def sanitize_input(text) -> str:
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="replace")
    else:
        text = str(text)

    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )

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

chain_roteador = RunnableWithMessageHistory( 
    prompt_roteador | llm_fast | StrOutputParser(),
    get_session_history=get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history"
)

agent_financeiro = create_tool_calling_agent(llm, TOOLS, prompt=prompt_financeiro)
executor_financeiro = AgentExecutor(agent=agent_financeiro, tools=TOOLS, verbose=False)

chain_financeiro = RunnableWithMessageHistory(
    executor_financeiro,
    get_session_history=get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history"
)

agent_agenda = create_tool_calling_agent(llm, TOOLS, prompt=prompt_agenda)
executor_agenda = AgentExecutor(agent=agent_agenda, tools=TOOLS, verbose=False)
chain_agenda = RunnableWithMessageHistory(
    executor_agenda,
    get_session_history=get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history"
)


agent_academia = create_tool_calling_agent(llm, TOOLS, prompt=prompt_academia)
executor_academia = AgentExecutor(agent=agent_academia, tools=TOOLS, verbose=False)
chain_academia = RunnableWithMessageHistory(
    executor_academia,
    get_session_history=get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history"
)


agent_alimentacao = create_tool_calling_agent(llm, TOOLS, prompt=prompt_alimentacao)
executor_alimentacao = AgentExecutor(agent=agent_alimentacao, tools=TOOLS, verbose=False)
chain_alimentacao = RunnableWithMessageHistory(
    executor_alimentacao,
    get_session_history=get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history"
)


chain_orquestrador = RunnableWithMessageHistory(
    prompt_orquestrador | llm_fast | StrOutputParser(),
    get_session_history=get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history"
)

chain_faq = (
    RunnablePassthrough.assign(
        question=lambda x: x['input'],
        context=lambda x: get_faq_context(x['input'])
    )
    | prompt_faq
    | llm_fast
    | StrOutputParser()
)

rota_map = {
    "financeiro": chain_financeiro,
    "agenda": chain_agenda,
    "academia": chain_academia,
    "alimentacao": chain_alimentacao,
    "faq": chain_faq,
    "fora_escopo": None
}

def to_safe_str(text):
    if isinstance(text, bytes):
        return text.decode('utf-8', errors='replace')
    return str(text)

CLARIFY_PATTERN = re.compile(r"CLARIFY=(.*)", re.DOTALL)
ROUTE_PATTERN = re.compile(r"ROUTE=(\w+)")

def executar_fluxo_assessor(pergunta, session_id):
    safe_input = sanitize_input(pergunta)

    resposta_roteador = to_safe_str(
        chain_roteador.invoke(
            {"input": safe_input},
            config={"configurable": {"session_id": session_id}}
        )
    )

    clarify_match = CLARIFY_PATTERN.search(resposta_roteador)
    if clarify_match:
        clarify = clarify_match.group(1).strip()
        if clarify:
            return clarify
    
    route_match = ROUTE_PATTERN.search(resposta_roteador)

    if not route_match:
        return resposta_roteador.strip()

    route = route_match.group(1)
    chain = rota_map.get(route)
    
    if not chain:
        return f"[Erro] Rota '{route}' não configurada."

    resposta_especialista = to_safe_str(
        chain.invoke(
            {"input": safe_input},
            config={"configurable": {"session_id": session_id}}
        )
    )

    resposta_orquestrador = to_safe_str(
        chain_orquestrador.invoke(
            {"input": resposta_especialista},
            config={"configurable": {"session_id": session_id}}
        )
    )
    
    return resposta_orquestrador


def router_node(state: dict) -> dict:
    resposta_roteador = chain_roteador.invoke(
        {"input": state["input"]},
        config={"configurable": {"session_id": state["session_id"]}}
    )  
   
    if not resposta_roteador.startswith("ROUTE="):
        return {"resposta_usuario": resposta_roteador}
   
    rota = resposta_roteador.split("\n", 1)[0].split("=", 1)[1].strip().lower()
    if rota not in {"financeiro", "agenda", "faq"}:
        return {"erro": f"Rota inválida: {rota}"}
 
    return {"rota": rota, "roteador": resposta_roteador, 'input':state['input'], 'session_id': state['session_id']}

def faq_node(state: dict) -> dict:
    result = chain_faq.invoke(
        {"input": state['input']}, 
        config={"configurable": {"session_id": state["session_id"]}}
    )
    
    return {"resposta_usuario": result, "session_id": state["session_id"]}

def financeiro_node(state: dict) -> dict:
    result = executor_financeiro.invoke(
        {"input": state['roteador']}, 
        config={"configurable": {"session_id": state["session_id"]}}
    )  
    return {"saida_especialista": result["output"], 'session_id': state['session_id']}

def agenda_node(state: dict) -> dict:
    result = executor_agenda.invoke(
        {"input": state['roteador']}, 
        config={"configurable": {"session_id": state["session_id"]}}
    )  
    return {"saida_especialista": result["output"], 'session_id': state['session_id']}

def orchestrator_node(state: dict) -> dict:
    resposta_final = chain_orquestrador.invoke(
        {"input": state['saida_especialista']},
        config={"configurable": {"session_id": state["session_id"]}}
    )  
    return {"resposta_usuario": resposta_final}

def decide_after_router(state: dict) -> str:
    if state.get("erro") or state.get("resposta_usuario"):
        return "end"
    rota = state.get("rota")
    if rota == "financeiro":
        return "financeiro"
    if rota == "agenda":
        return "agenda"
    if rota == "faq":
        return "faq"
    return "end"

def decide_after_specialist(state: dict) -> str:
    if state.get("erro"):
        return "end"
    return "orquestrador"


graph = StateGraph(dict)

graph.add_node("roteador", router_node)
graph.add_node("financeiro", financeiro_node)
graph.add_node("agenda", agenda_node)
graph.add_node("faq", faq_node)
graph.add_node("orquestrador", orchestrator_node)

graph.add_edge(START, "roteador")

graph.add_conditional_edges(
    "roteador",
    decide_after_router,
    {
        "financeiro": "financeiro",
        "agenda": "agenda",
        "faq": "faq",
        "end": END,
    },
)

graph.add_conditional_edges(
    "financeiro",
    decide_after_specialist,
    {"orquestrador": "orquestrador", "end": END},
)
graph.add_conditional_edges(
    "agenda",
    decide_after_specialist,
    {"orquestrador": "orquestrador", "end": END},
)

graph.add_edge("orquestrador", END)
graph.add_edge("faq", END)

app = graph.compile()


def executar_fluxo_assessor(pergunta_usuario: str, session_id: str) -> str:
    final_state = app.invoke({"input": pergunta_usuario, "session_id": session_id})
    if final_state.get("erro"):
        return f"Erro: {final_state['erro']}"
    return final_state.get("resposta_usuario", "Não foi possível responder.")

while True:
    try:
        user_input = input("> ")
        if user_input.lower() in ('sair', 'end', 'fim', 'tchau', 'bye'):
            print("Encerrando a conversa.")
            break
        
        resposta = executar_fluxo_assessor(
            pergunta_usuario=user_input, 
            session_id="PRECISA_MAS_NÃO_IMPORTA"
        )
        
        print(resposta)
        
    except Exception as e:
            print("Erro ao consumir a API:", e)
            continue
