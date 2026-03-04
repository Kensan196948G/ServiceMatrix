import { test, expect } from '@playwright/test';
import { API_BASE, getToken } from '../utils/helpers';

test.describe('API 全エンドポイント疎通確認', () => {
  let token: string;

  test.beforeAll(async () => {
    try {
      token = await getToken();
    } catch {
      token = '';
    }
  });

  const endpoints = [
    { method: 'GET', path: '/api/v1/health', expectedStatus: [200] },
    { method: 'GET', path: '/openapi.json', expectedStatus: [200] },
    { method: 'GET', path: '/api/v1/incidents', expectedStatus: [200, 401] },
    { method: 'GET', path: '/api/v1/changes', expectedStatus: [200, 401] },
    { method: 'GET', path: '/api/v1/problems', expectedStatus: [200, 401] },
    { method: 'GET', path: '/api/v1/audit/logs', expectedStatus: [200, 401] },
  ];

  for (const ep of endpoints) {
    test(`${ep.method} ${ep.path} が応答する`, async ({ request }) => {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const response = ep.method === 'GET'
        ? await request.get(`${API_BASE}${ep.path}`, { headers })
        : await request.post(`${API_BASE}${ep.path}`, { headers });
      expect(ep.expectedStatus).toContain(response.status());
    });
  }
});
