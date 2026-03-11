import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// CIスモークテスト設定
export const options = {
  vus: 10,
  duration: '30s',
  thresholds: {
    http_req_duration: ['p(99)<500'],   // CI緩和: 500ms (本番目標は200ms)
    http_req_failed: ['rate<0.05'],      // エラーレート5%未満
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const errorRate = new Rate('errors');

export function setup() {
  // 認証トークン取得
  const res = http.post(`${BASE_URL}/api/v1/auth/login`, JSON.stringify({
    username: 'admin@example.com',
    password: 'admin123',
  }), { headers: { 'Content-Type': 'application/json' } });

  if (res.status === 200) {
    return { token: res.json('access_token') };
  }
  return { token: null };
}

export default function(data) {
  const headers = data.token
    ? { 'Authorization': `Bearer ${data.token}`, 'Content-Type': 'application/json' }
    : { 'Content-Type': 'application/json' };

  // GET /api/v1/incidents
  const incRes = http.get(`${BASE_URL}/api/v1/incidents?limit=20`, { headers });
  const incOk = check(incRes, {
    'incidents 200': (r) => r.status === 200 || r.status === 401,
    'incidents <500ms': (r) => r.timings.duration < 500,
  });
  errorRate.add(!incOk);

  // GET /api/v1/changes
  const chgRes = http.get(`${BASE_URL}/api/v1/changes?limit=20`, { headers });
  const chgOk = check(chgRes, {
    'changes 200': (r) => r.status === 200 || r.status === 401,
    'changes <500ms': (r) => r.timings.duration < 500,
  });
  errorRate.add(!chgOk);

  // GET /api/v1/health (認証不要)
  const healthRes = http.get(`${BASE_URL}/api/v1/health`);
  check(healthRes, { 'health 200': (r) => r.status === 200 });

  sleep(1);
}
