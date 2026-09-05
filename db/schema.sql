CREATE TABLE IF NOT EXISTS builds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    commit_hash TEXT NOT NULL,
    branch TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    status TEXT NOT NULL,
    runtime_sec REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS stage_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    build_id INTEGER NOT NULL,
    stage TEXT NOT NULL,
    status TEXT NOT NULL,
    runtime_sec REAL NOT NULL,
    FOREIGN KEY (build_id) REFERENCES builds(id)
);

CREATE TABLE IF NOT EXISTS timing_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    build_id INTEGER NOT NULL,
    setup_wns REAL,
    hold_whs REAL,
    FOREIGN KEY (build_id) REFERENCES builds(id)
);
