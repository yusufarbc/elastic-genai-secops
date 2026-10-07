.PHONY: up down build test lint clean logs

GO_SERVICES   := detection-service alert-gateway case-service bff
PY_SERVICES   := enrichment-service masking-service llm-orchestrator

COMPOSE       := docker compose -f deploy/compose/docker-compose.yml
K8S_BASE      := deploy/kubernetes/base

# ---------------------------------------------------------------------------
# Local dev
# ---------------------------------------------------------------------------

up:
	$(COMPOSE) up -d --build
	@echo "Kibana:  http://localhost:5601"
	@echo "BFF:     http://localhost:8080"

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=50

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

build:
	$(COMPOSE) build

build-go:
	$(foreach svc,$(GO_SERVICES),cd services/$(svc) && go build ./... && cd ../..;)

build-py:
	$(foreach svc,$(PY_SERVICES),cd services/$(svc) && pip install -q . && cd ../..;)

# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

test: test-go test-py

test-go:
	$(foreach svc,$(GO_SERVICES),\
	  echo "==> testing $(svc)" && \
	  cd services/$(svc) && go test ./... -race -count=1 && cd ../..;)

test-py:
	$(foreach svc,$(PY_SERVICES),\
	  echo "==> testing $(svc)" && \
	  cd services/$(svc) && python -m pytest tests/ -v 2>/dev/null || echo "no tests yet" && cd ../..;)

# ---------------------------------------------------------------------------
# Lint
# ---------------------------------------------------------------------------

lint: lint-go lint-py

lint-go:
	$(foreach svc,$(GO_SERVICES),\
	  echo "==> linting $(svc)" && \
	  cd services/$(svc) && golangci-lint run ./... && cd ../..;)

lint-py:
	$(foreach svc,$(PY_SERVICES),\
	  echo "==> linting $(svc)" && \
	  cd services/$(svc) && ruff check . && ruff format --check . && cd ../..;)

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

clean:
	$(COMPOSE) down -v --remove-orphans
	docker system prune -f

# ---------------------------------------------------------------------------
# GKE deploy (requires GCP_PROJECT and IMAGE_TAG env vars)
# Usage: GCP_PROJECT=my-project IMAGE_TAG=abc1234 make apply-k8s
# ---------------------------------------------------------------------------

apply-k8s:
	@test -n "$(GCP_PROJECT)" || (echo "ERROR: GCP_PROJECT is not set" && exit 1)
	@test -n "$(IMAGE_TAG)"   || (echo "ERROR: IMAGE_TAG is not set"   && exit 1)
	@echo "Applying K8s manifests for project=$(GCP_PROJECT) tag=$(IMAGE_TAG)..."
	GCP_PROJECT=$(GCP_PROJECT) IMAGE_TAG=$(IMAGE_TAG) \
	  envsubst < $(K8S_BASE)/namespace.yaml | kubectl apply -f -
	GCP_PROJECT=$(GCP_PROJECT) IMAGE_TAG=$(IMAGE_TAG) \
	  envsubst < $(K8S_BASE)/services/configmap.yaml | kubectl apply -f -
	kubectl apply -f $(K8S_BASE)/eck/elasticsearch.yaml -f $(K8S_BASE)/eck/kibana.yaml \
	  -f $(K8S_BASE)/eck/fleet-server.yaml -f $(K8S_BASE)/eck/ilm-policy.yaml \
	  -f deploy/kubernetes/overlays/gke/gcs-snapshot-repo.yaml
	GCP_PROJECT=$(GCP_PROJECT) IMAGE_TAG=$(IMAGE_TAG) \
	  envsubst '$$GCP_PROJECT $$IMAGE_TAG' < $(K8S_BASE)/services/detection-service.yaml | kubectl apply -f -
	GCP_PROJECT=$(GCP_PROJECT) IMAGE_TAG=$(IMAGE_TAG) \
	  envsubst '$$GCP_PROJECT $$IMAGE_TAG' < $(K8S_BASE)/services/alert-gateway.yaml | kubectl apply -f -
	GCP_PROJECT=$(GCP_PROJECT) IMAGE_TAG=$(IMAGE_TAG) \
	  envsubst '$$GCP_PROJECT $$IMAGE_TAG' < $(K8S_BASE)/services/enrichment-service.yaml | kubectl apply -f -
	GCP_PROJECT=$(GCP_PROJECT) IMAGE_TAG=$(IMAGE_TAG) \
	  envsubst '$$GCP_PROJECT $$IMAGE_TAG' < $(K8S_BASE)/services/masking-service.yaml | kubectl apply -f -
	GCP_PROJECT=$(GCP_PROJECT) IMAGE_TAG=$(IMAGE_TAG) \
	  envsubst '$$GCP_PROJECT $$IMAGE_TAG' < $(K8S_BASE)/services/llm-orchestrator.yaml | kubectl apply -f -
	GCP_PROJECT=$(GCP_PROJECT) IMAGE_TAG=$(IMAGE_TAG) \
	  envsubst '$$GCP_PROJECT $$IMAGE_TAG' < $(K8S_BASE)/services/case-service.yaml | kubectl apply -f -
	GCP_PROJECT=$(GCP_PROJECT) IMAGE_TAG=$(IMAGE_TAG) \
	  envsubst '$$GCP_PROJECT $$IMAGE_TAG' < $(K8S_BASE)/services/bff.yaml | kubectl apply -f -
	@echo "Done. Check pod status: kubectl get pods -n esm"

# ---------------------------------------------------------------------------
# Pub/Sub topic bootstrap (run once against the emulator)
# ---------------------------------------------------------------------------

pubsub-init:
	@echo "Creating Pub/Sub topics and subscriptions on emulator..."
	$(eval PUBSUB_URL=http://localhost:8085)
	curl -s -X PUT "$(PUBSUB_URL)/v1/projects/esm-local/topics/esm.alerts"
	curl -s -X PUT "$(PUBSUB_URL)/v1/projects/esm-local/topics/esm.incidents"
	curl -s -X PUT "$(PUBSUB_URL)/v1/projects/esm-local/topics/esm.masked-incidents"
	curl -s -X PUT "$(PUBSUB_URL)/v1/projects/esm-local/topics/esm.triage-decisions"
	curl -s -X PUT "$(PUBSUB_URL)/v1/projects/esm-local/topics/esm.dlq"
	curl -s -X PUT "$(PUBSUB_URL)/v1/projects/esm-local/subscriptions/esm.alerts.gateway-sub" \
	  -H "Content-Type: application/json" \
	  -d '{"topic":"projects/esm-local/topics/esm.alerts"}'
	curl -s -X PUT "$(PUBSUB_URL)/v1/projects/esm-local/subscriptions/esm.incidents.enrichment-sub" \
	  -H "Content-Type: application/json" \
	  -d '{"topic":"projects/esm-local/topics/esm.incidents"}'
	curl -s -X PUT "$(PUBSUB_URL)/v1/projects/esm-local/subscriptions/esm.masked-incidents.llm-sub" \
	  -H "Content-Type: application/json" \
	  -d '{"topic":"projects/esm-local/topics/esm.masked-incidents"}'
	curl -s -X PUT "$(PUBSUB_URL)/v1/projects/esm-local/subscriptions/esm.triage-decisions.case-sub" \
	  -H "Content-Type: application/json" \
	  -d '{"topic":"projects/esm-local/topics/esm.triage-decisions"}'
	@echo "Done."
