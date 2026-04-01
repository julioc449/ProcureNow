"""
SQLite Database Module — Audit History Persistence.

Uses Python's built-in sqlite3. Stores both the high-level audit summary
and the detailed per-requirement results.
"""
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

from . import config
from .schema import AuditReport, ComplianceObject, RequirementList


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize the database schema if it doesn't exist."""
    conn = _get_db()
    try:
        cursor = conn.cursor()
        
        # Audits table (metadata and summary stats)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audits (
                id TEXT PRIMARY KEY,
                rfp_name TEXT NOT NULL,
                overall_percentage REAL NOT NULL,
                complete_count INTEGER NOT NULL,
                partial_count INTEGER NOT NULL,
                incomplete_count INTEGER NOT NULL,
                total_requirements INTEGER NOT NULL,
                critical_omissions TEXT, -- JSON array
                created_at TEXT NOT NULL
            )
        ''')
        
        # Audit results table (per-requirement items)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audit_id TEXT NOT NULL,
                category TEXT NOT NULL,
                requirement TEXT NOT NULL,
                status TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                proposal_evidence TEXT,
                missing_elements TEXT, -- JSON array
                page_reference INTEGER,
                evidence_page INTEGER,
                format_match INTEGER, -- boolean 1/0/null
                percentage_filled REAL NOT NULL,
                risk_level TEXT,
                risk_reasoning TEXT,
                FOREIGN KEY (audit_id) REFERENCES audits (id) ON DELETE CASCADE
            )
        ''')
        
        # Migration: Add risk fields if they don't exist
        cursor.execute("PRAGMA table_info(audit_results)")
        columns = [info['name'] for info in cursor.fetchall()]
        if 'risk_level' not in columns:
            cursor.execute("ALTER TABLE audit_results ADD COLUMN risk_level TEXT")
            cursor.execute("ALTER TABLE audit_results ADD COLUMN risk_reasoning TEXT")
            print("[Database] 🔄 Migrated `audit_results` to include risk fields.")
        
        # Index for faster history lookups by date
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audits_created_at ON audits(created_at DESC)')
        
        # Memoized rubrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memoized_rubrics (
                rfp_hash TEXT PRIMARY KEY,
                rfp_name TEXT NOT NULL,
                requirements_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')

        conn.commit()
        print(f"[Database] ✅ Initialized at {config.DB_PATH}")
    finally:
        conn.close()


def save_memoized_rubric(rfp_hash: str, rfp_name: str, requirements: RequirementList) -> None:
    conn = _get_db()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO memoized_rubrics (
                rfp_hash, rfp_name, requirements_json, created_at
            ) VALUES (?, ?, ?, ?)
        ''', (
            rfp_hash,
            rfp_name,
            requirements.model_dump_json(),
            datetime.utcnow().isoformat() + "Z"
        ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"[Database] ❌ Failed to save memoized rubric: {e}")
    finally:
        conn.close()


def get_memoized_rubric(rfp_hash: str) -> Optional[RequirementList]:
    conn = _get_db()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT requirements_json FROM memoized_rubrics WHERE rfp_hash = ?', (rfp_hash,))
        row = cursor.fetchone()
        if not row:
            return None
        return RequirementList.model_validate_json(row['requirements_json'])
    except Exception as e:
        print(f"[Database] ❌ Failed to get memoized rubric: {e}")
        return None
    finally:
        conn.close()


def save_audit(report: AuditReport) -> None:
    """Save an entire AuditReport to the database."""
    conn = _get_db()
    try:
        cursor = conn.cursor()
        
        # Insert main audit record
        cursor.execute('''
            INSERT OR REPLACE INTO audits (
                id, rfp_name, overall_percentage, complete_count, 
                partial_count, incomplete_count, total_requirements, 
                critical_omissions, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            report.proposal_id,
            report.rfp_name,
            report.overall_percentage,
            report.complete_count,
            report.partial_count,
            report.incomplete_count,
            report.total_requirements,
            json.dumps(report.critical_omissions),
            datetime.utcnow().isoformat() + "Z"
        ))
        
        # Delete existing results if overwriting (e.g. same proposal_id somehow)
        cursor.execute('DELETE FROM audit_results WHERE audit_id = ?', (report.proposal_id,))
        
        # Insert all results
        for res in report.audit_results:
            cursor.execute('''
                INSERT INTO audit_results (
                    audit_id, category, requirement, status, confidence_score,
                    proposal_evidence, missing_elements, page_reference,
                    evidence_page, format_match, percentage_filled,
                    risk_level, risk_reasoning
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                report.proposal_id,
                res.category,
                res.requirement,
                res.status,
                res.confidence_score,
                res.proposal_evidence,
                json.dumps(res.missing_elements),
                res.page_reference,
                res.evidence_page,
                res.format_match if res.format_match is not None else None,
                res.percentage_filled,
                res.risk_level,
                res.risk_reasoning
            ))
            
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"[Database] ❌ Failed to save audit: {e}")
        raise
    finally:
        conn.close()


def list_audits(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """Retrieve a list of audits (summary data only)."""
    conn = _get_db()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM audits 
            ORDER BY created_at DESC 
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        
        audits = []
        for row in cursor.fetchall():
            d = dict(row)
            d['critical_omissions'] = json.loads(d['critical_omissions'])
            audits.append(d)
        return audits
    finally:
        conn.close()


def get_audit(audit_id: str) -> Optional[AuditReport]:
    """Retrieve a full AuditReport by ID, including all results."""
    conn = _get_db()
    try:
        cursor = conn.cursor()
        
        # Get main record
        cursor.execute('SELECT * FROM audits WHERE id = ?', (audit_id,))
        audit_row = cursor.fetchone()
        
        if not audit_row:
            return None
            
        audit_data = dict(audit_row)
        critical_omissions = json.loads(audit_data['critical_omissions'])
        
        # Get results
        cursor.execute('SELECT * FROM audit_results WHERE audit_id = ?', (audit_id,))
        results = []
        for res_row in cursor.fetchall():
            res_data = dict(res_row)
            
            # Reconstruct ComplianceObject
            format_match_val = None
            if res_data['format_match'] is not None:
                format_match_val = bool(res_data['format_match'])
                
            results.append(ComplianceObject(
                category=res_data['category'],
                requirement=res_data['requirement'],
                status=res_data['status'],
                confidence_score=res_data['confidence_score'],
                proposal_evidence=res_data['proposal_evidence'],
                missing_elements=json.loads(res_data['missing_elements']),
                page_reference=res_data['page_reference'],
                evidence_page=res_data['evidence_page'],
                format_match=format_match_val,
                percentage_filled=res_data['percentage_filled'],
                risk_level=res_data.get('risk_level'),
                risk_reasoning=res_data.get('risk_reasoning')
            ))
            
        return AuditReport(
            proposal_id=audit_data['id'],
            rfp_name=audit_data['rfp_name'],
            audit_results=results,
            critical_omissions=critical_omissions
        )
    finally:
        conn.close()


def delete_audit(audit_id: str) -> bool:
    """Delete an audit and its results (via CASCADE or explicit delete). Returns True if deleted."""
    conn = _get_db()
    try:
        cursor = conn.cursor()
        # Explicit delete to be safe if PRAGMA foreign_keys is off
        cursor.execute('DELETE FROM audit_results WHERE audit_id = ?', (audit_id,))
        cursor.execute('DELETE FROM audits WHERE id = ?', (audit_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        return deleted
    finally:
        conn.close()
