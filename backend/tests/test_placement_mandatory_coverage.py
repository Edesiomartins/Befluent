"""Coverage v3 release contract; historical placements keep their own policy."""
import pytest
from collections import Counter
from sqlalchemy import select

from app.models import PlacementItem, PlacementTest, PlacementTestAnswer
from app.services import placement_engine as engine
from app.services.placement_delivery import deliver_item


def new_test(client, auth):
    response = client.post('/api/v1/placement-tests', headers=auth, json={'language_code': 'en'})
    assert response.status_code == 200
    return response.json()['id']


def answer_item(client, auth, db, test_id, item, correct=True):
    deliver_item(db, db.get(PlacementTest, test_id), item)
    db.commit()
    response = client.post(f'/api/v1/placement-tests/{test_id}/answers', headers=auth,
        json={'item_id': item.id, 'answer': item.correct_answer_json['value'] if correct else '__wrong__'})
    assert response.status_code == 200


def mock_production(monkeypatch):
    from app.api import placement_tests as api
    def evaluation(*args, **kwargs):
        return {'status': 'assessed', 'evaluated_by': 'ai', 'estimated_level': 'A2',
            'reported_level': 'A2', 'accepted_level': 'A2', 'level_origin': 'model_reported',
            'normalized_score': .8, 'criteria': {}, 'provenance': {'provider': 'controlled-test'},
            'limitations': ['single_sample', 'pronunciation_not_measured', 'fluency_not_measured']}
    monkeypatch.setattr(api, 'evaluate_writing', evaluation)
    monkeypatch.setattr(api, 'evaluate_speaking', evaluation)
    monkeypatch.setattr(api, 'transcribe_audio', lambda *args: {'text': 'A spontaneous answer about my experience.', 'provider': 'controlled-stt'})


def run_flow(client, auth, db, test_id, *, skip=None, skip_reason="user_skipped", correct=True):
    collected = Counter()
    payloads = []
    for _ in range(32):
        response = client.post(f'/api/v1/placement-tests/{test_id}/next-item', headers=auth)
        assert response.status_code == 200, response.text
        payload = response.json()
        payloads.append(payload)
        if payload['stage'] == 'ready_to_complete':
            return collected, payloads
        item = db.get(PlacementItem, payload['item']['id'])
        if item.skill in engine.OBJECTIVE_SKILLS:
            result = client.post(f'/api/v1/placement-tests/{test_id}/answers', headers=auth,
                json={'item_id': item.id, 'answer': item.correct_answer_json['value'] if correct else '__wrong__'})
        elif item.skill == skip:
            result = client.post(f'/api/v1/placement-tests/{test_id}/skip-production', headers=auth,
                json={'item_id': item.id, 'text': 'skip', 'reason': skip_reason})
        elif item.skill == 'writing':
            result = client.post(f'/api/v1/placement-tests/{test_id}/writing', headers=auth,
                json={'item_id': item.id, 'text': 'I would like to explain an important experience and what I learned from it.'})
        else:
            assert 'descreva' in item.prompt.lower()
            assert 'espontânea' in item.instructions.lower()
            result = client.post(f'/api/v1/placement-tests/{test_id}/speaking', headers=auth,
                data={'item_id': item.id}, files={'file': ('test.webm', b'controlled-audio', 'audio/webm')})
        assert result.status_code == 200, result.text
        if item.skill != skip:
            collected[item.skill] += 1
    pytest.fail('Selector did not terminate within the budget')


def test_new_session_has_versioned_16_plus_4_contract(client, auth, db_session):
    test_id = new_test(client, auth)
    result = client.get(f'/api/v1/placement-tests/{test_id}', headers=auth).json()
    coverage = result['progress']['assessment_coverage']
    assert coverage['minimum_total'] == 16
    assert coverage['maximum_total'] == 20
    assert not coverage['mandatory_complete']
    assert coverage['skills']['vocabulary_grammar']['required'] == 6
    assert db_session.get(PlacementTest, test_id).result_json['coverage_policy_version'] == 'placement-coverage-v3'


def test_complete_cannot_bypass_available_mandatory_evidence(client, auth, db_session):
    test_id = new_test(client, auth)
    item = db_session.scalar(select(PlacementItem).where(PlacementItem.language_code == 'en', PlacementItem.skill == 'reading'))
    answer_item(client, auth, db_session, test_id, item)
    result = client.post(f'/api/v1/placement-tests/{test_id}/complete', headers=auth)
    assert result.status_code == 409
    assert result.json()['error']['code'] == 'placement_coverage_incomplete'
    assert db_session.get(PlacementTest, test_id).status != 'completed'


