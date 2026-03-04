import { test, expect } from '@playwright/test';
import { API_BASE } from '../utils/helpers';

test.describe('ダッシュボード', () => {
  test('トップページが表示される', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('body')).toBeVisible();
  });

  test('ダッシュボードページが存在する', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('API ドキュメント', () => {
  test('Swagger UI が表示される', async ({ page }) => {
    await page.goto(`${API_BASE}/docs`);
    await page.waitForLoadState('domcontentloaded');
    await expect(page.locator('body')).toBeVisible();
  });

  test('OpenAPI JSON が有効', async ({ request }) => {
    const response = await request.get(`${API_BASE}/openapi.json`);
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data).toHaveProperty('openapi');
    expect(data).toHaveProperty('paths');
  });
});

test.describe('ヘルスチェック', () => {
  test('バックエンド API が起動している', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/v1/health`);
    expect(response.status()).toBe(200);
  });

  test('メトリクスエンドポイントが応答する', async ({ request }) => {
    const response = await request.get(`${API_BASE}/metrics`);
    // 200 または 404（prometheus が未インストールの場合）
    expect([200, 404]).toContain(response.status());
  });
});
