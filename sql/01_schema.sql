-- Autores (users da API pública)
CREATE TABLE autor (
    id                INTEGER PRIMARY KEY,
    nome              VARCHAR(150) NOT NULL,
    email             VARCHAR(150) NOT NULL,
    telefone          VARCHAR(50),
    endereco          VARCHAR(300),
    empresa_nome      VARCHAR(150),
    empresa_segmento  VARCHAR(200),
    criado_em         TIMESTAMP NOT NULL DEFAULT now(),
    atualizado_em     TIMESTAMP NOT NULL DEFAULT now()
);

-- Acordos (albums da API pública)
CREATE TABLE acordo (
    id         INTEGER PRIMARY KEY,
    autor_id   INTEGER NOT NULL REFERENCES autor(id),
    titulo     VARCHAR(300) NOT NULL,
    criado_em  TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX ix_acordo_autor_id ON acordo(autor_id);

-- Documentos (photos da API pública)
CREATE TABLE documento (
    id             INTEGER PRIMARY KEY,
    acordo_id      INTEGER NOT NULL REFERENCES acordo(id),
    titulo         VARCHAR(300) NOT NULL,
    url            VARCHAR(500) NOT NULL,
    thumbnail_url  VARCHAR(500) NOT NULL,
    criado_em      TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX ix_documento_acordo_id ON documento(acordo_id);

-- Registro de mensagens que falharam repetidamente
CREATE TABLE carga_erro (
    id              SERIAL PRIMARY KEY,
    correlation_id  VARCHAR(64),
    tipo            VARCHAR(30),
    payload         JSONB,
    erro            TEXT,
    criado_em       TIMESTAMP NOT NULL DEFAULT now()
);
