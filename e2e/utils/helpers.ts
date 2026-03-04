import { Page, expect } from '@playwright/test';

export const TEST_USER = {
  username: process.env.TEST_E2E_USERNAME || 'admin',
  password: process.env.TEST_E2E_PASSWORD || 'Admin1234!',
};

export const API_BASE = process.env.API_BASE_URL || 'http://localhost:8000';

/**
 * ログインヘルパー（UIログイン）
 */
export async function login(page: Page, username = TEST_USER.username, password = TEST_USER.password): Promise<void> {
  await page.goto('/login');
  await page.waitForLoadState('domcontentloaded');

  const usernameInput = page.getByLabel(/ユーザー名|username/i).or(page.locator('input[name="username"]'));
  const passwordInput = page.getByLabel(/パスワード|password/i).or(page.locator('input[type="password"]'));

  await usernameInput.fill(username);
  await passwordInput.fill(password);

  await page.getByRole('button', { name: /ログイン|login|sign in/i }).click();
  await page.waitForLoadState('domcontentloaded');
}

/**
 * API経由で JWT トークンを取得
 */
export async function getToken(username = TEST_USER.username, password = TEST_USER.password): Promise<string> {
  const response = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ username, password }),
  });

  if (!response.ok) {
    throw new Error(`Login failed: ${response.status}`);
  }

  const data = await response.json();
  return data.access_token || '';
}

/**
 * API ヘルスチェック
 */
export async function checkApiHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/api/v1/health`);
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * ページタイトルの確認ヘルパー
 */
export async function assertPageTitle(page: Page, expectedTitle: string | RegExp): Promise<void> {
  await expect(page).toHaveTitle(expectedTitle);
}
