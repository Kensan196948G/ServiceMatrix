"""Kubernetes Helm Chart 検証テスト - Issue #77

helm コマンドなしで YAML 構造・必須フィールド・セキュリティ設定を検証する。
"""

from pathlib import Path

import pytest
import yaml

CHART_ROOT = Path(__file__).parent.parent / "k8s" / "helm" / "servicematrix"
TEMPLATES = CHART_ROOT / "templates"
VALUES_FILE = CHART_ROOT / "values.yaml"
VALUES_PROD_FILE = CHART_ROOT / "values-prod.yaml"


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def load_yaml_multi(path: Path) -> list[dict]:
    """複数ドキュメントを含む YAML ファイルをリストで返す。"""
    with open(path) as f:
        return [doc for doc in yaml.safe_load_all(f) if doc is not None]


def find_templates(pattern: str) -> list[Path]:
    return sorted(TEMPLATES.rglob(pattern))


# ---------------------------------------------------------------------------
# Chart.yaml 検証
# ---------------------------------------------------------------------------


def test_chart_yaml_exists() -> None:
    """Chart.yaml が存在する"""
    assert (CHART_ROOT / "Chart.yaml").exists()


def test_chart_yaml_required_fields() -> None:
    """Chart.yaml に必須フィールドが存在する"""
    chart = load_yaml(CHART_ROOT / "Chart.yaml")
    assert "apiVersion" in chart
    assert "name" in chart
    assert "version" in chart
    assert "appVersion" in chart
    assert chart["apiVersion"] == "v2"
    assert chart["name"] == "servicematrix"


def test_chart_yaml_version_format() -> None:
    """Chart.yaml のバージョンが semver 形式"""
    chart = load_yaml(CHART_ROOT / "Chart.yaml")
    version = chart["version"]
    parts = version.split(".")
    assert len(parts) == 3, f"バージョンが semver 形式ではない: {version}"
    for part in parts:
        assert part.isdigit(), f"バージョン部分が数値ではない: {part}"


# ---------------------------------------------------------------------------
# values.yaml 検証
# ---------------------------------------------------------------------------


def test_values_yaml_exists() -> None:
    """values.yaml が存在する"""
    assert VALUES_FILE.exists()


def test_values_yaml_backend_section() -> None:
    """values.yaml に backend セクションが存在する"""
    values = load_yaml(VALUES_FILE)
    assert "backend" in values
    backend = values["backend"]
    assert "image" in backend
    assert "replicaCount" in backend
    assert "resources" in backend
    assert "autoscaling" in backend


def test_values_yaml_resource_limits() -> None:
    """backend/frontend リソース制限が設定されている"""
    values = load_yaml(VALUES_FILE)
    for component in ("backend", "frontend"):
        resources = values[component]["resources"]
        assert "requests" in resources, f"{component} に requests がない"
        assert "limits" in resources, f"{component} に limits がない"
        assert "memory" in resources["requests"]
        assert "cpu" in resources["requests"]


def test_values_yaml_autoscaling_bounds() -> None:
    """HPA の min <= max を満たす"""
    values = load_yaml(VALUES_FILE)
    for component in ("backend", "frontend"):
        hpa = values[component]["autoscaling"]
        assert hpa["minReplicas"] >= 1
        assert hpa["maxReplicas"] >= hpa["minReplicas"]


def test_values_yaml_ingress_section() -> None:
    """values.yaml に ingress セクションが存在する"""
    values = load_yaml(VALUES_FILE)
    assert "ingress" in values
    ingress = values["ingress"]
    assert "enabled" in ingress
    assert "host" in ingress


def test_values_yaml_network_policy_section() -> None:
    """values.yaml に networkPolicy セクションが存在する"""
    values = load_yaml(VALUES_FILE)
    assert "networkPolicy" in values
    assert "enabled" in values["networkPolicy"]


def test_values_yaml_service_account_section() -> None:
    """values.yaml に serviceAccount セクションが存在する"""
    values = load_yaml(VALUES_FILE)
    assert "serviceAccount" in values
    assert "create" in values["serviceAccount"]


# ---------------------------------------------------------------------------
# テンプレートファイル存在確認
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "template_path",
    [
        "backend/deployment.yaml",
        "backend/service.yaml",
        "backend/hpa.yaml",
        "backend/configmap.yaml",
        "backend/pdb.yaml",
        "frontend/deployment.yaml",
        "frontend/service.yaml",
        "frontend/hpa.yaml",
        "frontend/pdb.yaml",
        "postgres/statefulset.yaml",
        "postgres/service.yaml",
        "postgres/pvc.yaml",
        "redis/deployment.yaml",
        "redis/service.yaml",
        "secrets.yaml",
        "namespace.yaml",
        "ingress.yaml",
        "networkpolicy.yaml",
        "serviceaccount.yaml",
        "_helpers.tpl",
    ],
)
def test_template_file_exists(template_path: str) -> None:
    """テンプレートファイルが存在する"""
    assert (TEMPLATES / template_path).exists(), f"{template_path} が存在しない"


