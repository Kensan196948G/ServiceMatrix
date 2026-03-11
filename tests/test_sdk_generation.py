"""SDK生成スクリプトの存在・内容確認テスト"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def test_generate_sdk_script_exists():
    """generate_sdk.sh が存在する"""
    script = PROJECT_ROOT / "scripts/generate_sdk.sh"
    assert script.exists()


def test_sdk_workflow_exists():
    """sdk-update.yml ワークフローが存在する"""
    workflow = PROJECT_ROOT / ".github/workflows/sdk-update.yml"
    assert workflow.exists()


def test_sdk_readme_exists():
    """sdk/README.md が存在する"""
    readme = PROJECT_ROOT / "sdk/README.md"
    assert readme.exists()


def test_sdk_guide_doc_exists():
    """SDK ガイドドキュメントが存在する"""
    doc = PROJECT_ROOT / "docs/10_api_sdk/SDK_GUIDE.md"
    assert doc.exists()


def test_sdk_workflow_contains_openapi_typescript():
    """ワークフローに openapi-typescript が含まれる"""
    workflow = PROJECT_ROOT / ".github/workflows/sdk-update.yml"
    content = workflow.read_text()
    assert "openapi-typescript" in content


def test_sdk_workflow_triggers_on_schema_change():
    """ワークフローがスキーマ変更時にトリガーされる"""
    workflow = PROJECT_ROOT / ".github/workflows/sdk-update.yml"
    content = workflow.read_text()
    assert "src/schemas" in content or "src/**/*.py" in content
