def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_register_success(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Maria Silva",
            "email": "Maria@BeFluent.Local",
            "password": "senha-forte-1",
            "password_confirmation": "senha-forte-1",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["message"] == "Conta criada com sucesso."
    assert body["user"]["email"] == "maria@befluent.local"
    assert body["user"]["name"] == "Maria Silva"
    assert "password" not in body
    assert "password" not in body["user"]
    assert "password_hash" not in body["user"]
    # Sem login automático
    assert client.cookies.get("befluent_session") is None
    assert client.get("/api/v1/auth/me").status_code == 401


def test_register_creates_user_preference(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "João",
            "email": "joao@befluent.local",
            "password": "senha-forte-1",
            "password_confirmation": "senha-forte-1",
        },
    )
    assert response.status_code == 201
    # Preferência criada: login + settings devem funcionar
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "joao@befluent.local", "password": "senha-forte-1"},
    )
    assert login.status_code == 200
    headers = {"X-CSRF-Token": client.cookies.get("csrf_token")}
    settings = client.get("/api/v1/settings", headers=headers)
    assert settings.status_code == 200
    body = settings.json()
    assert "password" not in body
    assert "password_hash" not in body


def test_register_duplicate_email(client):
    payload = {
        "name": "Maria",
        "email": "dup@befluent.local",
        "password": "senha-forte-1",
        "password_confirmation": "senha-forte-1",
    }
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    again = client.post("/api/v1/auth/register", json=payload)
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "email_taken"


def test_register_password_mismatch(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Ana",
            "email": "ana@befluent.local",
            "password": "senha-forte-1",
            "password_confirmation": "outra-senha-1",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_register_short_password(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Ana",
            "email": "ana2@befluent.local",
            "password": "curta",
            "password_confirmation": "curta",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_register_rejects_admin_fields(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Hack",
            "email": "hack@befluent.local",
            "password": "senha-forte-1",
            "password_confirmation": "senha-forte-1",
            "is_admin": True,
            "role": "admin",
        },
    )
    assert response.status_code == 422


def test_auth_and_me(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@befluent.local", "password": "senha-segura"},
    )
    assert response.status_code == 200
    assert client.cookies.get("befluent_session")
    assert client.get("/api/v1/auth/me").json()["email"] == "admin@befluent.local"


def test_logout(client, auth):
    assert client.post("/api/v1/auth/logout", headers=auth).status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401


def test_csrf_error(client, auth):
    response = client.post("/api/v1/languages/activate", json={"code": "en"})
    assert response.status_code == 403
    assert set(response.json()["error"]) == {"code", "message", "retryable", "request_id"}


def test_languages_and_onboarding(client, auth):
    items = client.get("/api/v1/languages").json()
    assert {x["code"] for x in items} == {"en", "es-ES", "fr", "ja", "zh-CN"}
    assert client.post("/api/v1/languages/activate", json={"code": "en"}, headers=auth).status_code == 200
    response = client.post(
        "/api/v1/onboarding/complete",
        json={
            "language_code": "en",
            "perceived_level": "iniciante",
            "goal": "Viagem",
            "minutes_per_day": 20,
            "skills": ["Conversação"],
        },
        headers=auth,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["completed"] is True
    assert body["language_code"] == "en"
    assert body["perceived_level"] == "iniciante"
    assert body["goal"] == "Viagem"
    assert body["minutes_per_day"] == 20
    assert body["skills"] == ["Conversação"]
    assert client.get("/api/v1/onboarding/status").json()["completed"]


def test_onboarding_legacy_payload_still_works(client, auth):
    response = client.post(
        "/api/v1/onboarding/complete",
        json={"language_code": "en", "level_estimate": "A1", "goals": ["Viagem"]},
        headers=auth,
    )
    assert response.status_code == 200
    assert response.json()["perceived_level"] == "A1"
    assert response.json()["goal"] == "Viagem"


def test_dashboard_shows_onboarding_data(client, auth):
    empty = client.get("/api/v1/dashboard", headers=auth)
    assert empty.status_code == 200
    assert empty.json()["onboarding_completed"] is False
    assert empty.json()["active_language"] is None
    assert empty.json()["next_activity"]["kind"] == "onboarding"

    complete = client.post(
        "/api/v1/onboarding/complete",
        json={
            "language_code": "fr",
            "perceived_level": "basico",
            "goal": "Trabalho e carreira",
            "minutes_per_day": 30,
            "skills": ["Vocabulário", "Gramática"],
        },
        headers=auth,
    )
    assert complete.status_code == 200

    dashboard = client.get("/api/v1/dashboard", headers=auth)
    assert dashboard.status_code == 200
    payload = dashboard.json()
    assert payload["onboarding_completed"] is True
    lang = payload["active_language"]
    assert lang["code"] == "fr"
    assert lang["name_pt"]
    assert lang["level_estimate"] == "basico"
    assert lang["goal"] == "Trabalho e carreira"
    assert lang["minutes_per_day"] == 30
    assert lang["skills"] == ["Vocabulário", "Gramática"]
    assert lang["onboarding_completed"] is True
    assert payload["reviews_due_count"] == 0
    assert payload["recent_activity"] == []
    assert payload["next_activity"]["href"] == "/learn/vocabulary"
    assert payload["day_plan"]["minutes_per_day"] == 30
    assert payload["progress"]["vocabulary_items"] == 0
    assert payload["progress"]["study_sessions"] == 0


def test_onboarding_persists_after_new_session(client):
    register = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Persistência",
            "email": "persist@befluent.local",
            "password": "senha-forte-1",
            "password_confirmation": "senha-forte-1",
        },
    )
    assert register.status_code == 201

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "persist@befluent.local", "password": "senha-forte-1"},
    )
    assert login.status_code == 200
    headers = {"X-CSRF-Token": client.cookies.get("csrf_token")}

    complete = client.post(
        "/api/v1/onboarding/complete",
        json={
            "language_code": "ja",
            "perceived_level": "intermediario",
            "goal": "Consumir cultura",
            "minutes_per_day": 45,
            "skills": ["Leitura"],
        },
        headers=headers,
    )
    assert complete.status_code == 200

    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/v1/dashboard").status_code == 401

    again = client.post(
        "/api/v1/auth/login",
        json={"email": "persist@befluent.local", "password": "senha-forte-1"},
    )
    assert again.status_code == 200
    headers = {"X-CSRF-Token": client.cookies.get("csrf_token")}
    dashboard = client.get("/api/v1/dashboard", headers=headers)
    assert dashboard.status_code == 200
    lang = dashboard.json()["active_language"]
    assert lang["code"] == "ja"
    assert lang["level_estimate"] == "intermediario"
    assert lang["goal"] == "Consumir cultura"
    assert lang["minutes_per_day"] == 45
    assert lang["skills"] == ["Leitura"]



