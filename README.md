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

First green run: [Actions run #1](https://github.com/dobbydobap/final-devops-project/actions/runs/38944663603)
(Test → Build, scan and push images → Deploy with Helm, 3m19s). Images:
[studydesk-backend](https://github.com/users/dobbydobap/packages/container/package/studydesk-backend) and
[studydesk-frontend](https://github.com/users/dobbydobap/packages/container/package/studydesk-frontend),
tagged `afaa0b63ef87…` (the commit SHA).

### Trivy

Trivy scans the OS packages and the Python/Node libraries inside each image the pipeline builds,
before anything is pushed. In run #1 both images came back clean: the backend
(`python:3.12-slim`, Debian 13, 87 OS packages plus every pip package) and the frontend
(`nginx` on Alpine 3.24) had **0 HIGH or CRITICAL vulnerabilities** with a fix available. The full
report from that run is in [`docs/trivy-ci-run-1.txt`](docs/trivy-ci-run-1.txt). Earlier scans
from when I first added the step are in `docs/screenshots/m6-trivy-before-*.png`.

A clean result means no *fixable* HIGH/CRITICAL issue was known in those images at scan time, not
that they have no CVEs at all — new ones get published every day, which is why the scan runs on
every build and the gate (`exit-code: 1`) would stop the push if one appeared.

## Kubernetes + Helm

```bash
kubectl apply -f k8s/namespace.yaml
helm upgrade --install studydesk helm/studydesk -n studydesk   --set backend.tag=<commit-sha> --set frontend.tag=<commit-sha>
kubectl get pods,svc,ingress -n studydesk
helm list -n studydesk
```

- backend and frontend each run 2 replicas behind ClusterIP Services
- the Ingress sends `/` to the frontend and `/api` to the backend
- an HPA scales the backend on CPU; `scripts/load-test.sh` generates load to watch it scale
- `values-dev.yaml` drops to 1 replica and no HPA for a laptop; the default values are what I deployed

I ran it on Minikube (Docker driver, ingress addon) with the images from GHCR. On Windows the
Minikube IP isn't reachable directly, so the Ingress was reached through
`kubectl port-forward -n ingress-nginx svc/ingress-nginx-controller 8088:80` with
`studydesk.local` pointed at it.

- `troubleshooting/` has two deliberately broken manifests (bad image tag, Service selector that
  matches nothing) used to practise `describe` / `logs` / `get endpoints`

## Monitoring

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace -f monitoring/prometheus-values.yaml
```

The chart's ServiceMonitor tells Prometheus to scrape the backend's `/metrics` on every backend pod
(`serviceMonitorSelectorNilUsesHelmValues: false` lets Prometheus pick up ServiceMonitors from
other releases). The Grafana dashboard is kept as code in
[`monitoring/studydesk-dashboard.json`](monitoring/studydesk-dashboard.json) — request rate by
route, p95 latency, responses by status class, backend pods up, and request count — built on
`http_requests_total` and `http_request_duration_seconds`. Import it from Grafana's
*Dashboards → New → Import*, or push it with the API:

```bash
kubectl port-forward -n monitoring svc/monitoring-grafana 3002:80
jq '{dashboard: ., overwrite: true}' monitoring/studydesk-dashboard.json |   curl -u admin:<password> -H 'Content-Type: application/json' -X POST localhost:3002/api/dashboards/db -d @-
```

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

**What I've actually run.** I don't have a paid AWS account, and EKS plus a NAT gateway are billed
by the hour, so I tested the configuration against [Moto](https://github.com/getmoto/moto), a local
AWS API emulator, using a throwaway provider override (`endpoints { ec2/eks/iam/sts = "http://localhost:5000" }`)
that is not part of this repo:

- `terraform init`, `fmt -check` and `validate` pass with the real config
- `terraform plan`: **54 to add, 0 to change, 0 to destroy**
- `terraform apply` created 51 of the 54 resources, including the VPC, both public and both private
  subnets, NAT and internet gateways, the EKS cluster (`ACTIVE`, 1.31) and the managed node group.
  The other two failed only because Moto doesn't implement them (EKS access entries, and it
  doesn't return the cluster's service CIDR the node-group module checks); real AWS supports both.
- `terraform destroy` removed everything

The same commands with real credentials create the cluster on AWS; I'll run that for the
evaluation and destroy it immediately afterwards.

## Repository layout

```
backend/        FastAPI app, Alembic migration, tests, Dockerfile
frontend/       React app, multi-stage Dockerfile (node build -> nginx)
docker-compose.yml
.github/workflows/ci-cd.yml
helm/studydesk/ Helm chart (+ dev/prod values)
k8s/            namespace
monitoring/     kube-prometheus-stack values + Grafana dashboard JSON
terraform/      VPC + EKS
scripts/        load test for the HPA
troubleshooting/ broken manifests for debugging practice
docs/screenshots/
```

## Evidence

| Module | Where |
|---|---|
| M1 app | [app in the browser](docs/screenshots/m1-app-browser.png), [Swagger](docs/screenshots/m1-swagger-docs.png) |
| M2 tests | test output above (18 passed) and the *Test* job of Actions run #1 |
| M3 git | [commit history](docs/screenshots/m3-commit-history.png) |
| M4 docker | `docker compose up --build` → app on :3000, API on :8000 |
| M5 CI/CD | [green run](docs/screenshots/m5-actions-run.png), [GHCR backend](docs/screenshots/m5-ghcr-backend.png), [GHCR frontend](docs/screenshots/m5-ghcr-frontend.png) |
| M6 Trivy | [`docs/trivy-ci-run-1.txt`](docs/trivy-ci-run-1.txt) |
| M7 Terraform | [init/validate](docs/screenshots/m7-terraform-init-validate.png), [plan](docs/screenshots/m7-terraform-plan.png), [apply (Moto)](docs/screenshots/m7-terraform-apply-moto.png), [VPC + EKS via AWS CLI (Moto)](docs/screenshots/m7-aws-cli-vpc-eks-moto.png), [destroy](docs/screenshots/m7-terraform-destroy.png) |
| M8 Kubernetes | [pods/svc/ingress/hpa](docs/screenshots/m8-kubectl-get-pods-svc.png), [helm list](docs/screenshots/m8-helm-list.png), [app through the Ingress](docs/screenshots/m8-app-via-ingress.png) |
| M9 monitoring | [`/metrics`](docs/screenshots/m9-metrics-endpoint.png), [Prometheus targets UP](docs/screenshots/m9-prometheus-targets.png), [Grafana dashboard](docs/screenshots/m9-grafana-dashboard.png) |

## Status

Everything above has been run: the app and migration, 18 tests, the compose stack, the CI/CD
pipeline (green, images on GHCR, Trivy clean), the Helm deployment on Minikube with Ingress and
HPA, and Prometheus + Grafana scraping the backend. The one piece not yet done on real AWS is the
Terraform apply/destroy, which so far has only been run against Moto (see the Terraform section).
