from pydantic import BaseModel, Field
from langchain.tools import tool
from dotenv import load_dotenv
from typing import Optional
import unicodedata
import psycopg2
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def get_conn():
    return psycopg2.connect(DATABASE_URL)


TYPE_LIST = {
    "INCOME": "INCOME",
    "ENTRADA": "INCOME",
    "RECEITA": "INCOME",
    "SÁLARIO": "INCOME",
    "EXPENSE": "EXPENSES",
    "EXPENSES": "EXPENSES",
    "DESPESA": "EXPENSES",
    "GASTO": "EXPENSES",
    "TRANSFER": "TRANSFER",
    "TRANSFERÊNCIA": "TRANSFER",
    "TRANSFERENCIA": "TRANSFER",
}


def _resolve_type_id(
    cur, type_id: Optional[int], type_name: Optional[str]
) -> Optional[int]:
    if type_name:
        t = type_name.strip().upper()
        if t in TYPE_LIST:
            t = TYPE_LIST[t]
        cur.execute(
            "SELECT id FROM transaction_types WHERE UPPER(type)=%s LIMIT 1;", (t,)
        )
        row = cur.fetchone()
        return row[0] if row else None
    if type_id:
        return int(type_id)
    return 2


def normalize(text: str) -> str:
    text = text.upper()
    text = "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )
    return text


def _resolve_category_id(
    cur, category_id: Optional[int] = None, category_name: Optional[str] = None
) -> Optional[int]:
    if category_id:
        return category_id

    if category_name:
        cur.execute("SELECT id, name FROM categories")
        rows = cur.fetchall()
        CATEGORY_MAP = {normalize(name): id_ for id_, name in rows}

        key = normalize(category_name.strip())
        mapped_id = CATEGORY_MAP.get(key)
        if mapped_id:
            return mapped_id

    return None


class AddTransactionArgs(BaseModel):
    amount: float = Field(..., description="Valor da transação (use positivo).")
    source_text: str = Field(..., description="Texto original do usuário.")
    occurred_at: Optional[str] = Field(
        default=None, description="Timestamp ISO 8601; se ausente, usa NOW() no banco."
    )
    type_id: Optional[int] = Field(
        default=None,
        description="ID em transaction_types (opcional) (1=INCOME, 2=EXPENSES, 3=TRANSFER).",
    )
    type_name: Optional[str] = Field(
        default=None,
        description="Nome do tipo (opcional) : INCOME | EXPENSES | TRANSFER.",
    )
    category_id: Optional[int] = Field(
        default=None,
        description="FK de categories (opcional):  (1=comida, 2=besteira, 3=estudo, 4=férias, 5=transporte, 6=moradia, 7=saúde, 8=lazer, 9=contas, 10=investimento, 11=presente, 12=outros)",
    )
    category_name: Optional[str] = Field(
        default=None,
        description="Nome da categories (opcional) : (comida, besteira, estudo, férias, transporte, moradia, saúde, lazer, contas, investimento, presente, outros)",
    )
    description: Optional[str] = Field(
        default=None, description="Descrição (opcional)."
    )
    payment_method: Optional[str] = Field(
        default=None, description="Forma de pagamento (opcional)."
    )


class AddWorkoutArgs(BaseModel):
    title: str = Field(
        ..., description="Nome do treino (ex: 'Treino A - Peito e Tríceps')."
    )
    notes: Optional[str] = Field(default=None, description="Observações do treino.")
    scheduled_at: Optional[str] = Field(
        default=None, description="Timestamp ISO 8601; se ausente, usa NOW()."
    )
    duration_min: Optional[int] = Field(default=None, description="Duração em minutos.")


class AddMealArgs(BaseModel):
    title: str = Field(..., description="Nome da refeição (ex: 'Café da manhã').")
    occurred_at: Optional[str] = Field(
        default=None, description="Timestamp ISO 8601; se ausente, usa NOW()."
    )
    notes: Optional[str] = Field(default=None, description="Observações da refeição.")


