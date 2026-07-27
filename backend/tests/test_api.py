def test_health(client):
    response=client.get("/health"); assert response.status_code==200; assert response.json()["status"]=="ok"
def test_auth_and_me(client):
    assert client.get("/api/v1/auth/me").status_code==401
    response=client.post("/api/v1/auth/login",json={"email":"admin@fluentia.local","password":"senha-segura"})
    assert response.status_code==200; assert client.cookies.get("fluentia_session")
    assert client.get("/api/v1/auth/me").json()["email"]=="admin@fluentia.local"
def test_logout(client,auth):
    assert client.post("/api/v1/auth/logout",headers=auth).status_code==200
    assert client.get("/api/v1/auth/me").status_code==401
def test_csrf_error(client,auth):
    response=client.post("/api/v1/languages/activate",json={"code":"en"})
    assert response.status_code==403; assert set(response.json()["error"])=={"code","message","retryable","request_id"}
def test_languages_and_onboarding(client,auth):
    items=client.get("/api/v1/languages").json(); assert {x["code"] for x in items}=={"en","es-ES","fr","ja","zh-CN"}
    assert client.post("/api/v1/languages/activate",json={"code":"en"},headers=auth).status_code==200
    response=client.post("/api/v1/onboarding/complete",json={"language_code":"en","level_estimate":"A1","goals":["Viagem"]},headers=auth)
    assert response.status_code==200; assert client.get("/api/v1/onboarding/status").json()["completed"]
def activate(client,auth):
    client.post("/api/v1/languages/activate",json={"code":"en"},headers=auth)
def test_conversation_mock(client,auth):
    activate(client,auth)
    conversation=client.post("/api/v1/conversations",json={"language_code":"en"},headers=auth).json()
    response=client.post(f"/api/v1/conversations/{conversation['id']}/messages",json={"text":"Hello"},headers=auth)
    assert response.status_code==200; assert response.json()["provider"]=="mock"
def test_speech_mocks(client,auth):
    stt=client.post("/api/v1/speech/transcribe",data={"language_code":"en"},files={"file":("voice.wav",b"audio","audio/wav")},headers=auth)
    assert stt.status_code==200; assert stt.json()["provider"]=="mock"
    tts=client.post("/api/v1/speech/synthesize",json={"text":"Hello","language_code":"en"},headers=auth)
    assert tts.status_code==200; assert tts.headers["content-type"]=="audio/wav"
def test_vocabulary_and_reviews(client,auth):
    activate(client,auth)
    created=client.post("/api/v1/vocabulary",json={"language_code":"en","term":"book","translation_pt":"livro"},headers=auth)
    assert created.status_code==200
    item=created.json(); assert client.patch(f"/api/v1/vocabulary/{item['id']}",json={"notes":"substantivo"},headers=auth).status_code==200
    due=client.get("/api/v1/reviews/due").json(); assert len(due)==1
    answer=client.post(f"/api/v1/reviews/{due[0]['id']}/answer",json={"rating":"good"},headers=auth)
    assert answer.status_code==200; assert answer.json()["interval_days"]==2
    assert client.delete(f"/api/v1/vocabulary/{item['id']}",headers=auth).status_code==200
def test_validation_error(client,auth):
    response=client.post("/api/v1/languages/activate",json={},headers=auth)
    assert response.status_code==422; assert response.json()["error"]["message"]=="Dados enviados são inválidos."
def test_http_error_format(client):
    response=client.get("/rota-inexistente")
    assert response.status_code==404
    assert response.json()["error"]["code"]=="http_error"
