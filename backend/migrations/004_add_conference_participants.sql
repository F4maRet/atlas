-- Миграция: добавить таблицу участников конференций
-- Выполнить если таблица ещё не существует

CREATE TABLE IF NOT EXISTS conference_participants (
    conference_id INTEGER NOT NULL REFERENCES conferences(id) ON DELETE CASCADE,
    author_id     INTEGER NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
    PRIMARY KEY (conference_id, author_id)
);

CREATE INDEX IF NOT EXISTS idx_conf_participants_conf ON conference_participants(conference_id);
CREATE INDEX IF NOT EXISTS idx_conf_participants_author ON conference_participants(author_id);
