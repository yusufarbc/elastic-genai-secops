.PHONY: siem-up platform-up down logs test test-go test-py lint rules apply-k8s

PY_SERVICES := masking-service enrichment-service llm-orchestrator
COMPOSE     := docker compose --project-directory deploy/compose -f deploy/compose/siem.yml
PLATFORM    := $(COMPOSE) -f deploy/compose/platform.yml
K8S_BASE    := deploy/kubernetes/base

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
# GKE deploy (requires GCP_PROJECT and IMAGE_TAG); kustomize overlays replace this in phase 3
# ---------------------------------------------------------------------------

apply-k8s:
	@test -n "$(GCP_PROJECT)" || (echo "ERROR: GCP_PROJECT is not set" && exit 1)
	@test -n "$(IMAGE_TAG)"   || (echo "ERROR: IMAGE_TAG is not set"   && exit 1)
	envsubst < $(K8S_BASE)/namespace.yaml | kubectl apply -f -
	envsubst < $(K8S_BASE)/services/configmap.yaml | kubectl apply -f -
	kubectl apply -f $(K8S_BASE)/eck/elasticsearch.yaml -f $(K8S_BASE)/eck/kibana.yaml \
	  -f $(K8S_BASE)/eck/fleet-server.yaml -f $(K8S_BASE)/eck/ilm-policy.yaml \
	  -f deploy/kubernetes/overlays/gke/gcs-snapshot-repo.yaml
	for svc in detection-service alert-gateway enrichment-service masking-service llm-orchestrator case-service bff; do \
	  envsubst '$$GCP_PROJECT $$IMAGE_TAG' < $(K8S_BASE)/services/$$svc.yaml | kubectl apply -f - ; \
	done