@pytest.mark.parametrize('skill', ['reading', 'listening'])
def test_confirmation_waits_for_other_mandatory_skills(client, auth, db_session, skill):
    test_id = new_test(client, auth)
    for band in ('A1', 'A2', 'B1', 'B2'):
        item = db_session.scalar(select(PlacementItem).where(PlacementItem.language_code == 'en',
            PlacementItem.skill == skill, PlacementItem.cefr_level == band,
            ~PlacementItem.external_key.contains('confirmation')))
        answer_item(client, auth, db_session, test_id, item)
    selected = client.post(f'/api/v1/placement-tests/{test_id}/next-item', headers=auth).json()
    assert selected['item']['skill'] != skill
    assert selected['progress']['selection']['phase'] == 'mandatory_coverage'


def test_normal_flow_covers_five_skills_before_extra_and_never_exceeds_20(client, auth, db_session, monkeypatch):
    mock_production(monkeypatch)
    test_id = new_test(client, auth)
    counts, payloads = run_flow(client, auth, db_session, test_id)
    assert counts['vocabulary_grammar'] >= 6
    assert counts['reading'] >= 4
    assert counts['listening'] >= 4
    assert counts['writing'] == counts['speaking'] == 1
    assert 16 <= sum(counts.values()) <= 20
    for payload in payloads:
        coverage = payload['progress']['assessment_coverage']
        if not coverage['mandatory_complete'] and payload['item']:
            skill = payload['item']['skill']
            assert not coverage['skills'][skill]['satisfied']
    result = client.post(f'/api/v1/placement-tests/{test_id}/complete', headers=auth)
    assert result.status_code == 200
    body = result.json()
    assert body['assessment_coverage']['mandatory_complete']
    assert body['assessment_coverage']['completed_total'] == sum(counts.values())
    assert body['assessment_status'] == 'complete'
    assert client.post(f'/api/v1/placement-tests/{test_id}/complete', headers=auth).json() == body
    assert client.get(f'/api/v1/placement-tests/{test_id}/result', headers=auth).json() == body


def test_confirmation_exposes_total_and_remaining_without_reinterpreting_needed():
    policy = engine.confirmation_policy([engine.AnswerRecord('reading', 'A1', 1)])
    assert policy['confirmation_count'] == 1
    assert policy['confirmation_needed'] == policy['confirmation_required_total'] == 2
    assert policy['confirmation_remaining'] == 1


def authored_item(db, skill, band, index):
    item = PlacementItem(language_code='en', skill=skill, cefr_level=band,
        item_type='multiple_choice' if skill == 'vocabulary_grammar' else f'{skill}_comprehension',
        prompt=f'Independent coverage fixture {skill} {band} {index}',
        external_key=f'coverage-fixture-{skill}-{band}-{index}',
        passage=f'Message {skill} {band} {index}' if skill == 'reading' else None,
        audio_script=f'Audio {skill} {band} {index}' if skill == 'listening' else None,
        options_json=['correct', 'wrong'], correct_answer_json={'value': 'correct'},
        rubric_json={'native_language': 'pt-BR'}, review_status='approved', is_active=True)
    db.add(item)
    db.commit()
    return item


def filled_coverage(client, auth, db, test_id, *, candidate_skills=(), include_speaking=True):
    for skill, amount in [('vocabulary_grammar', 6), ('reading', 4), ('listening', 4)]:
        bands = ['A1', 'A2', 'B1', 'B2'] if skill in candidate_skills else ['A1'] * amount
        for index, band in enumerate(bands):
            answer_item(client, auth, db, test_id, authored_item(db, skill, band, index))
    for skill in ('writing', 'speaking'):
        if skill == 'speaking' and not include_speaking:
            continue
        item = db.scalar(select(PlacementItem).where(PlacementItem.language_code == 'en',
            PlacementItem.skill == skill, PlacementItem.cefr_level == 'B1'))
        deliver_item(db, db.get(PlacementTest, test_id), item)
        db.commit()
        if skill == 'writing':
            result = client.post(f'/api/v1/placement-tests/{test_id}/writing', headers=auth,
                json={'item_id': item.id, 'text': 'I am explaining an experience and what it taught me about learning.'})
        else:
            result = client.post(f'/api/v1/placement-tests/{test_id}/speaking', headers=auth,
                data={'item_id': item.id}, files={'file': ('test.webm', b'audio', 'audio/webm')})
        assert result.status_code == 200


@pytest.mark.parametrize('candidate_skills, expected', [((), 16), (('reading',), 17), (('reading', 'listening'), 18)])
def test_resolved_evidence_stops_at_16_17_or_18(client, auth, db_session, monkeypatch, candidate_skills, expected):
    mock_production(monkeypatch)
    test_id = new_test(client, auth)
    filled_coverage(client, auth, db_session, test_id, candidate_skills=candidate_skills)
    extra, payloads = run_flow(client, auth, db_session, test_id)
    assert 16 + sum(extra.values()) == expected
    assert all(p['progress']['assessment_coverage']['mandatory_complete'] for p in payloads)
    assert all(p['progress']['selection']['phase'] == 'adaptive_confirmation' for p in payloads if p['item'])
    result = client.post(f'/api/v1/placement-tests/{test_id}/complete', headers=auth).json()
    assert result['completed_activities_total'] == expected
    assert result['overall_level'] is None  # Production remains provisional.


