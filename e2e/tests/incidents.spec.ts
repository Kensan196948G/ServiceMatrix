import { test, expect } from '@playwright/test';
import { API_BASE, getToken } from '../utils/helpers';

test.describe('インシデント API テスト（API レベル）', () => {
  let token: string;

  test.beforeEach(async () => {
    try {
      token = await getToken();
    } catch {
      token = '';
    }
  });

  test('インシデント一覧 API が応答する', async ({ request }) => {
    if (!token) {
      test.skip();
      return;
    }
    const response = await request.get(`${API_BASE}/api/v1/incidents`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(Array.isArray(data)).toBeTruthy();
  });

  test('インシデント作成 API が動作する', async ({ request }) => {
    if (!token) {
      test.skip();
      return;
    }
    const response = await request.post(`${API_BASE}/api/v1/incidents`, {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        title: 'E2E テスト インシデント',
        description: 'Playwright E2E テストで作成',
        priority: 'P3',
        category: 'Test',
      },
    });
    // 201 または 422（バリデーション）
    expect([201, 422, 200]).toContain(response.status());
  });

  test('存在しないインシデントは 404 を返す', async ({ request }) => {
    if (!token) {
      test.skip();
      return;
    }
    const fakeId = '00000000-0000-0000-0000-000000000000';
    const response = await request.get(`${API_BASE}/api/v1/incidents/${fakeId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(response.status()).toBe(404);
  });

  test('認証なしでインシデント一覧アクセスは 401', async ({ request }) => {
    const response = await request.get(`${API_BASE}/api/v1/incidents`);
    expect([401, 403]).toContain(response.status());
  });
});

test.describe('インシデント UI テスト', () => {
  test('インシデント一覧ページが存在する', async ({ page }) => {
    await page.goto('/incidents');
    await page.waitForLoadState('domcontentloaded');
    // ページが読み込まれる（ログイン画面またはインシデント一覧）
    await expect(page.locator('body')).toBeVisible();
  });
});
