.PHONY: siem-up platform-up down logs test test-go test-py lint rules k8s-render k8s-apply

PY_SERVICES := masking-service enrichment-service llm-orchestrator
COMPOSE     := docker compose --project-directory deploy/compose -f deploy/compose/siem.yml
PLATFORM    := $(COMPOSE) -f deploy/compose/platform.yml

# ---------------------------------------------------------------------------
# Docker Compose (on Windows without make, run the docker compose commands from deploy/compose)
# ---------------------------------------------------------------------------

siem-up:            ## Elasticsearch + Kibana + Logstash + detection rules
	sh deploy/compose/init-env.sh
	$(COMPOSE) up -d
	@echo "Kibana: http://localhost:5601 (user elastic, password in deploy/compose/.env)"

platform-up:        ## siem + AI triage pipeline (mock LLM unless LLM_PROVIDER is set in .env)
	sh deploy/compose/init-env.sh
	$(PLATFORM) up -d --build
	@echo "Kibana: http://localhost:5601   Cases API: http://localhost:8080/api/cases"

down:
	$(PLATFORM) down

logs:
	$(PLATFORM) logs -f --tail=50

# ---------------------------------------------------------------------------
# Tests and lint
# ---------------------------------------------------------------------------

test: test-go test-py

test-go:
	go vet ./...
	go test -race -count=1 ./...

test-py:
	$(foreach svc,$(PY_SERVICES),(cd services/$(svc) && python -m pytest -q tests) &&) true

lint:
	test -z "$$(gofmt -l libs services)"
	ruff check libs/py-common $(addprefix services/,$(PY_SERVICES))

rules:              ## rebuild content/detection-rules/rules.ndjson from rules.yml
	python content/detection-rules/build.py

# ---------------------------------------------------------------------------
# Kubernetes (ECK + kustomize): make k8s-apply OVERLAY=lab|onprem|gke
# ---------------------------------------------------------------------------

OVERLAY ?= lab

k8s-render:
	kubectl kustomize --load-restrictor LoadRestrictionsNone deploy/kubernetes/overlays/$(OVERLAY)

k8s-apply:
	sh deploy/kubernetes/init-secrets.sh $(OVERLAY)
	kubectl -n esm delete job esm-bootstrap --ignore-not-found
	kubectl kustomize --load-restrictor LoadRestrictionsNone deploy/kubernetes/overlays/$(OVERLAY) \
	  | kubectl apply --server-side --force-conflicts -f -
