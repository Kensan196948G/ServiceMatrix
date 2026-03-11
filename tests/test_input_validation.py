"""入力バリデーション＆RequestSanitizerテストスイート - OWASP Top10対応"""

from __future__ import annotations

import pytest

# ── 入力バリデーション ユニットテスト ─────────────────────────────────────────


class TestSqlInjectionDetection:
    """SQLインジェクション検出のテスト"""

    def test_select_statement(self):
        """SELECT文を検出する"""
        from src.core.input_validation import contains_sql_injection

        assert contains_sql_injection("'; SELECT * FROM users--") is True

    def test_drop_table(self):
        """DROP TABLE を検出する"""
        from src.core.input_validation import contains_sql_injection

        assert contains_sql_injection("'; DROP TABLE incidents;") is True

    def test_union_select(self):
        """UNION SELECT を検出する"""
        from src.core.input_validation import contains_sql_injection

        assert contains_sql_injection("' UNION SELECT 1,2,3--") is True

    def test_double_dash_comment(self):
        """-- コメントを検出する"""
        from src.core.input_validation import contains_sql_injection

        assert contains_sql_injection("admin'--") is True

    def test_safe_string(self):
        """安全な文字列は検出しない"""
        from src.core.input_validation import contains_sql_injection

        assert contains_sql_injection("通常のインシデントタイトル") is False
        assert contains_sql_injection("P1 priority incident") is False
        assert contains_sql_injection("System failure at 12:00") is False

    def test_exec_keyword(self):
        """EXEC キーワードを検出する"""
        from src.core.input_validation import contains_sql_injection

        assert contains_sql_injection("'; EXEC xp_cmdshell('cmd')") is True


class TestXssDetection:
    """XSS検出のテスト"""

    def test_script_tag(self):
        """scriptタグを検出する"""
        from src.core.input_validation import contains_xss

        assert contains_xss("<script>alert('xss')</script>") is True

    def test_javascript_protocol(self):
        """javascript:プロトコルを検出する"""
        from src.core.input_validation import contains_xss

        assert contains_xss("javascript:alert(1)") is True

    def test_event_handler(self):
        """onclickなどのイベントハンドラを検出する"""
        from src.core.input_validation import contains_xss

        assert contains_xss("<img onclick=alert(1)>") is True

    def test_iframe_tag(self):
        """iframeタグを検出する"""
        from src.core.input_validation import contains_xss

        assert contains_xss("<iframe src='evil.com'>") is True

    def test_safe_string(self):
        """安全な文字列は検出しない"""
        from src.core.input_validation import contains_xss

        assert contains_xss("通常テキスト") is False
        assert contains_xss("<br>改行") is False
        assert contains_xss("a < b and b > c") is False


class TestPathTraversalDetection:
    """パストラバーサル検出のテスト"""

    def test_dotdot_slash(self):
        """../パストラバーサルを検出する"""
        from src.core.input_validation import contains_path_traversal

        assert contains_path_traversal("../../etc/passwd") is True

    def test_url_encoded(self):
        """URLエンコードされたパストラバーサルを検出する"""
        from src.core.input_validation import contains_path_traversal

        assert contains_path_traversal("%2e%2e/etc/passwd") is True

    def test_safe_path(self):
        """安全なパスは検出しない"""
        from src.core.input_validation import contains_path_traversal

        assert contains_path_traversal("/api/v1/incidents") is False
        assert contains_path_traversal("incidents/list") is False


