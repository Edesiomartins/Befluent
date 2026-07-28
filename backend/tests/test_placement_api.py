"""Testes de API do teste de nivelamento (fluxo, segurança e persistência)."""

from sqlalchemy import select

from app.core.levels import LEVEL_ORDER
from app.models import PlacementItem, PlacementTest, UserLanguage


def create_test(client, auth, language="en", beginner=False):
    return client.post(
        "/api/v1/placement-tests",
        json={"language_code": language, "declared_beginner": beginner},
        headers=auth,
    )


def answer_all(client, auth, test_id, db_session, correct=True, limit=40):
    """Responde itens objetivos até o teste indicar que pode concluir."""
    answered = 0
    while answered < limit:
        payload = client.post(
            f"/api/v1/placement-tests/{test_id}/next-item", headers=auth
        ).json()
        item = payload.get("item")
        if item is None or payload["stage"] != "objective":
            return payload
        db_item = db_session.get(PlacementItem, item["id"])
        expected = (db_item.correct_answer_json or {}).get("value")
        chosen = expected if correct else "__resposta_errada__"
        client.post(
            f"/api/v1/placement-tests/{test_id}/answers",
            json={"item_id": item["id"], "answer": chosen, "response_time_ms": 6000},
            headers=auth,
        )
        answered += 1
    return {"stage": "limit_reached"}


class TestLevels:
    def test_lista_niveis_cefr(self, client):
        response = client.get("/api/v1/levels")
        assert response.status_code == 200
        body = response.json()
        assert [level["code"] for level in body["levels"]] == LEVEL_ORDER
        assert body["framework"] == "CEFR"

    def test_niveis_tem_nome_e_descricao(self, client):
        levels = client.get("/api/v1/levels").json()["levels"]
        pre_a1 = next(level for level in levels if level["code"] == "PRE_A1")
        assert "Pré-A1" in pre_a1["name_pt"]
        assert pre_a1["short_description"]

    def test_c1_c2_existem_mas_nao_sao_testaveis(self, client):
        body = client.get("/api/v1/levels").json()
        assert "C1" not in body["testable_levels"]
        assert "C2" not in body["testable_levels"]


class TestCreation:
    def test_cria_teste(self, client, auth):
        response = create_test(client, auth)
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "in_progress"
        assert body["language_code"] == "en"

    def test_idioma_inexistente(self, client, auth):
        response = create_test(client, auth, language="xx")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "language_not_found"

    def test_retoma_teste_em_andamento_em_vez_de_duplicar(self, client, auth):
        first = create_test(client, auth).json()
        second = create_test(client, auth).json()
        assert first["id"] == second["id"]

    def test_exige_autenticacao(self, client):
        response = client.post(
            "/api/v1/placement-tests", json={"language_code": "en"}
        )
        assert response.status_code in (401, 403)

    def test_exige_csrf(self, client):
        client.post(
            "/api/v1/auth/login",
            json={"email": "admin@befluent.local", "password": "senha-segura"},
        )
        response = client.post("/api/v1/placement-tests", json={"language_code": "en"})
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "csrf_invalid"


class TestOwnership:
    def test_nao_acessa_teste_de_outro_usuario(self, client, auth, other_user, db_session):
        alheio = PlacementTest(user_id=other_user, language_code="en", status="in_progress")
        db_session.add(alheio)
        db_session.commit()

        response = client.get(f"/api/v1/placement-tests/{alheio.id}", headers=auth)
        assert response.status_code == 404

    def test_nao_responde_teste_de_outro_usuario(self, client, auth, other_user, db_session):
        alheio = PlacementTest(user_id=other_user, language_code="en", status="in_progress")
        db_session.add(alheio)
        db_session.commit()
        item = db_session.scalar(select(PlacementItem).where(PlacementItem.language_code == "en"))

        response = client.post(
            f"/api/v1/placement-tests/{alheio.id}/answers",
            json={"item_id": item.id, "answer": "x"},
            headers=auth,
        )
        assert response.status_code == 404

    def test_teste_inexistente_retorna_404(self, client, auth):
        response = client.get("/api/v1/placement-tests/nao-existe", headers=auth)
        assert response.status_code == 404


