"""Reservation removal after main.init_db has snapshotted the existing database."""

def migrate(c):
    c.execute('SAVEPOINT remove_reservations')
    try:
        c.execute('CREATE TABLE IF NOT EXISTS imported_records (origin_key TEXT PRIMARY KEY, payload_json TEXT NOT NULL, imported_at TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS legacy_archive (origin_key TEXT PRIMARY KEY, table_name TEXT NOT NULL, payload_json TEXT NOT NULL)')
        columns={r['name'] for r in c.execute('PRAGMA table_info(calls)')}
        for name in ('recipient','scheduled_at'):
            if name not in columns:c.execute(f'ALTER TABLE calls ADD COLUMN {name} TEXT')
        tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'scheduled_calls' in tables:
            # Preserve the actual alias/time used for a past call, not the current schedule settings.
            c.execute('''UPDATE calls SET
                recipient=COALESCE(recipient,(SELECT recipient FROM scheduled_calls WHERE call_id=calls.id)),
                scheduled_at=COALESCE(scheduled_at,(SELECT scheduled_at FROM scheduled_calls WHERE call_id=calls.id))
                WHERE EXISTS(SELECT 1 FROM scheduled_calls WHERE call_id=calls.id)''')
            c.execute('DROP TABLE scheduled_calls')
        c.execute('DROP TABLE IF EXISTS care_schedules')
        c.execute('CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)')
        c.execute("INSERT OR IGNORE INTO schema_migrations(name) VALUES('remove_reservations_v1')")
        c.execute('RELEASE remove_reservations')
    except Exception:
        c.execute('ROLLBACK TO remove_reservations')
        c.execute('RELEASE remove_reservations')
        raise
