CREATE TABLE IF NOT EXISTS categories (
  id           SERIAL PRIMARY KEY,
  name         VARCHAR(64) NOT NULL,             
  description  TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()                        
);

CREATE TABLE IF NOT EXISTS transaction_types (
  id      serial PRIMARY KEY,
  type    TEXT NOT NULL                                        
);

CREATE TABLE IF NOT EXISTS transactions (
  id             BIGSERIAL PRIMARY KEY,
  amount         NUMERIC(14,2) NOT NULL , 	
  type           INT REFERENCES transaction_types(id) NOT NULL DEFAULT 2,          
  category_id    INT REFERENCES categories(id) ON DELETE SET NULL,
  description    TEXT,                                                
  payment_method VARCHAR(32),                                         
  occurred_at    TIMESTAMPTZ NOT NULL,                                
  source_text    TEXT NOT NULL                                        
);

-- Índices úteis para consultas comuns
CREATE INDEX IF NOT EXISTS idx_transactions_occurred_at
  ON transactions (occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_transactions_category_time
  ON transactions (category_id, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_transactions_localday
  ON transactions ( ((occurred_at AT TIME ZONE 'America/Sao_Paulo')::date) );

CREATE TABLE IF NOT EXISTS events (
  id           BIGSERIAL PRIMARY KEY,
  title        TEXT NOT NULL,                                          
  start_time   TIMESTAMPTZ NOT NULL,                                   
  end_time     TIMESTAMPTZ,                                            
  location     TEXT,
  notes        TEXT,
  recorded_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),                     
  source_text  TEXT NOT NULL                                           
);

CREATE INDEX IF NOT EXISTS idx_events_start_time
  ON events (start_time DESC);

INSERT INTO transaction_types (type) VALUES
  ('INCOME'),
  ('EXPENSES'),
  ('TRANSFER');

INSERT INTO categories (name) VALUES
  ('comida'),
  ('besteira'),
  ('estudo'),
  ('férias'),
  ('transporte'),
  ('moradia'),
  ('saúde'),
  ('lazer'),
  ('contas'),
  ('investimento'),
  ('presente'),
  ('outros');


-- =======================
-- ACADEMIA
-- =======================

CREATE TABLE IF NOT EXISTS workouts (
  id            BIGSERIAL PRIMARY KEY,
  title         TEXT NOT NULL,                         -- nome do treino (ex: "Treino A - Peito e Tríceps")
  notes         TEXT,                                  -- observações
  scheduled_at  TIMESTAMPTZ NOT NULL,                  -- quando o treino foi/será realizado
  duration_min  INT,                                   -- duração em minutos
  source_text   TEXT NOT NULL,                         -- texto bruto extraído
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Exercícios pertencentes a cada treino
CREATE TABLE IF NOT EXISTS exercises (
  id            BIGSERIAL PRIMARY KEY,
  workout_id    BIGINT REFERENCES workouts(id) ON DELETE CASCADE,
  name          TEXT NOT NULL,                         -- ex: "Supino reto"
  sets          INT,                                   -- número de séries
  reps          INT,                                   -- repetições por série
  weight_kg     NUMERIC(6,2),                          -- carga usada
  notes         TEXT
);

CREATE INDEX IF NOT EXISTS idx_workouts_date
  ON workouts (scheduled_at DESC);


-- =======================
-- ALIMENTAÇÃO
-- =======================

CREATE TABLE IF NOT EXISTS meals (
  id            BIGSERIAL PRIMARY KEY,
  title         TEXT NOT NULL,                         -- ex: "Café da manhã", "Almoço"
  occurred_at   TIMESTAMPTZ NOT NULL,                  -- horário da refeição
  notes         TEXT,
  source_text   TEXT NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Itens dentro de cada refeição
CREATE TABLE IF NOT EXISTS meal_items (
  id            BIGSERIAL PRIMARY KEY,
  meal_id       BIGINT REFERENCES meals(id) ON DELETE CASCADE,
  food_name     TEXT NOT NULL,                         -- nome do alimento (ex: "Arroz integral")
  quantity      NUMERIC(10,2),                         -- quantidade
  unit          VARCHAR(32),                           -- unidade (ex: "g", "ml", "porção")
  calories      NUMERIC(10,2),                         -- kcal (opcional)
  protein_g     NUMERIC(10,2),                         -- proteínas em gramas
  carbs_g       NUMERIC(10,2),                         -- carboidratos em gramas
  fat_g         NUMERIC(10,2)                          -- gorduras em gramas
);

CREATE INDEX IF NOT EXISTS idx_meals_date
  ON meals (occurred_at DESC);
