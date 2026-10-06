"""Diagnóstico somente leitura e regressões do incidente FR B1 confirmado."""
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
from sqlalchemy import select, event
from app.models import User, Language, UserLanguage, Lesson, ContentSource, ContentUnit, LessonContentUsage, AiResponseCache

TITLE = "Logical Structure for Opinion & Justification in French"
EXPLANATION = "Logic: In French, assim como em português com 'porque... então...', we create a chain: opinion → reason → result. Connectors have fixed roles..."

def incident_payload():
    return {"title":TITLE, "objective":"Opinião e justificativa — estruturas-chave",
            "explanation":EXPLANATION, "examples":[], "exercises":[],
            "language_code":"fr", "native_language":"pt-BR", "level":"B1"}

def test_dry_run_links_library_lesson_and_cache_without_personal_data(db_session):
    from scripts.diagnose_fr_b1_content import diagnose
    user = db_session.scalar(select(User))
    language = db_session.scalar(select(Language).where(Language.code == "fr"))
    owner = UserLanguage(user_id=user.id, language_id=language.id, current_level="B1")
    source = ContentSource(title="Fonte de teste", language_id=language.id, source_type="book")
    db_session.add_all([owner,source]); db_session.flush()
    unit = ContentUnit(source_id=source.id, language_id=language.id, cefr_level="B1", skill="vocabulary_grammar", mode="grammar", title=TITLE, payload_json=incident_payload())
    lesson = Lesson(user_language_id=owner.id,title=TITLE,objective="Teste",content_json={**incident_payload(),"provider":"curated_library"})
    cache = AiResponseCache(cache_key="incident-test", capability="grammar", language_code="fr", level="B1", response_json=incident_payload(), hit_count=7)
    db_session.add_all([unit,lesson,cache]); db_session.flush()
    db_session.add(LessonContentUsage(lesson_id=lesson.id,content_unit_id=unit.id)); db_session.commit()
    statements = []
    def capture(conn,cursor,statement,parameters,context,executemany):
        statements.append(statement)
    conn = db_session.connection()
    event.listen(conn, "before_cursor_execute", capture)
    try:
        report = diagnose(conn)
    finally:
        event.remove(conn,"before_cursor_execute",capture)
    assert report["counts"] == {"content_units":1,"lessons":1,"ai_response_cache":1}
    assert report["matched_users_count"] == 1
    records = {row["record_type"]:row for row in report["records"]}
    assert records["lessons"]["linked_content_unit_ids"] == [unit.id]
    assert records["content_units"]["provenance"]["source_id"] == source.id
    assert records["lessons"]["language_code"] == "fr"
    assert records["lessons"]["cefr_level"] == "B1"
    assert {"title","explanation"} <= set(records["lessons"]["contaminated_fields"])
    assert records["lessons"]["user_ref"] != user.id
    assert user.email not in str(report) and user.password_hash not in str(report)
    assert all(statement.lstrip().upper().startswith("SELECT") for statement in statements)
    db_session.refresh(cache)
    assert cache.hit_count == 7

def test_diagnostic_does_not_invent_missing_payload_metadata(db_session):
    from scripts.diagnose_fr_b1_content import describe_payload
    report = describe_payload({"title":TITLE})
    assert report["learner_fields"] == {"title":TITLE}
    assert report["cefr_level"] is None
    assert report["provenance"]["provider"] is None

def test_thread_false_does_not_get_relabelled_as_library_origin():
    from scripts.diagnose_fr_b1_content import describe_payload
    report = describe_payload({"provider":"openrouter", "thread":{
        "guaranteed":False, "sources":["Vocabulário"]}})
    assert report["provenance"]["provider"] == "openrouter"
    assert report["thread_metadata"] == {"guaranteed":False,"sources":["Vocabulário"]}
    assert report["provenance"]["content_origin"] is None

def test_read_only_cli_handles_stored_title_and_leaves_database_unchanged(tmp_path):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.models import Base
    database = tmp_path / "incident.db"
    engine = create_engine(f"sqlite:///{database.as_posix()}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        source = ContentSource(title="Fonte", source_type="book")
        session.add(source); session.flush()
        session.add(ContentUnit(source_id=source.id, cefr_level="B1", skill="vocabulary_grammar",
                                mode="grammar", title=TITLE, payload_json={"title":"Exprimer une opinion"}))
        session.commit()
    engine.dispose()
    before = database.read_bytes()
    result = subprocess.run([sys.executable, "scripts/diagnose_fr_b1_content.py"],
                            cwd=Path(__file__).resolve().parents[1],
                            env={**os.environ,"DATABASE_URL":f"sqlite:///{database.as_posix()}"},
                            capture_output=True, encoding="utf-8", timeout=30)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["read_only"] is True
    assert report["counts"] == {"content_units":1,"lessons":0,"ai_response_cache":0}
    assert report["records"][0]["contaminated_fields"] == ["stored_title"]
    assert report["records"][0]["learner_fields"]["title"] == "Exprimer une opinion"
    assert database.read_bytes() == before

def test_fr_b1_known_incident_must_be_rejected_before_generation():
    from app.services.editorial_validation import valid_generated_lesson
    assert not valid_generated_lesson(incident_payload(),"grammar","fr",native_language="pt-BR")

def test_persisted_fr_b1_incident_must_not_be_reused_as_valid():
    from app.services.language_policy import ensure_stored_content_language
    from app.core.errors import APIError
    with pytest.raises(APIError):
        ensure_stored_content_language(incident_payload(),"pt-BR")

def test_valid_pair_fixture_has_french_primary_and_portuguese_support():
    from app.services.editorial_validation import valid_generated_lesson
    # Fixture de teste, não substitui conteúdo editorial cuja origem é desconhecida.
    payload = {"title":"Exprimer une opinion", "explanation":"On donne son avis, puis on explique pourquoi.",
               "explanation_native":"Dê sua opinião e explique o motivo.", "examples":[],"exercises":[],"level":"B1"}
    assert valid_generated_lesson(payload,"grammar","fr",native_language="pt-BR")
    assert TITLE not in str(payload) and "Logic: In French" not in str(payload)
