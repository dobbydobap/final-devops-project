# StudyDesk

StudyDesk is a small assignment tracker for college: you add an assignment with its course and due
date, and the dashboard shows what is pending, what is overdue, and which deadlines are coming up
next. I built it because I kept losing track of deadlines across Scaler courses, and it gave me a
real app to put the whole DevOps pipeline around for the Session 21 capstone.

The DevOps layer follows the architecture from the course's TaskBoard reference (FastAPI +
PostgreSQL + React, Docker, GitHub Actions, Helm, Terraform, Prometheus). The application itself —
data model, API, migration, tests and UI — is StudyDesk's own.

## What it does

- Add an assignment: title, course, due date, priority, notes
- Move it through `PENDING → IN_PROGRESS → SUBMITTED`
- List is sorted by nearest due date; filter by status or course
- Stats: pending / in progress / submitted, and **overdue** (past due date and not submitted)
- "Coming up" panel with the next open deadlines

## Stack

| Layer | Tech |
|---|---|
| Frontend | React (Vite), served by Nginx (multi-stage image, non-root) |
| Backend | FastAPI, SQLAlchemy, Alembic, `/metrics` via prometheus-fastapi-instrumentator |
| Database | PostgreSQL 16 |
| CI/CD | GitHub Actions → pytest, frontend build, Docker build, Trivy, push to GHCR |
| Kubernetes | Helm chart in `helm/studydesk` (Deployments, Services, Ingress, HPA, ServiceMonitor) |
| Infra | Terraform for an AWS VPC + EKS cluster in `terraform/` |
| Monitoring | kube-prometheus-stack (Prometheus + Grafana), values in `monitoring/` |

```
browser ──> Ingress ──/────> frontend (nginx)
                   └─/api──> backend (FastAPI) ──> PostgreSQL
                                   │
                              /metrics <── Prometheus ──> Grafana
```

## API

| Method | Path | |
|---|---|---|
| GET | `/health` | liveness, returns `{"status": "UP"}` |
| GET | `/ready` | readiness, checks the database |
| GET | `/api/assignments` | list, soonest due first. `?course=DevOps` to filter |
| GET | `/api/assignments/stats` | counts by status + overdue |
| GET | `/api/assignments/{id}` | one assignment |
| POST | `/api/assignments` | create |
| PUT | `/api/assignments/{id}` | partial update (only the fields you send) |
| DELETE | `/api/assignments/{id}` | delete |
| GET | `/metrics` | Prometheus metrics |

Swagger UI is at `http://localhost:8000/docs` when running locally.

## Running it locally

```bash
docker compose up --build
```

- App: http://localhost:3000
- API: http://localhost:8000/docs

The backend container runs `alembic upgrade head` before starting Uvicorn, so the `assignments`
table is created by the migration in `backend/alembic/versions/0001_create_assignments.py`.

If you ran an older version of this project before, reset the database volume once with
`docker compose down -v` (the database user changed).

## Tests

```bash
cd backend
pip install -r requirements.txt
pytest -v
```

`tests/conftest.py` points the app at a throwaway SQLite file before anything imports the config, so
the tests never touch Postgres. Current run:

```
tests/test_api.py::test_health PASSED
tests/test_api.py::test_root PASSED
tests/test_api.py::test_create_assignment PASSED
tests/test_api.py::test_metrics_endpoint PASSED
tests/test_assignments_crud.py::test_ready_checks_the_database PASSED
tests/test_assignments_crud.py::test_list_includes_new_assignment PASSED
tests/test_assignments_crud.py::test_list_orders_by_nearest_due_date PASSED
tests/test_assignments_crud.py::test_filter_by_course PASSED
tests/test_assignments_crud.py::test_get_assignment_by_id PASSED
tests/test_assignments_crud.py::test_get_missing_assignment_returns_404 PASSED
tests/test_assignments_crud.py::test_update_only_changes_sent_fields PASSED
tests/test_assignments_crud.py::test_update_missing_assignment_returns_404 PASSED
tests/test_assignments_crud.py::test_delete_assignment PASSED
tests/test_assignments_crud.py::test_delete_missing_assignment_returns_404 PASSED
tests/test_assignments_crud.py::test_stats_count_by_status_and_overdue PASSED
tests/test_assignments_crud.py::test_empty_title_is_rejected PASSED
tests/test_assignments_crud.py::test_course_is_required PASSED
tests/test_assignments_crud.py::test_invalid_status_is_rejected PASSED
======================== 18 passed in 0.52s ========================
```