def test_four_extras_stop_at_20_with_persisted_conflict(client, auth, db_session, monkeypatch):
    mock_production(monkeypatch)
    test_id = new_test(client, auth)
    filled_coverage(client, auth, db_session, test_id, candidate_skills=('reading',))
    for index in range(4, 8):
        authored_item(db_session, 'reading', 'B2', index)
    extra, _ = run_flow(client, auth, db_session, test_id, correct=False)
    assert sum(extra.values()) == 4
    result = client.post(f'/api/v1/placement-tests/{test_id}/complete', headers=auth).json()
    assert result['completed_activities_total'] == 20
    assert result['assessment_coverage']['stop_reason'] == 'maximum_reached'
    assert result['assessment_coverage']['confirmation_deficits']['reading']['confirmation_required']
    reading = next(s for s in result['skills'] if s['skill'] == 'reading')
    assert reading['candidate_level'] == 'B2'
    assert reading['estimated_level'] is None


@pytest.mark.parametrize('skill, reason', [('writing', 'user_skipped'), ('speaking', 'user_skipped'),
    ('speaking', 'microphone_unavailable'), ('speaking', 'production_unavailable'), ('speaking', 'hard_technical_failure')])
def test_explicit_production_skip_is_not_completed_or_cognitive_evidence(client, auth, db_session, monkeypatch, skill, reason):
    mock_production(monkeypatch)
    test_id = new_test(client, auth)
    _, _ = run_flow(client, auth, db_session, test_id, skip=skill, skip_reason=reason)
    result = client.post(f'/api/v1/placement-tests/{test_id}/complete', headers=auth)
    assert result.status_code == 200
    body = result.json()
    coverage = body['assessment_coverage']
    assert not coverage['mandatory_complete']
    assert coverage['mandatory_resolved']
    assert coverage['skills'][skill]['completed'] == 0
    assert coverage['skills'][skill]['skipped'] == 1
    assert coverage['skills'][skill]['reason'] == reason
    assert not body[f'{skill}_submitted']
    assert body['assessment_status'] == 'incomplete'
    assert body['planning_level_trace']['assessment_status'] == 'incomplete'
    data = next(s for s in body['skills'] if s['skill'] == skill)
    assert data['estimated_level'] is None and data['score'] is None
    assert client.get(f'/api/v1/placement-tests/{test_id}/result', headers=auth).json() == body


def test_empty_vg_bank_does_not_ignore_other_skills_or_loop(client, auth, db_session, monkeypatch):
    mock_production(monkeypatch)
    for item in db_session.scalars(select(PlacementItem).where(PlacementItem.language_code == 'en', PlacementItem.skill == 'vocabulary_grammar')):
        item.is_active = False
    db_session.commit()
    test_id = new_test(client, auth)
    counts, _ = run_flow(client, auth, db_session, test_id)
    assert counts['vocabulary_grammar'] == 0
    assert counts['writing'] == counts['speaking'] == 1
    body = client.post(f'/api/v1/placement-tests/{test_id}/complete', headers=auth).json()
    assert body['assessment_status'] == 'incomplete'
    assert body['assessment_coverage']['skills']['vocabulary_grammar']['reason'] == 'bank_exhausted'
    assert body['assessment_coverage']['skills']['vocabulary_grammar']['deficit'] == 6


def test_reuse_and_clones_do_not_satisfy_quota(db_session):
    from app.api.placement_tests import _mandatory_coverage
    test = PlacementTest(user_id='fixture', language_code='en', result_json={'coverage_policy_version': 'placement-coverage-v3'})
    answers = [PlacementTestAnswer(test_id='fixture', item_id=f'item-{i}', skill='vocabulary_grammar', cefr_level='A1',
        normalized_score=1, feedback_json={'exposure': {'reused': True, 'evidence_eligible': False}}) for i in range(6)]
    coverage = _mandatory_coverage(test, answers)
    assert coverage['objective_answered'] == coverage['completed_total'] == 6
    assert coverage['skills']['vocabulary_grammar']['completed'] == 0
    from app.services.placement_coverage import mandatory_snapshot
    clones = [engine.AnswerRecord('reading', 'A1', 1, evidence_keys=('passage:same',)) for _ in range(4)]
    assert mandatory_snapshot(clones, [], 4)['skills']['reading']['completed'] == 1


