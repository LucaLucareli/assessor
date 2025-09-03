from pydantic import BaseModel, Field
from langchain.tools import tool
from dotenv import load_dotenv
from typing import Optional
import psycopg2
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")  


def get_conn():
    return psycopg2.connect(DATABASE_URL)

def _resolve_type_id(cur, type_id: Optional[int], type_name: Optional[str]) -> Optional[int]:
    if type_name:
        t = type_name.strip().upper()
        if t == "EXPENSE":
            t = "EXPENSES"
        cur.execute("SELECT id FROM transaction_types WHERE UPPER(type)=%s LIMIT 1;", (t,))
        row = cur.fetchone()
        return row[0] if row else None
    if type_id:
        return int(type_id)
    return 2


class AddTransactionArgs(BaseModel):
    amount: float = Field(..., description="Valor da transação (use positivo).")
    source_text: str = Field(..., description="Texto original do usuário.")
    occurred_at: Optional[str] = Field(
        default=None,
        description="Timestamp ISO 8601; se ausente, usa NOW() no banco."
    )
    type_id: Optional[int] = Field(default=None, description="ID em transaction_types (1=INCOME, 2=EXPENSES, 3=TRANSFER).")
    type_name: Optional[str] = Field(default=None, description="Nome do tipo: INCOME | EXPENSES | TRANSFER.")
    category_id: Optional[int] = Field(default=None, description="FK de categories (opcional).")
    description: Optional[str] = Field(default=None, description="Descrição (opcional).")
    payment_method: Optional[str] = Field(default=None, description="Forma de pagamento (opcional).")

class AddWorkoutArgs(BaseModel):
    title: str = Field(..., description="Nome do treino (ex: 'Treino A - Peito e Tríceps').")
    notes: Optional[str] = Field(default=None, description="Observações do treino.")
    scheduled_at: Optional[str] = Field(default=None, description="Timestamp ISO 8601; se ausente, usa NOW().")
    duration_min: Optional[int] = Field(default=None, description="Duração em minutos.")

class AddMealArgs(BaseModel):
    title: str = Field(..., description="Nome da refeição (ex: 'Café da manhã').")
    occurred_at: Optional[str] = Field(default=None, description="Timestamp ISO 8601; se ausente, usa NOW().")
    notes: Optional[str] = Field(default=None, description="Observações da refeição.")


@tool("add_transaction", args_schema=AddTransactionArgs)
def add_transaction(
    amount: float,
    source_text: str,
    occurred_at: Optional[str] = None,
    type_id: Optional[int] = None,
    type_name: Optional[str] = None,
    category_id: Optional[int] = None,
    description: Optional[str] = None,
    payment_method: Optional[str] = None,
) -> dict:
    """Insere uma transação financeira no banco de dados Postgres."""
    conn = get_conn()
    cur = conn.cursor()
    try:
        resolved_type_id = _resolve_type_id(cur, type_id, type_name)
        if not resolved_type_id:
            return {"status": "error", "message": "Tipo inválido (use type_id ou type_name: INCOME/EXPENSES/TRANSFER)."}

        if occurred_at:
            cur.execute(
                """
                INSERT INTO transactions
                    (amount, type, category_id, description, payment_method, occurred_at, source_text)
                VALUES
                    (%s, %s, %s, %s, %s, %s::timestamptz, %s)
                RETURNING id, occurred_at;
                """,
                (amount, resolved_type_id, category_id, description, payment_method, occurred_at, source_text),
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
                (amount, resolved_type_id, category_id, description, payment_method, source_text),
            )

        new_id, occurred = cur.fetchone()
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
        new_id, scheduled = cur.fetchone()
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
        new_id, occurred = cur.fetchone()
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

TOOLS = [
    add_transaction,
    add_workout,
    add_meal
]