class TestItemDelivery:
    def test_next_item_nao_revela_gabarito(self, client, auth):
        test_id = create_test(client, auth).json()["id"]
        item = client.post(
            f"/api/v1/placement-tests/{test_id}/next-item", headers=auth
        ).json()["item"]

        assert "correct_answer" not in item
        assert "correct_answer_json" not in item
        assert "explanation" not in item
        assert "rubric" not in item
        assert "difficulty" not in item

    def test_next_item_traz_opcoes(self, client, auth):
        test_id = create_test(client, auth).json()["id"]
        item = client.post(
            f"/api/v1/placement-tests/{test_id}/next-item", headers=auth
        ).json()["item"]
        assert item["options"]
        assert item["prompt"]

    def test_iniciante_absoluto_comeca_em_pre_a1(self, client, auth, db_session):
        test_id = create_test(client, auth, beginner=True).json()["id"]
        item = client.post(
            f"/api/v1/placement-tests/{test_id}/next-item", headers=auth
        ).json()["item"]
        db_item = db_session.get(PlacementItem, item["id"])
        assert db_item.cefr_level == "PRE_A1"

    def test_resposta_nao_revela_se_acertou(self, client, auth, db_session):
        test_id = create_test(client, auth).json()["id"]
        item = client.post(
            f"/api/v1/placement-tests/{test_id}/next-item", headers=auth
        ).json()["item"]

        body = client.post(
            f"/api/v1/placement-tests/{test_id}/answers",
            json={"item_id": item["id"], "answer": "qualquer"},
            headers=auth,
        ).json()

        assert "is_correct" not in body
        assert "correct_answer" not in body
        assert body["accepted"] is True

    def test_nao_aceita_resposta_duplicada(self, client, auth):
        test_id = create_test(client, auth).json()["id"]
        item = client.post(
            f"/api/v1/placement-tests/{test_id}/next-item", headers=auth
        ).json()["item"]

        client.post(
            f"/api/v1/placement-tests/{test_id}/answers",
            json={"item_id": item["id"], "answer": "a"},
            headers=auth,
        )
        again = client.post(
            f"/api/v1/placement-tests/{test_id}/answers",
            json={"item_id": item["id"], "answer": "a"},
            headers=auth,
        )
        assert again.status_code == 409

    def test_score_nao_vem_do_cliente(self, client, auth):
        """Campos extras são rejeitados: o cliente não influencia a pontuação."""
        test_id = create_test(client, auth).json()["id"]
        item = client.post(
            f"/api/v1/placement-tests/{test_id}/next-item", headers=auth
        ).json()["item"]

        response = client.post(
            f"/api/v1/placement-tests/{test_id}/answers",
            json={"item_id": item["id"], "answer": "a", "normalized_score": 1.0},
            headers=auth,
        )
        assert response.status_code == 422


class TestCompletion:
    def test_nao_conclui_sem_itens_suficientes(self, client, auth):
        test_id = create_test(client, auth).json()["id"]
        response = client.post(f"/api/v1/placement-tests/{test_id}/complete", headers=auth)
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "placement_insufficient_items"

    def test_fluxo_completo_gera_resultado(self, client, auth, db_session):
        test_id = create_test(client, auth).json()["id"]
        answer_all(client, auth, test_id, db_session, correct=True)

        response = client.post(f"/api/v1/placement-tests/{test_id}/complete", headers=auth)
        assert response.status_code == 200
        body = response.json()

        assert body["status"] == "completed"
        assert body["overall_level"] in LEVEL_ORDER
        assert 0 <= body["confidence_score"] <= 100
        assert body["disclaimer"] == "Nível estimado. Não é uma certificação oficial."

    def test_resultado_marca_speaking_como_indisponivel(self, client, auth, db_session):
        test_id = create_test(client, auth).json()["id"]
        answer_all(client, auth, test_id, db_session)
        body = client.post(f"/api/v1/placement-tests/{test_id}/complete", headers=auth).json()

        speaking = next(s for s in body["skills"] if s["skill"] == "speaking")
        assert speaking["status"] == "not_available"
        assert speaking["estimated_level"] is None
        assert body["speaking_available"] is False

    def test_resultado_persiste_no_perfil(self, client, auth, db_session):
        test_id = create_test(client, auth).json()["id"]
        answer_all(client, auth, test_id, db_session)
        body = client.post(f"/api/v1/placement-tests/{test_id}/complete", headers=auth).json()

        profile = db_session.scalar(
            select(UserLanguage).where(UserLanguage.placement_test_id == test_id)
        )
        assert profile is not None
        assert profile.current_level == body["overall_level"]
        assert profile.level_source == "placement_test"
        assert profile.diagnostic_completed is True

    def test_resultado_recuperavel_depois(self, client, auth, db_session):
        test_id = create_test(client, auth).json()["id"]
        answer_all(client, auth, test_id, db_session)
        client.post(f"/api/v1/placement-tests/{test_id}/complete", headers=auth)

        response = client.get(f"/api/v1/placement-tests/{test_id}/result", headers=auth)
        assert response.status_code == 200
        assert response.json()["overall_level"] in LEVEL_ORDER

    def test_resultado_de_teste_incompleto_falha(self, client, auth):
        test_id = create_test(client, auth).json()["id"]
        response = client.get(f"/api/v1/placement-tests/{test_id}/result", headers=auth)
        assert response.status_code == 409

    def test_desempenho_fraco_gera_nivel_baixo(self, client, auth, db_session):
        test_id = create_test(client, auth).json()["id"]
        answer_all(client, auth, test_id, db_session, correct=False)
        body = client.post(f"/api/v1/placement-tests/{test_id}/complete", headers=auth).json()
        assert body["overall_level"] in ("PRE_A1", "A1")

    def test_nao_permite_refazer_imediatamente(self, client, auth, db_session):
        test_id = create_test(client, auth).json()["id"]
        answer_all(client, auth, test_id, db_session)
        client.post(f"/api/v1/placement-tests/{test_id}/complete", headers=auth)

        response = create_test(client, auth)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "placement_retake_too_soon"