## CI/CD

`.github/workflows/ci-cd.yml` runs on every push and pull request to `main`:

1. **test** — `pytest -v` on the backend and `npm run build` on the frontend. A failing test stops
   the pipeline before any image is built.
2. **build-scan-push** — builds both images tagged with the commit SHA (never `latest`), scans
   each with Trivy (`HIGH,CRITICAL`, `exit-code: 1`, so a fixable high/critical CVE fails the
   build), then pushes to `ghcr.io/dobbydobap/studydesk-backend` and `studydesk-frontend`.
3. **deploy** — creates a kind cluster on the runner and runs `helm upgrade --install` with the new
   SHA tags, as a smoke test that the chart deploys the images that were just pushed.

### Trivy

Trivy scans the OS packages and Python/Node libraries inside each built image. The scans from when
I first added it are in `docs/screenshots/m6-trivy-before-*.png`, and the result after fixing the
images is in `m6-trivy-after.png`. A clean result
means no *fixable* HIGH or CRITICAL vulnerability is known in that image at scan time — not that it
has no CVEs at all, which is why the scan runs on every build.

## Kubernetes + Helm

```bash
kubectl apply -f k8s/namespace.yaml
helm upgrade --install studydesk helm/studydesk -n studydesk -f helm/studydesk/values-dev.yaml
kubectl get pods,svc,ingress -n studydesk
helm list -n studydesk
```

- backend and frontend each run 2 replicas behind ClusterIP Services
- the Ingress sends `/` to the frontend and `/api` to the backend
- an HPA scales the backend on CPU; `scripts/load-test.sh` generates load to watch it scale
- `troubleshooting/` has two deliberately broken manifests (bad image tag, Service selector that
  matches nothing) used to practise `describe` / `logs` / `get endpoints`

## Monitoring

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace -f monitoring/prometheus-values.yaml
```

The chart's ServiceMonitor tells Prometheus to scrape the backend's `/metrics`. Grafana panels use
`http_requests_total` (request rate by route) and `http_request_duration_seconds` (latency).

## Terraform (AWS)

`terraform/` creates a VPC (2 public + 2 private subnets across `ap-south-1a/b`, one NAT gateway)
and an EKS 1.31 cluster with a managed node group of 2 × t3.medium.

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply      # creates billable resources
terraform destroy    # run this right after evaluation
```

No credentials are stored in the repo; Terraform reads them from `aws configure` or environment
variables. `terraform.tfvars` and all state files are git-ignored.

## Repository layout

```
backend/        FastAPI app, Alembic migration, tests, Dockerfile
frontend/       React app, multi-stage Dockerfile (node build -> nginx)
docker-compose.yml
.github/workflows/ci-cd.yml
helm/studydesk/ Helm chart (+ dev/prod values)
k8s/            namespace
monitoring/     kube-prometheus-stack values
terraform/      VPC + EKS
scripts/        load test for the HPA
troubleshooting/ broken manifests for debugging practice
docs/screenshots/
```

## Status

Done and verified locally: the app, Alembic migration, 18 passing tests, Docker images, compose
stack, CI workflow, Helm chart and monitoring values.

Still to capture: the green GitHub Actions run and GHCR packages, the Kubernetes/Grafana
screenshots for StudyDesk, and the Terraform `apply`/`destroy` on AWS — EKS is not free-tier, so I
am running it only for the evaluation and destroying it straight after.