def activate(client, auth):
    client.post("/api/v1/languages/activate", json={"code": "en"}, headers=auth)


def test_conversation_mock(client, auth):
    activate(client, auth)
    conversation = client.post("/api/v1/conversations", json={"language_code": "en"}, headers=auth).json()
    response = client.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        json={"text": "Hello"},
        headers=auth,
    )
    assert response.status_code == 200
    assert response.json()["provider"] == "mock"


def test_speech_mocks(client, auth):
    stt = client.post(
        "/api/v1/speech/transcribe",
        data={"language_code": "en"},
        files={"file": ("voice.wav", b"audio", "audio/wav")},
        headers=auth,
    )
    assert stt.status_code == 200
    assert stt.json()["provider"] == "mock"
    tts = client.post(
        "/api/v1/speech/synthesize",
        json={"text": "Hello", "language_code": "en"},
        headers=auth,
    )
    assert tts.status_code == 200
    assert tts.headers["content-type"] == "audio/wav"


def test_vocabulary_and_reviews(client, auth):
    activate(client, auth)
    created = client.post(
        "/api/v1/vocabulary",
        json={"language_code": "en", "term": "book", "translation_pt": "livro"},
        headers=auth,
    )
    assert created.status_code == 200
    item = created.json()
    assert client.patch(f"/api/v1/vocabulary/{item['id']}", json={"notes": "substantivo"}, headers=auth).status_code == 200
    due = client.get("/api/v1/reviews/due").json()
    assert len(due) == 1
    answer = client.post(f"/api/v1/reviews/{due[0]['id']}/answer", json={"rating": "good"}, headers=auth)
    assert answer.status_code == 200
    assert answer.json()["interval_days"] == 2
    assert client.delete(f"/api/v1/vocabulary/{item['id']}", headers=auth).status_code == 200


def test_validation_error(client, auth):
    response = client.post("/api/v1/languages/activate", json={}, headers=auth)
    assert response.status_code == 422
    assert response.json()["error"]["message"] == "Dados enviados são inválidos."


def test_http_error_format(client):
    response = client.get("/rota-inexistente")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "http_error"
