from datetime import date, timedelta


def test_ready_checks_the_database(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "READY"}


def test_list_includes_new_assignment(client, make_assignment):
    item = make_assignment(title="Write Helm chart")
    titles = [a["title"] for a in client.get("/api/assignments").json()]
    assert item["title"] in titles


def test_list_orders_by_nearest_due_date(client, make_assignment):
    later = make_assignment(title="later", due_date=str(date.today() + timedelta(days=9)))
    sooner = make_assignment(title="sooner", due_date=str(date.today() + timedelta(days=1)))
    ids = [a["id"] for a in client.get("/api/assignments").json()]
    assert ids.index(sooner["id"]) < ids.index(later["id"])


def test_filter_by_course(client, make_assignment):
    make_assignment(title="Matrix rank", course="Linear Algebra")
    make_assignment(title="Docker lab", course="DevOps")
    courses = {a["course"] for a in client.get("/api/assignments", params={"course": "Linear Algebra"}).json()}
    assert courses == {"Linear Algebra"}


def test_get_assignment_by_id(client, make_assignment):
    item = make_assignment(title="Configure ingress", priority="HIGH", due_date="2026-10-20")
    response = client.get(f"/api/assignments/{item['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Configure ingress"
    assert body["priority"] == "HIGH"
    assert body["due_date"] == "2026-10-20"
    assert body["status"] == "PENDING"


def test_get_missing_assignment_returns_404(client):
    response = client.get("/api/assignments/999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Assignment not found"


def test_update_only_changes_sent_fields(client, make_assignment):
    item = make_assignment(title="Provision EKS", priority="LOW")
    response = client.put(f"/api/assignments/{item['id']}", json={"status": "IN_PROGRESS"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "IN_PROGRESS"
    assert body["title"] == "Provision EKS"
    assert body["priority"] == "LOW"


def test_update_missing_assignment_returns_404(client):
    response = client.put("/api/assignments/999999", json={"status": "SUBMITTED"})
    assert response.status_code == 404


def test_delete_assignment(client, make_assignment):
    item = make_assignment(title="temporary")
    assert client.delete(f"/api/assignments/{item['id']}").status_code == 204
    assert client.get(f"/api/assignments/{item['id']}").status_code == 404


def test_delete_missing_assignment_returns_404(client):
    assert client.delete("/api/assignments/999999").status_code == 404


def test_stats_count_by_status_and_overdue(client, make_assignment):
    before = client.get("/api/assignments/stats").json()
    yesterday = str(date.today() - timedelta(days=1))
    make_assignment(status="SUBMITTED", due_date=yesterday)  # late but handed in: not overdue
    make_assignment(status="PENDING", due_date=yesterday)    # overdue
    after = client.get("/api/assignments/stats").json()
    assert after["total"] == before["total"] + 2
    assert after["submitted"] == before["submitted"] + 1
    assert after["pending"] == before["pending"] + 1
    assert after["overdue"] == before["overdue"] + 1


def test_empty_title_is_rejected(client):
    response = client.post("/api/assignments", json={"title": "", "course": "DevOps"})
    assert response.status_code == 422


def test_course_is_required(client):
    response = client.post("/api/assignments", json={"title": "x"})
    assert response.status_code == 422


def test_invalid_status_is_rejected(client):
    response = client.post("/api/assignments", json={"title": "x", "course": "DevOps", "status": "DONE"})
    assert response.status_code == 422