class TestResume:
    def test_retoma_teste_abandonado(self, client, auth):
        test_id = create_test(client, auth).json()["id"]
        item = client.post(
            f"/api/v1/placement-tests/{test_id}/next-item", headers=auth
        ).json()["item"]
        client.post(
            f"/api/v1/placement-tests/{test_id}/answers",
            json={"item_id": item["id"], "answer": "a"},
            headers=auth,
        )

        current = client.get("/api/v1/placement-tests/current", headers=auth).json()
        assert current["test"]["id"] == test_id
        assert current["test"]["progress"]["answered"] == 1

    def test_sem_teste_em_andamento(self, client, auth):
        current = client.get("/api/v1/placement-tests/current", headers=auth).json()
        assert current["test"] is None


class TestWriting:
    def test_avalia_escrita(self, client, auth, db_session):
        test_id = create_test(client, auth).json()["id"]
        answer_all(client, auth, test_id, db_session)
        payload = client.post(
            f"/api/v1/placement-tests/{test_id}/next-item", headers=auth
        ).json()

        assert payload["stage"] == "writing"
        response = client.post(
            f"/api/v1/placement-tests/{test_id}/writing",
            json={
                "item_id": payload["item"]["id"],
                "text": "My name is Ana. I am from Brazil. I like reading books and travelling.",
            },
            headers=auth,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "assessed"

    def test_escrita_entra_no_resultado(self, client, auth, db_session):
        test_id = create_test(client, auth).json()["id"]
        answer_all(client, auth, test_id, db_session)
        payload = client.post(
            f"/api/v1/placement-tests/{test_id}/next-item", headers=auth
        ).json()
        client.post(
            f"/api/v1/placement-tests/{test_id}/writing",
            json={
                "item_id": payload["item"]["id"],
                "text": "My name is Ana. I am from Brazil. I like reading and travelling a lot.",
            },
            headers=auth,
        )
        body = client.post(f"/api/v1/placement-tests/{test_id}/complete", headers=auth).json()
        writing = next(s for s in body["skills"] if s["skill"] == "writing")
        assert writing["status"] == "assessed"

    def test_texto_vazio_rejeitado(self, client, auth, db_session):
        test_id = create_test(client, auth).json()["id"]
        item = db_session.scalar(
            select(PlacementItem).where(
                PlacementItem.language_code == "en", PlacementItem.skill == "writing"
            )
        )
        response = client.post(
            f"/api/v1/placement-tests/{test_id}/writing",
            json={"item_id": item.id, "text": ""},
            headers=auth,
        )
        assert response.status_code == 422

    def test_texto_excessivo_rejeitado(self, client, auth, db_session):
        test_id = create_test(client, auth).json()["id"]
        item = db_session.scalar(
            select(PlacementItem).where(
                PlacementItem.language_code == "en", PlacementItem.skill == "writing"
            )
        )
        response = client.post(
            f"/api/v1/placement-tests/{test_id}/writing",
            json={"item_id": item.id, "text": "a" * 5000},
            headers=auth,
        )
        assert response.status_code == 422


class TestSpeaking:
    def test_avaliacao_oral_indisponivel(self, client, auth):
        test_id = create_test(client, auth).json()["id"]
        response = client.post(f"/api/v1/placement-tests/{test_id}/speaking", headers=auth)
        assert response.status_code == 501
        assert response.json()["error"]["code"] == "speaking_not_available"
