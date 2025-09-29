from pydantic import BaseModel, Field
from typing import Optional, List
from langchain.tools import tool
from dotenv import load_dotenv
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

class QueryTransactionsArgs(BaseModel):
    text: Optional[str] = Field(None, description="Texto para busca em 'source_text' ou 'description'")
    type_name: Optional[str] = Field(None, description="Nome do tipo de transação")
    date_local: Optional[str] = Field(None, description="Data exata da transação (formato YYYY-MM-DD)")
    date_from_local: Optional[str] = Field(None, description="Data inicial para filtro por intervalo (YYYY-MM-DD)")
    date_to_local: Optional[str] = Field(None, description="Data final para filtro por intervalo (YYYY-MM-DD)")
    limit: int = Field(20, description="Quantidade máxima de registros a retornar")


class EmptyArgs(BaseModel):
    pass

class DailyBalanceArgs(BaseModel):
    date_local: str = Field(..., description="Dia local no formato YYYY-MM-DD para calcular o saldo.")

class UpdateTransactionArgs(BaseModel):
    id: Optional[int] = Field(
        default=None,
        description="ID da transaÃ§Ã£o a atualizar. Se ausente, serÃ¡ feita uma busca por (match_text + date_local)."
    )
    match_text: Optional[str] = Field(
        default=None,
        description="Texto para localizar transaÃ§Ã£o quando id nÃ£o for informado (busca em source_text/description)."
    )
    date_local: Optional[str] = Field(
        default=None,
        description="Data local (YYYY-MM-DD) em America/Sao_Paulo; usado em conjunto com match_text quando id ausente."
    )
    amount: Optional[float] = Field(default=None, description="Novo valor.")
    type_id: Optional[int] = Field(default=None, description="Novo type_id (1/2/3).")
    type_name: Optional[str] = Field(default=None, description="Novo type_name: INCOME | EXPENSES | TRANSFER.")
    category_id: Optional[int] = Field(default=None, description="Nova categoria (id).")
    category_name: Optional[str] = Field(default=None, description="Nova categoria (nome).")
    description: Optional[str] = Field(default=None, description="Nova descriÃ§Ã£o.")
    payment_method: Optional[str] = Field(default=None, description="Novo meio de pagamento.")
    occurred_at: Optional[str] = Field(default=None, description="Novo timestamp ISO 8601.")

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


        new_id, occurred = cur.fetchone() or [None, None]

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

@tool(
    "query_transactions",
    args_schema=QueryTransactionsArgs,
    description="Consulta transações no banco com filtros opcionais"
)
def query_transactions(
    text: Optional[str] = None,
    type_name: Optional[str] = None,
    date_local: Optional[str] = None,
    date_from_local: Optional[str] = None,
    date_to_local: Optional[str] = None,
    limit: int = 20
) -> dict:
    conn = get_conn()
    cur = conn.cursor()
    filters = []
    params = []

    conditions = [
        (text, "(source_text ILIKE %s OR description ILIKE %s)", lambda v: [f"%{v}%", f"%{v}%"]),
        (type_name, "type = (SELECT id FROM transaction_types WHERE type ILIKE %s)", lambda v: [v]),
        (date_local, "(occurred_at AT TIME ZONE 'America/Sao_Paulo')::date = %s::date", lambda v: [v]),
        ((date_from_local, date_to_local) if date_from_local and date_to_local else None,
        "(occurred_at AT TIME ZONE 'America/Sao_Paulo')::date BETWEEN %s::date AND %s::date",
        lambda v: list(v) if v else [])
    ]

    for val, sql, to_params in conditions:
        if val:
            filters.append(sql)
            params.extend(to_params(val))

        where_clause = " AND ".join(filters)
        if where_clause:
            where_clause = "WHERE " + where_clause

        order_clause = "ORDER BY occurred_at ASC" if date_from_local or date_to_local else "ORDER BY occurred_at DESC"

    try:
        query = f"""
            SELECT t.id, t.amount, tt.type, t.category_id, t.description, t.payment_method,
                t.occurred_at AT TIME ZONE 'America/Sao_Paulo' AS occurred_local,
                t.source_text
            FROM transactions t
            JOIN transaction_types tt ON t.type = tt.id
            {where_clause}
            {order_clause}
            LIMIT %s
        """
        params.append(limit)

        cur.execute(query, params)
        results = cur.fetchall()
        cur.close()
        conn.close()

        return {"transactions": results}
    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass

@tool(
    "total_balance",
    args_schema=EmptyArgs,
    description="Retorna o saldo total considerando todas as transações, ignorando transferências (type = 3)."
)
def total_balance() -> dict:
    conn = get_conn()
    cur = conn.cursor()
    try:
        query = """
        SELECT
            COALESCE(SUM(CASE WHEN type = 1 THEN amount ELSE 0 END), 0) AS total_income,
            COALESCE(SUM(CASE WHEN type = 2 THEN amount ELSE 0 END), 0) AS total_expenses
        FROM transactions
        WHERE type != 3
        """
        cur.execute(query)
        row = cur.fetchone() or [0, 0]
        total_income, total_expenses = float(row[0]), float(row[1])
        cur.close()
        conn.close()

        return {
            "total_income": total_income,
            "total_expenses": total_expenses,
            "balance": total_expenses - total_income
        }
    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass

