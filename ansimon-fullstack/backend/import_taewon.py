"""Explicit, repeat-safe import. Source is read-only; never bundle real DBs.
Usage: python import_taewon.py --source PATH --target PATH [--dry-run]
"""
import argparse
import base64
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def payload(row):
    return {k:({'base64':base64.b64encode(v).decode()} if isinstance(v,bytes) else v) for k,v in dict(row).items()}


def import_database(source_path,target_path,dry_run=False):
    source_path=Path(source_path).resolve();target_path=Path(target_path).resolve()
    if source_path==target_path:raise ValueError('원본 DB와 통합 DB 경로는 달라야 합니다.')
    if not source_path.is_file():raise ValueError('원본 DB 파일을 찾을 수 없습니다.')
    with sqlite3.connect(source_path.as_uri()+'?mode=ro',uri=True) as src:
        src.row_factory=sqlite3.Row
        if src.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('원본 DB 무결성 검사 실패')
        names=[r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        if 'records' not in names:raise ValueError('taewon DB 형식이 아닙니다.')
        rows={name:[payload(r) for r in src.execute('SELECT * FROM "'+name.replace('"','""')+'"')] for name in names}
        result={'source_counts':{k:len(v) for k,v in rows.items()},'dry_run':dry_run}
        if dry_run:return result
        # Source snapshot includes any committed WAL content without modifying the source.
        backup=source_path.with_name(source_path.name+'.backup-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
        with sqlite3.connect(backup) as dst:src.backup(dst)
    os.environ['ANSIMON_DB']=str(target_path)
    import main
    main.DB_PATH=target_path
    # Import-time initialization covered the chosen target; repeat calls still snapshot it.
    main.init_db()
    with main.db(write=True) as c:
        for name,records in rows.items():
            for index,r in enumerate(records):
                key=f'taewon:archive:{name}:{r.get("id",index)}'
                raw=json.dumps(r,ensure_ascii=False,sort_keys=True)
                c.execute('INSERT OR IGNORE INTO legacy_archive VALUES(?,?,?)',(key,name,raw))
        for record in rows['records']:
            decoded={**record,'assessment':json.loads(record['assessment'])}
            datetime.fromisoformat(record['date'])
            if record['status'] not in ('수신 거절','안부 확인 완료','통화 중단'):raise ValueError('알 수 없는 이전 통화 상태')
            key='taewon:record:'+record['id'];raw=json.dumps(decoded,ensure_ascii=False,sort_keys=True)
            old=c.execute('SELECT payload_json FROM imported_records WHERE origin_key=?',(key,)).fetchone()
            if old and old[0]!=raw:raise ValueError('같은 ID의 이전 기록이 변경되었습니다. 자동 덮어쓰기를 중단합니다.')
            c.execute('INSERT OR IGNORE INTO imported_records VALUES(?,?,?)',(key,raw,main.now()))
        result['reservations_not_restored']=len(rows.get('schedules',[]))+len(rows.get('queue',[]))
        result['imported_records']=c.execute('SELECT COUNT(*) FROM imported_records').fetchone()[0]
        result['archive_rows']=c.execute('SELECT COUNT(*) FROM legacy_archive').fetchone()[0]
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True);parser.add_argument('--target',required=True);parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    print(json.dumps(import_database(args.source,args.target,args.dry_run),ensure_ascii=False))
