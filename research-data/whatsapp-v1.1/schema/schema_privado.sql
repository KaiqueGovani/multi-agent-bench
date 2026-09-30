-- Esquema extraído do SQLite real; sem conteúdo das tabelas.
PRAGMA foreign_keys = ON;

BEGIN;

CREATE TABLE metadata(
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE sources(
    source_id TEXT PRIMARY KEY,
    filename TEXT,
    sha256 TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    profile_json TEXT NOT NULL
);

CREATE TABLE chats_original(
    chat_uid TEXT PRIMARY KEY,
    whatsapp_id TEXT UNIQUE NOT NULL,
    group_uid TEXT NOT NULL,
    is_group INTEGER NOT NULL,
    raw_json TEXT NOT NULL
);

CREATE TABLE messages_original(
    message_uid TEXT PRIMARY KEY,
    chat_uid TEXT NOT NULL REFERENCES chats_original,
    whatsapp_id TEXT UNIQUE NOT NULL,
    source_id TEXT NOT NULL REFERENCES sources,
    timestamp_unix INTEGER,
    from_me INTEGER NOT NULL,
    type TEXT NOT NULL,
    raw_json TEXT NOT NULL,
    raw_sha256 TEXT NOT NULL
);

CREATE TABLE original_fields(
    message_uid TEXT NOT NULL REFERENCES messages_original,
    field TEXT NOT NULL,
    original_text TEXT NOT NULL,
    PRIMARY KEY(message_uid,field)
);

CREATE TABLE messages_redacted(
    message_uid TEXT PRIMARY KEY REFERENCES messages_original,
    chat_uid TEXT NOT NULL REFERENCES chats_original,
    role TEXT NOT NULL,
    type TEXT NOT NULL,
    body TEXT NOT NULL,
    caption TEXT NOT NULL,
    quoted_text TEXT NOT NULL,
    extra_text TEXT NOT NULL,
    content_class TEXT NOT NULL,
    redaction_count INTEGER NOT NULL,
    residual_flags TEXT NOT NULL,
    review_status TEXT NOT NULL DEFAULT 'pending',
    pipeline_version TEXT NOT NULL
);

CREATE TABLE redaction_spans(
    message_uid TEXT NOT NULL REFERENCES messages_original,
    field TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    start INTEGER NOT NULL,
    end INTEGER NOT NULL,
    redacted_start INTEGER NOT NULL,
    redacted_end INTEGER NOT NULL,
    kind TEXT NOT NULL,
    detector TEXT NOT NULL,
    token TEXT NOT NULL,
    original_value TEXT NOT NULL,
    PRIMARY KEY(message_uid,field,ordinal)
);

CREATE TABLE episodes(
    episode_uid TEXT PRIMARY KEY,
    chat_uid TEXT NOT NULL REFERENCES chats_original,
    group_uid TEXT NOT NULL,
    split TEXT NOT NULL,
    category_hint TEXT NOT NULL,
    review_status TEXT NOT NULL DEFAULT 'pending',
    start_unix INTEGER,
    end_unix INTEGER,
    message_count INTEGER NOT NULL,
    media_count INTEGER NOT NULL,
    is_group INTEGER NOT NULL
);

CREATE TABLE episode_messages(
    episode_uid TEXT NOT NULL REFERENCES episodes,
    message_uid TEXT NOT NULL REFERENCES messages_original,
    sequence INTEGER NOT NULL,
    elapsed_seconds INTEGER NOT NULL,
    PRIMARY KEY(episode_uid,sequence),
    UNIQUE(message_uid)
);

CREATE TABLE media_original(
    media_uid TEXT PRIMARY KEY,
    manifest_json TEXT NOT NULL
);

CREATE TABLE message_media(
    message_uid TEXT NOT NULL REFERENCES messages_original,
    media_uid TEXT NOT NULL REFERENCES media_original,
    PRIMARY KEY(message_uid,media_uid)
);

CREATE TABLE auxiliary_original(
    kind TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    raw_json TEXT NOT NULL,
    PRIMARY KEY(kind,ordinal)
);

CREATE TABLE review_log(
    id INTEGER PRIMARY KEY,
    episode_uid TEXT NOT NULL REFERENCES episodes,
    decision TEXT NOT NULL,
    reviewer TEXT NOT NULL,
    note TEXT NOT NULL,
    reviewed_at TEXT NOT NULL
);

CREATE TABLE evaluation_cases(
    case_uid TEXT PRIMARY KEY,
    episode_uid TEXT NOT NULL REFERENCES episodes,
    cut_sequence INTEGER NOT NULL,
    reference_message_uid TEXT REFERENCES messages_original,
    label_status TEXT NOT NULL DEFAULT 'weak_reference_not_ground_truth'
);

CREATE TABLE experiment_runs(
    run_uid TEXT PRIMARY KEY,
    case_uid TEXT NOT NULL REFERENCES evaluation_cases,
    architecture TEXT NOT NULL CHECK(architecture IN ('orchestrator','workflow','swarm')),
    model TEXT NOT NULL,
    seed INTEGER NOT NULL,
    prompt_version TEXT NOT NULL,
    tools_version TEXT NOT NULL,
    dataset_sha256 TEXT NOT NULL,
    latency_ms REAL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    tool_calls INTEGER,
    handoffs INTEGER,
    resolved INTEGER,
    human_intervention INTEGER,
    cost REAL,
    redacted_output TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE experiment_events(
    run_uid TEXT NOT NULL REFERENCES experiment_runs,
    sequence INTEGER NOT NULL,
    agent_role TEXT NOT NULL,
    event_type TEXT NOT NULL,
    duration_ms REAL,
    payload_redacted_json TEXT,
    PRIMARY KEY(run_uid,sequence)
);

CREATE TABLE case_labels(
    case_uid TEXT PRIMARY KEY REFERENCES evaluation_cases,
    expected_intent TEXT,
    expected_tool TEXT,
    needs_professional INTEGER,
    expected_resolution TEXT,
    reviewer TEXT NOT NULL,
    label_version TEXT NOT NULL
);

CREATE INDEX original_chat_time ON messages_original(chat_uid,timestamp_unix);

CREATE INDEX redaction_token ON redaction_spans(token);

CREATE TRIGGER immutable_sources_update BEFORE UPDATE ON sources BEGIN SELECT RAISE(ABORT,'Original preservado: crie uma nova versao'); END;

CREATE TRIGGER immutable_sources_delete BEFORE DELETE ON sources BEGIN SELECT RAISE(ABORT,'Original preservado: crie uma nova versao'); END;

CREATE TRIGGER immutable_chats_original_update BEFORE UPDATE ON chats_original BEGIN SELECT RAISE(ABORT,'Original preservado: crie uma nova versao'); END;

CREATE TRIGGER immutable_chats_original_delete BEFORE DELETE ON chats_original BEGIN SELECT RAISE(ABORT,'Original preservado: crie uma nova versao'); END;

CREATE TRIGGER immutable_messages_original_update BEFORE UPDATE ON messages_original BEGIN SELECT RAISE(ABORT,'Original preservado: crie uma nova versao'); END;

CREATE TRIGGER immutable_messages_original_delete BEFORE DELETE ON messages_original BEGIN SELECT RAISE(ABORT,'Original preservado: crie uma nova versao'); END;

CREATE TRIGGER immutable_original_fields_update BEFORE UPDATE ON original_fields BEGIN SELECT RAISE(ABORT,'Original preservado: crie uma nova versao'); END;

CREATE TRIGGER immutable_original_fields_delete BEFORE DELETE ON original_fields BEGIN SELECT RAISE(ABORT,'Original preservado: crie uma nova versao'); END;

CREATE TRIGGER immutable_media_original_update BEFORE UPDATE ON media_original BEGIN SELECT RAISE(ABORT,'Original preservado: crie uma nova versao'); END;

CREATE TRIGGER immutable_media_original_delete BEFORE DELETE ON media_original BEGIN SELECT RAISE(ABORT,'Original preservado: crie uma nova versao'); END;

CREATE TRIGGER immutable_auxiliary_original_update BEFORE UPDATE ON auxiliary_original BEGIN SELECT RAISE(ABORT,'Original preservado: crie uma nova versao'); END;

CREATE TRIGGER immutable_auxiliary_original_delete BEFORE DELETE ON auxiliary_original BEGIN SELECT RAISE(ABORT,'Original preservado: crie uma nova versao'); END;

COMMIT;