@tool("add_transaction", args_schema=AddTransactionArgs)
def add_transaction(
    amount: float,
    source_text: str,
    occurred_at: Optional[str] = None,
    type_id: Optional[int] = None,
    type_name: Optional[str] = None,
    category_id: Optional[int] = None,
    category_name: Optional[str] = None,
    description: Optional[str] = None,
    payment_method: Optional[str] = None,
) -> dict:
    """Insere uma transação financeira no banco de dados Postgres."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        resolved_type_id = _resolve_type_id(cur, type_id, type_name)
        if not resolved_type_id:
            return {
                "status": "error",
                "message": "Tipo inválido (use type_id ou type_name: INCOME/EXPENSES/TRANSFER).",
            }

        resolve_category_id = _resolve_category_id(cur, category_id, category_name)

        if occurred_at:
            cur.execute(
                """
                INSERT INTO transactions
                    (amount, type, category_id, description, payment_method, occurred_at, source_text)
                VALUES
                    (%s, %s, %s, %s, %s, %s::timestamptz, %s)
                RETURNING id, occurred_at;
                """,
                (
                    amount,
                    resolved_type_id,
                    resolve_category_id,
                    description,
                    payment_method,
                    occurred_at,
                    source_text,
                ),
            )
        else:
            cur.execute(
                """
                INSERT INTO transactions
                    (amount, type, category_id, description, payment_method, occurred_at, source_text)
                VALUES
                    (%s, %s, %s, %s, %s, NOW(), %s)
                RETURNING id, occurred_at;
                """,
                (
                    amount,
                    resolved_type_id,
                    category_id,
                    description,
                    payment_method,
                    source_text,
                ),
            )

        row = cur.fetchone()

        if row is not None:
            new_id, occurred = row
        else:
            new_id, occurred = None, None

        conn.commit()
        return {"status": "ok", "id": new_id, "occurred_at": str(occurred)}

    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


@tool("add_workout", args_schema=AddWorkoutArgs)
def add_workout(
    title: str,
    notes: Optional[str] = None,
    scheduled_at: Optional[str] = None,
    duration_min: Optional[int] = None,
) -> dict:
    """Insere um treino no banco de dados Postgres."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        if scheduled_at:
            cur.execute(
                """
                INSERT INTO workouts (title, notes, scheduled_at, duration_min, source_text)
                VALUES (%s, %s, %s::timestamptz, %s, %s)
                RETURNING id, scheduled_at;
                """,
                (title, notes, scheduled_at, duration_min, title),
            )
        else:
            cur.execute(
                """
                INSERT INTO workouts (title, notes, scheduled_at, duration_min, source_text)
                VALUES (%s, %s, NOW(), %s, %s)
                RETURNING id, scheduled_at;
                """,
                (title, notes, duration_min, title),
            )

        row = cur.fetchone()

        if row is not None:
            new_id, scheduled = row
        else:
            new_id, scheduled = None, None

        conn.commit()
        return {"status": "ok", "id": new_id, "scheduled_at": str(scheduled)}
    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


@tool("add_meal", args_schema=AddMealArgs)
def add_meal(
    title: str,
    occurred_at: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    """Insere uma refeição no banco de dados Postgres."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        if occurred_at:
            cur.execute(
                """
                INSERT INTO meals (title, occurred_at, notes, source_text)
                VALUES (%s, %s::timestamptz, %s, %s)
                RETURNING id, occurred_at;
                """,
                (title, occurred_at, notes, title),
            )
        else:
            cur.execute(
                """
                INSERT INTO meals (title, occurred_at, notes, source_text)
                VALUES (%s, NOW(), %s, %s)
                RETURNING id, occurred_at;
                """,
                (title, notes, title),
            )

        row = cur.fetchone()

        if row is not None:
            new_id, occurred = row
        else:
            new_id, occurred = None, None

        conn.commit()
        return {"status": "ok", "id": new_id, "occurred_at": str(occurred)}
    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


TOOLS = [add_transaction, add_workout, add_meal]