def test_open_delivery_is_resumed_without_counting_as_completed(client, auth, db_session):
    test_id = new_test(client, auth)
    first = client.post(f'/api/v1/placement-tests/{test_id}/next-item', headers=auth).json()
    second = client.post(f'/api/v1/placement-tests/{test_id}/next-item', headers=auth).json()
    assert first['item']['id'] == second['item']['id']
    assert second['progress']['completed_activities_total'] == 0
    assert client.post(f'/api/v1/placement-tests/{test_id}/complete', headers=auth).status_code == 409


def test_historical_snapshot_is_neither_backfilled_nor_reclassified(client, auth, db_session):
    test_id = new_test(client, auth)
    test = db_session.get(PlacementTest, test_id)
    test.result_json = {'result_schema_version': 2, 'policy_version': 'placement-coverage-v2',
        'overall_level': None, 'skills': {}, 'assessment_coverage': {'historical': True},
        'planning_level': 'A1', 'planning_level_source': 'historical'}
    test.status = 'completed'
    db_session.commit()
    before = dict(test.result_json)
    result = client.get(f'/api/v1/placement-tests/{test_id}/result', headers=auth).json()
    assert result['assessment_coverage'] == {'historical': True}
    assert 'assessment_status' not in result
    db_session.refresh(test)
    assert test.result_json == before


def test_speaking_zero_cannot_complete_without_explicit_exception(client, auth, db_session, monkeypatch):
    mock_production(monkeypatch)
    test_id = new_test(client, auth)
    filled_coverage(client, auth, db_session, test_id, include_speaking=False)
    response = client.post(f'/api/v1/placement-tests/{test_id}/complete', headers=auth)
    assert response.status_code == 409
    next_item = client.post(f'/api/v1/placement-tests/{test_id}/next-item', headers=auth).json()
    assert next_item['stage'] == 'speaking'
    assert not next_item['progress']['assessment_coverage']['mandatory_complete']


def test_spontaneous_speaking_absence_is_explicit_and_reading_aloud_is_not_substituted(client, auth, db_session, monkeypatch):
    mock_production(monkeypatch)
    for item in db_session.scalars(select(PlacementItem).where(PlacementItem.language_code == 'en', PlacementItem.skill == 'speaking')):
        item.is_active = False
    db_session.add(PlacementItem(language_code='en', skill='speaking', cefr_level='B1',
        item_type='speaking_prompt', prompt='Leia este texto em voz alta.',
        external_key='coverage-read-aloud', review_status='approved', is_active=True))
    db_session.commit()
    test_id = new_test(client, auth)
    counts, _ = run_flow(client, auth, db_session, test_id)
    assert counts['speaking'] == 0
    result = client.post(f'/api/v1/placement-tests/{test_id}/complete', headers=auth).json()
    assert result['assessment_coverage']['skills']['speaking']['reason'] == 'production_unavailable'
    assert result['assessment_status'] == 'incomplete'


def test_v3_preserves_native_support_boundary(client, auth, db_session):
    from app.models import User
    db_session.scalar(select(User)).native_language = 'en'
    db_session.commit()
    test_id = client.post('/api/v1/placement-tests', headers=auth, json={'language_code': 'fr'}).json()['id']
    response = client.post(f'/api/v1/placement-tests/{test_id}/next-item', headers=auth)
    assert response.status_code == 409
    assert response.json()['error']['code'] == 'native_support_unavailable'
    assert not list(db_session.scalars(select(PlacementTestAnswer).where(PlacementTestAnswer.test_id == test_id)))


def test_v3_retains_prior_planning_and_records_incomplete_provenance(client, auth, db_session, monkeypatch):
    from app.models import Language, User, UserLanguage, Curriculum
    mock_production(monkeypatch)
    user = db_session.scalar(select(User))
    language = db_session.scalar(select(Language).where(Language.code == 'en'))
    profile = UserLanguage(user_id=user.id, language_id=language.id, is_active=True,
        planning_level='B2', planning_level_source='prior_global', current_level='B2',
        assessment_summary_json={'global_estimate_status': 'sufficient'})
    db_session.add(profile)
    db_session.commit()
    test_id = new_test(client, auth)
    run_flow(client, auth, db_session, test_id, skip='speaking')
    result = client.post(f'/api/v1/placement-tests/{test_id}/complete', headers=auth).json()
    assert result['planning_level'] == 'B2'
    assert result['planning_level_trace']['assessment_status'] == 'incomplete'
    assert result['planning_level_trace']['action'] == 'retained_prior_planning'
    assert result['overall_level'] is None
    db_session.refresh(profile)
    assert profile.current_level == 'B2'
    assert profile.planning_level == 'B2'
    assert client.get('/api/v1/curriculum/active?language_code=en', headers=auth).status_code == 200