# ---------------------------------------------------------------------------
# YAML 構文検証
# ---------------------------------------------------------------------------


def test_all_yaml_templates_contain_api_version() -> None:
    """全テンプレート YAML ファイル（_helpers.tpl 除く）に apiVersion が含まれる。"""
    errors = []
    for yaml_file in TEMPLATES.rglob("*.yaml"):
        content = yaml_file.read_text(encoding="utf-8")
        if "apiVersion" not in content:
            errors.append(f"{yaml_file.relative_to(TEMPLATES)}: apiVersion が見つからない")
    assert not errors, "apiVersion 不足:\n" + "\n".join(errors)


def test_all_yaml_templates_are_nonempty() -> None:
    """全テンプレートファイルが空でない。"""
    for yaml_file in TEMPLATES.rglob("*.yaml"):
        assert yaml_file.stat().st_size > 0, f"{yaml_file.name} が空ファイル"


def test_all_yaml_templates_have_no_unclosed_braces() -> None:
    """Helm テンプレート構文に未閉じブレースがない。"""
    import re

    errors = []
    for yaml_file in TEMPLATES.rglob("*.yaml"):
        content = yaml_file.read_text(encoding="utf-8")
        opens = len(re.findall(r"\{\{", content))
        closes = len(re.findall(r"\}\}", content))
        if opens != closes:
            errors.append(f"{yaml_file.name}: {{ {opens} 個 vs }} {closes} 個")
    assert not errors, "未閉じブレース:\n" + "\n".join(errors)


# ---------------------------------------------------------------------------
# セキュリティ設定検証
# ---------------------------------------------------------------------------


def test_backend_deployment_has_liveness_probe() -> None:
    """backend Deployment に livenessProbe が設定されている"""
    content = (TEMPLATES / "backend" / "deployment.yaml").read_text()
    assert "livenessProbe" in content


def test_backend_deployment_has_readiness_probe() -> None:
    """backend Deployment に readinessProbe が設定されている"""
    content = (TEMPLATES / "backend" / "deployment.yaml").read_text()
    assert "readinessProbe" in content


def test_secrets_template_uses_secret_ref() -> None:
    """secrets.yaml が Secret リソースを定義している"""
    content = (TEMPLATES / "secrets.yaml").read_text()
    assert "kind: Secret" in content or "Secret" in content


def test_ingress_tls_configurable() -> None:
    """ingress.yaml に TLS 設定がある"""
    content = (TEMPLATES / "ingress.yaml").read_text()
    assert "tls" in content.lower()


def test_pdb_template_backend_exists() -> None:
    """backend PDB テンプレートが minAvailable を設定している"""
    content = (TEMPLATES / "backend" / "pdb.yaml").read_text()
    assert "PodDisruptionBudget" in content
    assert "minAvailable" in content


def test_pdb_template_frontend_exists() -> None:
    """frontend PDB テンプレートが minAvailable を設定している"""
    content = (TEMPLATES / "frontend" / "pdb.yaml").read_text()
    assert "PodDisruptionBudget" in content
    assert "minAvailable" in content


def test_network_policy_restricts_egress() -> None:
    """NetworkPolicy テンプレートに Egress 制限がある"""
    content = (TEMPLATES / "networkpolicy.yaml").read_text()
    assert "Egress" in content
    assert "Ingress" in content


def test_service_account_template_disables_token_automount() -> None:
    """ServiceAccount テンプレートが automountServiceAccountToken: false を設定"""
    content = (TEMPLATES / "serviceaccount.yaml").read_text()
    assert "automountServiceAccountToken: false" in content


# ---------------------------------------------------------------------------
# values-prod.yaml 検証
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not VALUES_PROD_FILE.exists(), reason="values-prod.yaml が存在しない")
def test_values_prod_higher_replicas() -> None:
    """values-prod.yaml の replicaCount がデフォルト値以上"""
    prod = load_yaml(VALUES_PROD_FILE)
    default = load_yaml(VALUES_FILE)
    if "backend" in prod and "replicaCount" in prod["backend"]:
        assert prod["backend"]["replicaCount"] >= default["backend"]["replicaCount"]
