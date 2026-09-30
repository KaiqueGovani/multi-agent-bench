-- Esquema extraído do SQLite real; sem conteúdo das tabelas.
PRAGMA foreign_keys = ON;

BEGIN;

CREATE TABLE metadata(
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE conversations(
    conversation_id TEXT PRIMARY KEY,
    split TEXT NOT NULL,
    is_group INTEGER NOT NULL
);

CREATE TABLE episodes(
    episode_id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations,
    split TEXT NOT NULL,
    category_hint TEXT NOT NULL,
    review_status TEXT NOT NULL,
    message_count INTEGER NOT NULL,
    media_count INTEGER NOT NULL
);

CREATE TABLE cases(
    case_id TEXT PRIMARY KEY,
    episode_id TEXT NOT NULL REFERENCES episodes,
    cut_sequence INTEGER NOT NULL
);

CREATE TABLE messages(
    message_id TEXT PRIMARY KEY,
    episode_id TEXT NOT NULL REFERENCES episodes,
    sequence INTEGER NOT NULL,
    elapsed_seconds INTEGER NOT NULL,
    role TEXT NOT NULL,
    type TEXT NOT NULL,
    body TEXT NOT NULL,
    caption TEXT NOT NULL,
    quoted_text TEXT NOT NULL,
    extra_text TEXT NOT NULL,
    content_class TEXT NOT NULL,
    redaction_count INTEGER NOT NULL,
    UNIQUE(episode_id,sequence)
);

CREATE INDEX message_episode ON messages(episode_id,sequence);

COMMIT;
