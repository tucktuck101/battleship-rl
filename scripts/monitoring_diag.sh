#!/usr/bin/env bash

# Simple diagnostics for the battleship-rl monitoring stack
# Run from the repo root: ./scripts/monitoring_diag.sh > monitoring_diag.txt

set -u  # (deliberately not using -e so we keep going on errors)

STACK_FILE="docker-compose.training.yml"

# Pick docker compose command
if command -v docker-compose >/dev/null 2>&1; then
  COMPOSE="docker-compose"
else
  COMPOSE="docker compose"
fi

echo "==== SYSTEM INFO ===="
date
echo
echo "---- OS ----"
uname -a || true
sw_vers 2>/dev/null || true
echo
echo "---- Docker ----"
docker version || true
echo
echo "---- Docker Compose ----"
$COMPOSE version || true

echo
echo "==== COMPOSE CONFIG (from $STACK_FILE) ===="
if [ -f "$STACK_FILE" ]; then
  $COMPOSE -f "$STACK_FILE" config || true
else
  echo "File $STACK_FILE not found in $(pwd)"
fi

echo
echo "==== COMPOSE PS (current state) ===="
$COMPOSE -f "$STACK_FILE" ps || true

echo
echo "==== DOCKER NETWORKS ===="
docker network ls || true

# Try to find the monitoring network name used by this stack
echo
echo "---- Monitoring network details (best-guess) ----"
MON_NET_NAME=$($COMPOSE -f "$STACK_FILE" config | awk '/networks:/ {in_n=1; next} in_n && /monitoring:/ {print "monitoring"; exit}' || true)
if [ -n "${MON_NET_NAME:-}" ]; then
  # Compose will create a real network name like "<folder>_monitoring"
  REAL_MON_NET=$(docker network ls --format '{{.Name}}' | grep "${MON_NET_NAME}" || true)
  if [ -n "$REAL_MON_NET" ]; then
    echo "Inspecting network: $REAL_MON_NET"
    docker network inspect "$REAL_MON_NET" || true
  else
    echo "Could not find a docker network matching '*${MON_NET_NAME}*'"
  fi
else
  echo "Could not determine monitoring network name from compose config."
fi

echo
echo "==== CONTAINER IDS (from compose) ===="
for svc in trainer otel-collector tempo loki prometheus grafana; do
  cid=$($COMPOSE -f "$STACK_FILE" ps -q "$svc" 2>/dev/null || true)
  echo "$svc: ${cid:-<no container>}"
done

echo
echo "==== OTEL-COLLECTOR LOGS (last 200 lines) ===="
$COMPOSE -f "$STACK_FILE" logs --tail=200 otel-collector || echo "otel-collector logs unavailable"

echo
echo "==== TEMPO LOGS (last 200 lines) ===="
$COMPOSE -f "$STACK_FILE" logs --tail=200 tempo || echo "tempo logs unavailable"

echo
echo "==== TRAINER LOGS (last 100 lines) ===="
$COMPOSE -f "$STACK_FILE" logs --tail=100 trainer || echo "trainer logs unavailable"

echo
echo "==== PROMETHEUS LOGS (last 100 lines) ===="
$COMPOSE -f "$STACK_FILE" logs --tail=100 prometheus || echo "prometheus logs unavailable"

echo
echo "==== GRAFANA LOGS (last 100 lines) ===="
$COMPOSE -f "$STACK_FILE" logs --tail=100 grafana || echo "grafana logs unavailable"

echo
echo "==== LOKI LOGS (last 100 lines) ===="
$COMPOSE -f "$STACK_FILE" logs --tail=100 loki || echo "loki logs unavailable"

echo
echo "==== OTEL-COLLECTOR CONFIG (ops/otel/config.yaml) ===="
if [ -f "ops/otel/config.yaml" ]; then
  sed -n '1,240p' ops/otel/config.yaml
else
  echo "ops/otel/config.yaml not found"
fi

echo
echo "==== TEMPO CONFIG (ops/tempo/tempo.yaml) ===="
if [ -f "ops/tempo/tempo.yaml" ]; then
  sed -n '1,240p' ops/tempo/tempo.yaml
else
  echo "ops/tempo/tempo.yaml not found"
fi

echo
echo "==== PROMETHEUS CONFIG (ops/prometheus/prometheus.yml) ===="
if [ -f "ops/prometheus/prometheus.yml" ]; then
  sed -n '1,240p' ops/prometheus/prometheus.yml
else
  echo "ops/prometheus/prometheus.yml not found"
fi

echo
echo "==== GRAFANA PROVISIONING TREE (ops/grafana/provisioning) ===="
if [ -d "ops/grafana/provisioning" ]; then
  find ops/grafana/provisioning -maxdepth 3 -type f | sort
else
  echo "ops/grafana/provisioning not found"
fi

echo
echo "==== TRAINER ENV VARS (from container) ===="
TRAINER_ID=$($COMPOSE -f "$STACK_FILE" ps -q trainer 2>/dev/null || true)
if [ -n "${TRAINER_ID:-}" ]; then
  docker inspect "$TRAINER_ID" --format '{{json .Config.Env}}' || true
else
  echo "Trainer container not found"
fi

echo
echo "==== OTEL-COLLECTOR ENV VARS (from container) ===="
OTEL_ID=$($COMPOSE -f "$STACK_FILE" ps -q otel-collector 2>/dev/null || true)
if [ -n "${OTEL_ID:-}" ]; then
  docker inspect "$OTEL_ID" --format '{{json .Config.Env}}' || true
else
  echo "otel-collector container not found"
fi

echo
echo "==== BASIC CONNECTIVITY CHECK (host -> otel-collector -> tempo) ===="
echo "Host -> otel-collector ports:"
nc -vz localhost 4317 2>&1 || echo "nc to localhost:4317 failed (collector gRPC?)"
nc -vz localhost 4318 2>&1 || echo "nc to localhost:4318 failed (collector HTTP?)"

echo
echo "If you want deeper connectivity tests (inside the network), we can add a small helper container once we see this output."
echo
echo "==== END OF MONITORING DIAGNOSTICS ===="