@tool(
    "daily_balance",
    args_schema=DailyBalanceArgs,
    description="Retorna o saldo do dia informado (YYYY-MM-DD) em America/Sao_Paulo, considerando receitas e despesas e ignorando transferências (type = 3)."
)
def daily_balance(date_local: str) -> dict:
    conn = get_conn()
    cur = conn.cursor()
    try:
        query = """
        SELECT
            COALESCE(SUM(CASE WHEN type = 1 THEN amount ELSE 0 END), 0) AS total_income,
            COALESCE(SUM(CASE WHEN type = 2 THEN amount ELSE 0 END), 0) AS total_expenses
        FROM transactions
        WHERE (occurred_at AT TIME ZONE 'America/Sao_Paulo')::date = %s
        AND type != 3
        """
        cur.execute(query, (date_local,))
        row = cur.fetchone() or [0, 0]
        total_income, total_expenses = float(row[0]), float(row[1])
        cur.close()
        conn.close()

        return {
            "date_local": date_local,
            "total_income": total_income,
            "total_expenses": total_expenses,
            "balance": total_income - total_expenses
        }
    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass

@tool("update_transaction", args_schema=UpdateTransactionArgs)
def update_transaction(
    id: Optional[int] = None,
    match_text: Optional[str] = None,
    date_local: Optional[str] = None,
    amount: Optional[float] = None,
    type_id: Optional[int] = None,
    type_name: Optional[str] = None,
    category_id: Optional[int] = None,
    category_name: Optional[str] = None,
    description: Optional[str] = None,
    payment_method: Optional[str] = None,
    occurred_at: Optional[str] = None,
) -> dict:
    """
    Atualiza uma transaÃ§Ã£o existente.
    EstratÃ©gias:
      - Se 'id' for informado: atualiza diretamente por ID.
      - Caso contrÃ¡rio: localiza a transaÃ§Ã£o mais recente que combine (match_text em source_text/description)
        E (date_local em America/Sao_Paulo), entÃ£o atualiza.
    Retorna: status, rows_affected, id, e o registro atualizado.
    """
    if not any([amount, type_id, type_name, category_id, category_name, description, payment_method, occurred_at]):
        return {"status": "error", "message": "Nada para atualizar: forneÃ§a pelo menos um campo (amount, type, category, description, payment_method, occurred_at)."}

    conn = get_conn()
    cur = conn.cursor()
    try:
        # Resolve target_id
        target_id = id
        if target_id is None:
            if not match_text or not date_local:
                return {"status": "error", "message": "Sem 'id': informe match_text E date_local para localizar o registro."}

            # Buscar o mais recente no dia local informado que combine o texto
            cur.execute(
                f"""
                SELECT
                    t.id
                FROM transactions t
                WHERE (t.source_text ILIKE %s OR t.description ILIKE %s)
                AND 
                    (t.occurred_at AT TIME ZONE 'America/Sao_Paulo')::date = %s
                ORDER BY t.occurred_at DESC
                LIMIT 1;
                """,
                (f"%{match_text}%", f"%{match_text}%", date_local)
            )
            row = cur.fetchone()
            if not row:
                return {"status": "error", "message": "Nenhuma transaÃ§Ã£o encontrada para os filtros fornecidos."}
            target_id = row[0]

        # Resolver type_id / category_id a partir de nomes, se fornecidos
        resolved_type_id = _resolve_type_id(cur, type_id, type_name) if (type_id or type_name) else None
        resolved_category_id = category_id
        if category_name and not category_id:
            resolved_category_id = _resolve_category_id(cur, category_name)

        # Montar SET dinÃ¢mico
        sets = []
        params: List[object] = []
        if amount is not None:
            sets.append("amount = %s")
            params.append(amount)
        if resolved_type_id is not None:
            sets.append("type = %s")
            params.append(resolved_type_id)
        if resolved_category_id is not None:
            sets.append("category_id = %s")
            params.append(resolved_category_id)
        if description is not None:
            sets.append("description = %s")
            params.append(description)
        if payment_method is not None:
            sets.append("payment_method = %s")
            params.append(payment_method)
        if occurred_at is not None:
            sets.append("occurred_at = %s::timestamptz")
            params.append(occurred_at)

        if not sets:
            return {"status": "error", "message": "Nenhum campo vÃ¡lido para atualizar."}

        params.append(target_id)

        cur.execute(
            f"UPDATE transactions SET {', '.join(sets)} WHERE id = %s;",
            params
        )
        rows_affected = cur.rowcount
        conn.commit()

        # Retornar o registro atualizado
        cur.execute(
            """
            SELECT
              t.id, t.occurred_at, t.amount, tt.type AS type_name,
              c.name AS category_name, t.description, t.payment_method, t.source_text
            FROM transactions t
            JOIN transaction_types tt ON tt.id = t.type
            LEFT JOIN categories c ON c.id = t.category_id
            WHERE t.id = %s;
            """,
            (target_id,)
        )
        r = cur.fetchone()
        updated = None
        if r:
            updated = {
                "id": r[0],
                "occurred_at": str(r[1]),
                "amount": float(r[2]),
                "type": r[3],
                "category": r[4],
                "description": r[5],
                "payment_method": r[6],
                "source_text": r[7],
            }

        return {
            "status": "ok",
            "rows_affected": rows_affected,
            "id": target_id,
            "updated": updated
        }

    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


TOOLS = [add_transaction, add_workout, add_meal, query_transactions, total_balance, daily_balance]