class TestValidateString:
    """validate_string 関数のテスト"""

    def test_max_length_exceeded(self):
        """最大長超過で400を送出する"""
        from fastapi import HTTPException

        from src.core.input_validation import validate_string

        with pytest.raises(HTTPException) as exc:
            validate_string("a" * 101, max_length=100)
        assert exc.value.status_code == 400

    def test_sql_injection_raises(self):
        """SQLインジェクションで400を送出する"""
        from fastapi import HTTPException

        from src.core.input_validation import validate_string

        with pytest.raises(HTTPException) as exc:
            validate_string("'; DROP TABLE users;--")
        assert exc.value.status_code == 400

    def test_xss_raises(self):
        """XSSで400を送出する"""
        from fastapi import HTTPException

        from src.core.input_validation import validate_string

        with pytest.raises(HTTPException) as exc:
            validate_string("<script>alert(1)</script>")
        assert exc.value.status_code == 400

    def test_path_traversal_raises_when_enabled(self):
        """check_path=True でパストラバーサル検出する"""
        from fastapi import HTTPException

        from src.core.input_validation import validate_string

        with pytest.raises(HTTPException) as exc:
            validate_string("../../etc/passwd", check_path=True)
        assert exc.value.status_code == 400

    def test_path_traversal_ignored_when_disabled(self):
        """check_path=False ではパストラバーサルを無視する"""
        from src.core.input_validation import validate_string

        result = validate_string("../../safe", check_path=False, check_sql=False, check_xss=False)
        assert result == "../../safe"

    def test_safe_string_returned(self):
        """安全な文字列はそのまま返す"""
        from src.core.input_validation import validate_string

        result = validate_string("安全なインシデント説明文")
        assert result == "安全なインシデント説明文"

    def test_no_sql_check(self):
        """check_sql=False の場合はSQL文字列を許可する"""
        from src.core.input_validation import validate_string

        result = validate_string("UNION ALL", check_sql=False, check_xss=False)
        assert result == "UNION ALL"


# ── RequestSanitizerMiddleware テスト ─────────────────────────────────────────


class TestRequestSanitizerMiddleware:
    """RequestSanitizerMiddleware の単体テスト"""

    def _make_middleware(self, max_body_size=None):
        from fastapi import FastAPI

        from src.middleware.request_sanitizer import RequestSanitizerMiddleware

        dummy_app = FastAPI()
        kwargs = {}
        if max_body_size is not None:
            kwargs["max_body_size"] = max_body_size
        return RequestSanitizerMiddleware(dummy_app, **kwargs)

    def test_default_max_body_size(self):
        """デフォルトのボディサイズ制限が10MBである"""
        from src.middleware.request_sanitizer import MAX_BODY_SIZE_BYTES

        mw = self._make_middleware()
        assert mw._max_body_size == MAX_BODY_SIZE_BYTES
        assert MAX_BODY_SIZE_BYTES == 10 * 1024 * 1024

    def test_custom_max_body_size(self):
        """カスタムボディサイズ制限が適用される"""
        mw = self._make_middleware(max_body_size=1024)
        assert mw._max_body_size == 1024

    def test_allowed_content_types_set(self):
        """許可されたContent-Typeセットが存在する"""
        from src.middleware.request_sanitizer import ALLOWED_CONTENT_TYPES

        assert "application/json" in ALLOWED_CONTENT_TYPES
        assert "multipart/form-data" in ALLOWED_CONTENT_TYPES

    def test_middleware_instantiation(self):
        """ミドルウェアが正しく初期化される"""
        mw = self._make_middleware()
        assert mw is not None
        assert mw._enforce_content_type is True


class TestRequestSanitizerIntegration:
    """RequestSanitizerMiddleware の結合テスト（FastAPI TestClient）"""

    def setup_method(self):
        from fastapi.testclient import TestClient

        from src.main import app

        self.client = TestClient(app, raise_server_exceptions=False)

    def test_normal_request_passes(self):
        """通常のリクエストは通過する"""
        resp = self.client.get("/api/v1/health")
        assert resp.status_code in (200, 503)

    def test_oversized_body_rejected(self):
        """Content-Length超過リクエストは413を返す"""
        headers = {"content-length": str(11 * 1024 * 1024)}
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"username": "a", "password": "b"},
            headers=headers,
        )
        assert resp.status_code == 413

    def test_invalid_content_type_rejected(self):
        """未対応のContent-TypeのPOSTリクエストは415を返す"""
        resp = self.client.post(
            "/api/v1/auth/login",
            data=b"raw binary data",
            headers={"content-type": "application/octet-stream"},
        )
        assert resp.status_code == 415

    def test_json_content_type_passes(self):
        """application/jsonはContent-Typeとして許可される"""
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"username": "test", "password": "test"},
        )
        assert resp.status_code != 415
