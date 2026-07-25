"""Validation checks for Phase 9.5 deployment artifacts.

These are lightweight structural checks — no cluster required. They
ensure the manifests, Helm chart, Dockerfiles, compose files, CI
workflows, and docs are present and well-formed.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
DOCKER = ROOT / "docker"
K8S = ROOT / "deploy" / "k8s"
HELM = ROOT / "deploy" / "helm"
CI = ROOT / ".github" / "workflows"
DOCS = ROOT / "docs"


def _yaml_docs(path: Path) -> list[dict]:
    with path.open() as fh:
        return [d for d in yaml.safe_load_all(fh) if d]


# --------------------------------------------------------------------------- #
# Dockerfiles
# --------------------------------------------------------------------------- #


def test_backend_dockerfile_exists():
    assert (DOCKER / "Dockerfile.backend").is_file()


def test_frontend_dockerfile_exists():
    assert (DOCKER / "Dockerfile.frontend").is_file()


def test_backend_dockerfile_multi_stage():
    text = (DOCKER / "Dockerfile.backend").read_text()
    stages = re.findall(r"^FROM\s+\S+\s+AS\s+(\w+)", text, re.MULTILINE)
    assert {"builder", "runtime", "worker", "scheduler"} <= set(stages)


def test_backend_dockerfile_non_root():
    text = (DOCKER / "Dockerfile.backend").read_text()
    assert "USER app" in text
    assert "useradd" in text


def test_backend_dockerfile_healthcheck():
    text = (DOCKER / "Dockerfile.backend").read_text()
    assert "HEALTHCHECK" in text


def test_backend_dockerfile_env_driven_port():
    text = (DOCKER / "Dockerfile.backend").read_text()
    assert "PORT=" in text


def test_frontend_dockerfile_multi_stage():
    text = (DOCKER / "Dockerfile.frontend").read_text()
    stages = re.findall(r"^FROM\s+\S+\s+AS\s+(\w+)", text, re.MULTILINE)
    assert {"builder", "runtime"} <= set(stages)


def test_frontend_dockerfile_non_root():
    text = (DOCKER / "Dockerfile.frontend").read_text()
    assert "USER app" in text


def test_frontend_dockerfile_healthcheck():
    text = (DOCKER / "Dockerfile.frontend").read_text()
    assert "HEALTHCHECK" in text


def test_nginx_conf_healthz_endpoint():
    text = (DOCKER / "nginx.conf").read_text()
    assert "/healthz" in text


# --------------------------------------------------------------------------- #
# Compose files
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("name", ["docker-compose.dev.yml", "docker-compose.prod.yml"])
def test_compose_file_parses(name):
    docs = _yaml_docs(DOCKER / name)
    assert docs and "services" in docs[0]


def test_compose_dev_has_expected_services():
    docs = _yaml_docs(DOCKER / "docker-compose.dev.yml")
    services = docs[0]["services"]
    for expected in ("postgres", "redis", "backend", "worker", "scheduler", "frontend"):
        assert expected in services


def test_compose_prod_has_expected_services():
    docs = _yaml_docs(DOCKER / "docker-compose.prod.yml")
    services = docs[0]["services"]
    for expected in ("backend", "worker", "scheduler", "frontend"):
        assert expected in services


def test_compose_prod_uses_env_indirection():
    text = (DOCKER / "docker-compose.prod.yml").read_text()
    assert "${DATABASE_URL}" in text
    assert "${APP_SECRET_KEY}" in text


def test_compose_dev_healthchecks_present():
    services = _yaml_docs(DOCKER / "docker-compose.dev.yml")[0]["services"]
    assert "healthcheck" in services["postgres"]
    assert "healthcheck" in services["redis"]


# --------------------------------------------------------------------------- #
# Kubernetes manifests
# --------------------------------------------------------------------------- #


K8S_FILES = [
    "namespace.yaml",
    "configmap.yaml",
    "secret.example.yaml",
    "backend-deployment.yaml",
    "worker-deployment.yaml",
    "scheduler-deployment.yaml",
    "frontend-deployment.yaml",
    "ingress.yaml",
    "hpa.yaml",
]


@pytest.mark.parametrize("name", K8S_FILES)
def test_k8s_manifest_parses(name):
    docs = _yaml_docs(K8S / name)
    assert docs, f"{name} produced no documents"
    for doc in docs:
        assert "apiVersion" in doc
        assert "kind" in doc


@pytest.mark.parametrize("name", K8S_FILES)
def test_k8s_manifest_uses_platform_namespace(name):
    for doc in _yaml_docs(K8S / name):
        if doc.get("kind") == "Namespace":
            assert doc["metadata"]["name"] == "platform"
        else:
            ns = doc.get("metadata", {}).get("namespace")
            assert ns == "platform", f"{name} kind={doc['kind']} namespace={ns!r}"


def test_backend_deployment_has_probes():
    for doc in _yaml_docs(K8S / "backend-deployment.yaml"):
        if doc.get("kind") == "Deployment":
            c = doc["spec"]["template"]["spec"]["containers"][0]
            assert "readinessProbe" in c
            assert "livenessProbe" in c
            assert "startupProbe" in c


def test_backend_deployment_runs_non_root():
    for doc in _yaml_docs(K8S / "backend-deployment.yaml"):
        if doc.get("kind") == "Deployment":
            sc = doc["spec"]["template"]["spec"]["securityContext"]
            assert sc["runAsNonRoot"] is True


def test_backend_deployment_has_resources():
    for doc in _yaml_docs(K8S / "backend-deployment.yaml"):
        if doc.get("kind") == "Deployment":
            c = doc["spec"]["template"]["spec"]["containers"][0]
            assert "requests" in c["resources"]
            assert "limits" in c["resources"]


def test_worker_command_is_celery_worker():
    for doc in _yaml_docs(K8S / "worker-deployment.yaml"):
        if doc.get("kind") == "Deployment":
            cmd = doc["spec"]["template"]["spec"]["containers"][0]["command"]
            assert cmd[0] == "celery" and "worker" in cmd


def test_scheduler_command_is_celery_beat():
    for doc in _yaml_docs(K8S / "scheduler-deployment.yaml"):
        if doc.get("kind") == "Deployment":
            cmd = doc["spec"]["template"]["spec"]["containers"][0]["command"]
            assert "beat" in cmd


def test_scheduler_uses_recreate_strategy():
    for doc in _yaml_docs(K8S / "scheduler-deployment.yaml"):
        if doc.get("kind") == "Deployment":
            assert doc["spec"]["strategy"]["type"] == "Recreate"


def test_frontend_deployment_has_probes():
    for doc in _yaml_docs(K8S / "frontend-deployment.yaml"):
        if doc.get("kind") == "Deployment":
            c = doc["spec"]["template"]["spec"]["containers"][0]
            assert "readinessProbe" in c and "livenessProbe" in c


def test_ingress_has_tls():
    for doc in _yaml_docs(K8S / "ingress.yaml"):
        if doc.get("kind") == "Ingress":
            assert doc["spec"]["tls"]
            assert doc["spec"]["rules"][0]["host"]


def test_hpa_defines_backend_and_worker():
    kinds = {d["metadata"]["name"] for d in _yaml_docs(K8S / "hpa.yaml")}
    assert {"backend", "worker"} <= kinds


def test_hpa_metrics_configured():
    for doc in _yaml_docs(K8S / "hpa.yaml"):
        assert doc["spec"]["minReplicas"] >= 1
        assert doc["spec"]["maxReplicas"] >= doc["spec"]["minReplicas"]
        assert doc["spec"]["metrics"]


def test_configmap_contains_expected_keys():
    doc = _yaml_docs(K8S / "configmap.yaml")[0]
    for key in ("APP_ENV", "LOG_LEVEL", "CORS_ORIGINS", "WORKER_CONCURRENCY"):
        assert key in doc["data"]


def test_secret_example_is_template_only():
    text = (K8S / "secret.example.yaml").read_text()
    assert "replace-me" in text.lower() or "template" in text.lower()


# --------------------------------------------------------------------------- #
# Helm chart
# --------------------------------------------------------------------------- #


def test_helm_chart_yaml():
    chart = yaml.safe_load((HELM / "Chart.yaml").read_text())
    assert chart["apiVersion"] == "v2"
    assert chart["name"] == "platform"
    assert chart["version"]
    assert chart["appVersion"]


def test_helm_values_yaml_parses():
    values = yaml.safe_load((HELM / "values.yaml").read_text())
    assert values["backend"]["replicaCount"] >= 1
    assert values["worker"]["concurrency"] >= 1
    assert values["scheduler"]["replicaCount"] >= 1


HELM_TEMPLATES = [
    "_helpers.tpl",
    "namespace.yaml",
    "configmap.yaml",
    "backend.yaml",
    "worker.yaml",
    "scheduler.yaml",
    "frontend.yaml",
    "ingress.yaml",
]


@pytest.mark.parametrize("name", HELM_TEMPLATES)
def test_helm_template_present(name):
    assert (HELM / "templates" / name).is_file()


def test_helm_readme_present():
    assert (HELM / "README.md").is_file()


def test_helm_templates_reference_values():
    text = (HELM / "templates" / "backend.yaml").read_text()
    assert "{{ .Values.image.backend.repository }}" in text
    assert "{{ .Values.backend.replicaCount }}" in text


def test_helm_worker_template_uses_concurrency_value():
    text = (HELM / "templates" / "worker.yaml").read_text()
    assert ".Values.worker.concurrency" in text


def test_helm_ingress_conditional_on_flag():
    text = (HELM / "templates" / "ingress.yaml").read_text()
    assert "{{- if .Values.ingress.enabled }}" in text


def test_helm_values_has_autoscaling():
    values = yaml.safe_load((HELM / "values.yaml").read_text())
    assert values["backend"]["autoscaling"]["enabled"] in (True, False)
    assert values["worker"]["autoscaling"]["enabled"] in (True, False)


# --------------------------------------------------------------------------- #
# CI workflows
# --------------------------------------------------------------------------- #


CI_WORKFLOWS = ["backend.yml", "frontend.yml", "docker.yml", "security.yml"]


@pytest.mark.parametrize("name", CI_WORKFLOWS)
def test_ci_workflow_parses(name):
    doc = yaml.safe_load((CI / name).read_text())
    assert doc["name"]
    # `on:` is parsed as True by PyYAML because YAML 1.1 treats it as a bool.
    assert ("on" in doc) or (True in doc)
    assert doc["jobs"]


def test_backend_workflow_runs_pytest():
    text = (CI / "backend.yml").read_text()
    assert "pytest" in text


def test_frontend_workflow_typechecks_and_builds():
    text = (CI / "frontend.yml").read_text()
    assert "bun run typecheck" in text and "bun run build" in text


def test_docker_workflow_builds_both_images():
    text = (CI / "docker.yml").read_text()
    assert "matrix" in text and "backend" in text and "frontend" in text


def test_security_workflow_has_schedule():
    doc = yaml.safe_load((CI / "security.yml").read_text())
    trigger = doc.get("on") or doc.get(True)
    assert "schedule" in trigger


# --------------------------------------------------------------------------- #
# Docs
# --------------------------------------------------------------------------- #


DOC_FILES = [
    ("DEPLOYMENT.md", ["Environment variables", "Production checklist", "Rollback"]),
    ("BACKUP_AND_RECOVERY.md", ["Backup strategy", "Restore procedure", "RPO"]),
    ("RUNBOOK.md", ["Health & probes", "Scaling guidance", "Incident response"]),
    ("PERFORMANCE.md", ["Methodology", "Baseline", "Tuning recommendations"]),
]


@pytest.mark.parametrize("name,sections", DOC_FILES)
def test_doc_has_expected_sections(name, sections):
    text = (DOCS / name).read_text()
    for section in sections:
        assert section in text, f"{name} missing {section!r}"


def test_deployment_doc_lists_required_env_vars():
    text = (DOCS / "DEPLOYMENT.md").read_text()
    for var in ("DATABASE_URL", "REDIS_URL", "APP_SECRET_KEY", "APP_ENV"):
        assert var in text


def test_runbook_documents_health_endpoints():
    text = (DOCS / "RUNBOOK.md").read_text()
    for endpoint in ("/health", "/health/live", "/health/ready", "/healthz"):
        assert endpoint in text


def test_backup_doc_covers_all_stores():
    text = (DOCS / "BACKUP_AND_RECOVERY.md").read_text()
    for store in ("PostgreSQL", "Redis"):
        assert store in text


def test_performance_doc_points_to_bench_harness():
    text = (DOCS / "PERFORMANCE.md").read_text()
    assert "scripts/benchmarks/bench_runtime" in text