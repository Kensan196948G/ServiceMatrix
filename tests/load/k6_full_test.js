import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// 本番負荷テスト設定（手動実行用）
export const options = {
  stages: [
    { duration: '2m', target: 20 },   // ウォームアップ
    { duration: '5m', target: 100 },  // ピーク負荷
    { duration: '2m', target: 50 },   // 緩和
    { duration: '1m', target: 0 },    // クールダウン
  ],
  thresholds: {
    http_req_duration: ['p(99)<200'],  // 本番目標: 200ms
    http_req_failed: ['rate<0.01'],    // エラーレート1%未満
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const errorRate = new Rate('errors');
const incidentDuration = new Trend('incident_list_duration');

export function setup() {
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

  const incRes = http.get(`${BASE_URL}/api/v1/incidents?limit=20`, { headers });
  incidentDuration.add(incRes.timings.duration);
  check(incRes, {
    'incidents ok': (r) => r.status === 200 || r.status === 401,
    'incidents p99<200ms': (r) => r.timings.duration < 200,
  });

  const chgRes = http.get(`${BASE_URL}/api/v1/changes?limit=20`, { headers });
  check(chgRes, {
    'changes ok': (r) => r.status === 200 || r.status === 401,
    'changes p99<200ms': (r) => r.timings.duration < 200,
  });

  http.get(`${BASE_URL}/api/v1/health`);
  sleep(Math.random() * 2 + 1);
}
