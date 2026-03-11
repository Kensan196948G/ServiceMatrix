"""外部ITSM同期サービス基盤（Jira / ServiceNow）"""

from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)


class IntegrationSyncService:
    """外部ITSM同期の基盤クラス"""

    DEFAULT_FIELD_MAPPING = {
        "jira": {
            "title": "summary",
            "description": "description",
            "priority": "priority.name",
            "status": "status.name",
        },
        "servicenow": {
            "title": "short_description",
            "description": "description",
            "priority": "priority",
            "status": "state",
        },
    }

    async def test_connection(
        self, integration_type: str, base_url: str, api_key: str
    ) -> dict[str, Any]:
        """外部システムへの接続テスト"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if integration_type == "jira":
                    resp = await client.get(
                        f"{base_url}/rest/api/2/myself",
                        headers={"Authorization": f"Bearer {api_key}"},
                    )
                elif integration_type == "servicenow":
                    resp = await client.get(
                        f"{base_url}/api/now/table/sys_user?sysparm_limit=1",
                        headers={"Authorization": f"Bearer {api_key}"},
                    )
                else:
                    return {"success": False, "error": f"Unknown type: {integration_type}"}

                return {
                    "success": resp.status_code < 400,
                    "status_code": resp.status_code,
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def map_fields(
        self,
        source_data: dict,
        integration_type: str,
        direction: str = "outbound",
    ) -> dict[str, Any]:
        """フィールドマッピングを適用"""
        mapping = self.DEFAULT_FIELD_MAPPING.get(integration_type, {})
        result = {}
        if direction == "outbound":
            for local_field, remote_field in mapping.items():
                if local_field in source_data:
                    result[remote_field] = source_data[local_field]
        else:
            reverse_mapping = {v: k for k, v in mapping.items()}
            for remote_field, local_field in reverse_mapping.items():
                if remote_field in source_data:
                    result[local_field] = source_data[remote_field]
        return result

    async def sync_incident_to_jira(
        self,
        incident_data: dict,
        config: dict,
    ) -> dict[str, Any]:
        """インシデントを Jira チケットに同期（モック実装）"""
        mapped = self.map_fields(incident_data, "jira", "outbound")
        logger.info("sync_to_jira", incident_id=incident_data.get("incident_id"), mapped=mapped)
        # 実際のJira API呼び出しはここで実装
        return {
            "success": True,
            "external_id": f"SVCM-{incident_data.get('incident_id', 'MOCK')[:8]}",
            "mapped_fields": mapped,
        }

    async def sync_incident_to_servicenow(
        self,
        incident_data: dict,
        config: dict,
    ) -> dict[str, Any]:
        """インシデントを ServiceNow チケットに同期（モック実装）"""
        mapped = self.map_fields(incident_data, "servicenow", "outbound")
        logger.info(
            "sync_to_servicenow", incident_id=incident_data.get("incident_id"), mapped=mapped
        )
        return {
            "success": True,
            "sys_id": f"SN-{incident_data.get('incident_id', 'MOCK')[:8]}",
            "mapped_fields": mapped,
        }


integration_sync_service = IntegrationSyncService()
