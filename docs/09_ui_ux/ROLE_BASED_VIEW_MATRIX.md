# ロール別ビューマトリックス

**ドキュメント番号**: SM-UI-002
**バージョン**: 2.0
**分類**: UI/UX設計仕様 / アクセス制御設計
**作成日**: 2026-03-02
**最終更新日**: 2026-03-02
**準拠規格**: ITIL 4 / ISO/IEC 20000 / J-SOX / RBAC原則
**ステータス**: 承認済み

---

## 1. 目的と適用範囲

### 1.1 目的

本ドキュメントは、ServiceMatrix Web UIにおける各ロール別の画面アクセス権限・操作権限・表示制御を定義する。
職務分掌（SoD: Segregation of Duties）原則に基づいたRBAC（Role-Based Access Control）を実装し、J-SOX対応の内部統制を確保する。

### 1.2 ロール定義

| ロールコード | ロール名 | 説明 | 想定利用者 |
|---|---|---|---|
| `SystemAdmin` | システム管理者 | システム全体の最上位管理権限 | ITシステム管理担当 |
| `ProcessOwner` | プロセスオーナー | ITSMプロセス全体の責任者 | IT部門マネージャー |
| `ChangeManager` | 変更マネージャー | 変更管理プロセスの責任者・CAB議長 | 変更管理担当 |
| `Operator` | オペレーター | 日常運用操作の実行担当 | 運用オペレーター・ヘルプデスク |
| `Auditor` | 監査担当者 | 内部統制・コンプライアンス監査担当 | 内部監査部門 |
| `EndUser` | エンドユーザー | サービスリクエストの申請のみ | 一般社員 |

### 1.3 ロール階層

```
SystemAdmin（最上位）
  └── ProcessOwner
        ├── ChangeManager
        │     └── Operator
        └── Auditor（独立・他ロールと兼任不可）

EndUser（独立・最下位）
```

**重要**: AuditorはSoD原則により他の運用ロールとの兼任を禁止する。

---

## 2. ロール別アクセス可能画面一覧

**凡例**: O = フル操作可 / R = 閲覧のみ / X = アクセス不可 / - = 該当なし

### 2.1 ダッシュボード画面

| 画面名 | パス | SystemAdmin | ProcessOwner | ChangeManager | Operator | Auditor | EndUser |
|---|---|---|---|---|---|---|---|
| 運用ダッシュボード | `/dashboard/operational` | O | O | R | O | X | X |
| 管理ダッシュボード | `/dashboard/management` | O | O | R | X | X | X |
| 監査ダッシュボード | `/dashboard/audit` | R | X | X | X | O | X |
| AI監視ダッシュボード | `/dashboard/ai-monitoring` | O | O | X | X | X | X |
| ホームダッシュボード | `/dashboard` | O | O | O | O | R | R |

### 2.2 インシデント管理画面

| 画面名 | パス | SystemAdmin | ProcessOwner | ChangeManager | Operator | Auditor | EndUser |
|---|---|---|---|---|---|---|---|
| インシデント一覧 | `/incidents` | O | O | R | O | R | X |
| インシデント詳細 | `/incidents/{id}` | O | O | R | O | R | X |
| インシデント登録 | `/incidents/new` | O | O | X | O | X | X |
| インシデント編集 | `/incidents/{id}/edit` | O | O | X | O | X | X |
| エスカレーション履歴 | `/incidents/{id}/escalations` | O | O | X | R | R | X |
| SLAカウンター詳細 | `/incidents/{id}/sla` | O | O | X | R | R | X |

### 2.3 変更管理画面

| 画面名 | パス | SystemAdmin | ProcessOwner | ChangeManager | Operator | Auditor | EndUser |
|---|---|---|---|---|---|---|---|
| 変更リクエスト一覧 | `/changes` | O | O | O | R | R | X |
| 変更リクエスト詳細 | `/changes/{id}` | O | O | O | R | R | X |
| RFC作成 | `/changes/new` | O | O | O | O | X | X |
| 変更承認 | `/changes/{id}/approve` | O | O | O | X | X | X |
| 変更承認履歴 | `/changes/{id}/approvals` | O | O | O | R | R | X |
| CABスケジュール | `/changes/cab` | O | O | O | R | R | X |
| PIR（事後レビュー） | `/changes/{id}/pir` | O | O | O | O | R | X |

### 2.4 問題管理画面

| 画面名 | パス | SystemAdmin | ProcessOwner | ChangeManager | Operator | Auditor | EndUser |
|---|---|---|---|---|---|---|---|
| 問題一覧 | `/problems` | O | O | R | O | R | X |
| 問題詳細 | `/problems/{id}` | O | O | R | O | R | X |
| 問題登録 | `/problems/new` | O | O | X | O | X | X |
| 根本原因分析 | `/problems/{id}/rca` | O | O | X | O | R | X |
| KEDB | `/problems/kedb` | O | O | R | R | R | X |

### 2.5 サービスリクエスト画面

| 画面名 | パス | SystemAdmin | ProcessOwner | ChangeManager | Operator | Auditor | EndUser |
|---|---|---|---|---|---|---|---|
| サービスリクエスト一覧 | `/requests` | O | O | R | O | R | O（自分のみ） |
| サービスリクエスト詳細 | `/requests/{id}` | O | O | R | O | R | O（自分のみ） |
| サービスリクエスト申請 | `/requests/new` | O | O | O | O | X | O |

### 2.6 CMDB画面

| 画面名 | パス | SystemAdmin | ProcessOwner | ChangeManager | Operator | Auditor | EndUser |
|---|---|---|---|---|---|---|---|
| CI一覧 | `/cmdb/ci` | O | R | R | O | R | X |
| CI詳細 | `/cmdb/ci/{id}` | O | R | R | O | R | X |
| CI登録 | `/cmdb/ci/new` | O | X | X | O | X | X |
| CI編集 | `/cmdb/ci/{id}/edit` | O | X | X | O | X | X |
| 依存関係グラフ | `/cmdb/relationships` | O | R | R | R | R | X |
| 影響分析 | `/cmdb/impact-analysis` | O | O | O | R | R | X |

### 2.7 SLA・レポート画面

| 画面名 | パス | SystemAdmin | ProcessOwner | ChangeManager | Operator | Auditor | EndUser |
|---|---|---|---|---|---|---|---|
| SLAダッシュボード | `/sla` | O | O | R | R | R | X |
| SLA定義管理 | `/sla/definitions` | O | O | X | X | R | X |
| SLAレポート | `/sla/reports` | O | O | O | R | R | X |
| レポート一覧 | `/reports` | O | O | O | R | R | X |

### 2.8 管理・設定画面

| 画面名 | パス | SystemAdmin | ProcessOwner | ChangeManager | Operator | Auditor | EndUser |
|---|---|---|---|---|---|---|---|
| ユーザー管理 | `/admin/users` | O | X | X | X | X | X |
| ロール管理 | `/admin/roles` | O | X | X | X | X | X |
| システム設定 | `/admin/settings` | O | X | X | X | X | X |
| API設定 | `/admin/api` | O | X | X | X | X | X |
| 通知設定（個人） | `/settings/notifications` | O | O | O | O | O | O |
| 通知設定（全体） | `/admin/notifications` | O | X | X | X | X | X |

### 2.9 監査・コンプライアンス画面

| 画面名 | パス | SystemAdmin | ProcessOwner | ChangeManager | Operator | Auditor | EndUser |
|---|---|---|---|---|---|---|---|
| 監査ログ | `/audit/logs` | R | X | X | X | O | X |
| AI活動ログ | `/audit/ai-activity` | O | X | X | X | R | X |
| コンプライアンスチェック | `/audit/compliance` | O | R | X | X | O | X |
| 監査レポート出力 | `/audit/export` | O | X | X | X | O | X |
| ハッシュ整合性確認 | `/audit/integrity` | O | X | X | X | O | X |

---

## 3. ロール別実行可能操作一覧

### 3.1 SystemAdmin（システム管理者）

**表示可能ダッシュボード**: 全ダッシュボード（運用・管理・AI監視・ホーム）+ 監査ダッシュボード（閲覧）

**実行可能操作**:
- 全画面へのフルアクセス
- ユーザー・ロール・権限の管理
- システム設定の変更
- AI自律レベルの変更
- 監査ログの閲覧（書き込み不可）
- 全種別のインシデント・変更・問題の操作
- APIキー・Webhook設定の管理

**表示不可データ**:
- 監査ログの直接編集・削除
- 他ユーザーのパスワード情報

---

### 3.2 ProcessOwner（プロセスオーナー）

**表示可能ダッシュボード**: 運用ダッシュボード・管理ダッシュボード・ホーム・AI監視ダッシュボード

**実行可能操作**:
- インシデント管理の全操作（削除を除く）
- 変更リクエストの閲覧・コメント
- SLAレポートの生成・閲覧
- コンプライアンスレポートの閲覧
- 通知設定（個人）の変更

**表示不可データ**:
- 監査ログ（詳細）
- AI活動ログ（詳細）
- ユーザー管理・権限設定
- システム設定

---

### 3.3 ChangeManager（変更マネージャー）

**表示可能ダッシュボード**: 運用ダッシュボード（閲覧）・ホームダッシュボード

**実行可能操作**:
- 変更リクエストのCRUD操作（削除はSystemAdminのみ）
- 変更の承認・却下
- CABスケジュールの管理
- PIR（事後レビュー）の実施・記録
- リスク評価の実施
- 影響分析の実施・閲覧
- SLAレポートの生成・閲覧

**表示不可データ**:
- 監査ログ（詳細）
- AI活動ログ
- ユーザー管理
- インシデントの詳細操作（閲覧のみ）

---

### 3.4 Operator（オペレーター）

**表示可能ダッシュボード**: 運用ダッシュボード・ホームダッシュボード

**実行可能操作**:
- インシデントの登録・更新・ステータス変更
- インシデントへのコメント追加・添付ファイル追加
- 担当者アサイン・エスカレーション実施
- 変更リクエストの作成（RFC）
- PIR（事後レビュー）への参加・コメント
- 問題の登録・更新・RCA実施
- CI（構成アイテム）の登録・更新
- SLAカウンターの閲覧
- 通知設定（個人）の変更

**表示不可データ**:
- 変更承認・却下操作（承認権限なし）
- SLA定義の変更
- ユーザー管理・権限設定
- 監査ログ
- AI活動ログ
- 管理ダッシュボード

---

### 3.5 Auditor（監査担当者）

**表示可能ダッシュボード**: 監査ダッシュボード・ホームダッシュボード（閲覧）

**実行可能操作**:
- 監査ログの検索・閲覧
- 監査レポートのエクスポート（PDF/CSV）
- ハッシュ整合性チェックの実行・閲覧
- AI判断ログの閲覧
- コンプライアンスチェックの実行
- 変更承認履歴の閲覧
- SLA違反記録の閲覧
- 通知設定（個人）の変更

**表示不可データ**:
- 監査ログの編集・削除
- インシデント・変更・問題の操作
- CMDB編集
- AI自律レベルの変更
- ユーザー管理

**特記事項**: AuditorはSoD原則により、審査対象となる操作を行うロールとの兼任を禁止する。

---

### 3.6 EndUser（エンドユーザー）

**表示可能ダッシュボード**: ホームダッシュボード（閲覧）

**実行可能操作**:
- サービスリクエストの申請
- 自分が申請したサービスリクエストの閲覧
- 通知設定（個人）の変更
- 自分のプロフィール設定

**表示不可データ**:
- 他ユーザーのチケット
- インシデント・変更・問題の詳細
- CMDB
- 監査ログ・AI活動ログ
- 管理設定

---

## 4. メニュー動的生成要件

### 4.1 ナビゲーション生成原則

```
メニュー表示の基本原則:
1. アクセス不可画面はメニューから非表示（403リダイレクトではなく非表示）
2. 閲覧のみ（R）の画面は表示するが操作ボタンを非活性化
3. ロール変更は次回ログイン時（または即時適用、設定による）に反映
4. 動的メニューはAPIから取得（SSR時にサーバーサイドで権限チェック）
```

### 4.2 ロール別ナビゲーション構成

**SystemAdmin**:
```
[ダッシュボード] 運用 / 管理 / AI監視 / ホーム
[インシデント] 一覧 / 登録 / ダッシュボード
[変更管理] 一覧 / RFC作成 / CAB / ダッシュボード
[問題管理] 一覧 / 登録 / KEDB
[サービスリクエスト] 一覧 / 申請
[SLA] ダッシュボード / 定義管理 / レポート
[CMDB] CI一覧 / 依存関係 / 影響分析
[監査] ログ / AI活動 / コンプライアンス / エクスポート
[管理] ユーザー / ロール / システム設定 / API
```

**Operator**:
```
[ダッシュボード] 運用 / ホーム
[インシデント] 一覧 / 登録
[変更管理] 一覧 / RFC作成
[問題管理] 一覧 / 登録
[サービスリクエスト] 一覧 / 申請
[SLA] ダッシュボード（閲覧）
[CMDB] CI一覧 / CI登録
[設定] 通知設定
```

**Auditor**:
```
[ダッシュボード] 監査 / ホーム（閲覧）
[監査] ログ / AI活動 / コンプライアンス / レポート出力 / 整合性確認
[SLA] レポート（閲覧）
[設定] 通知設定
```

**EndUser**:
```
[ダッシュボード] ホーム（閲覧）
[サービスリクエスト] 自分のリクエスト / 新規申請
[設定] プロフィール / 通知設定
```

### 4.3 動的メニュー実装方針（Next.js）

```typescript
// app/dashboard/layout.tsx
// サーバーコンポーネントで権限チェックを実施
import { getServerSession } from 'next-auth';
import { getMenuItems } from '@/lib/navigation';

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await getServerSession();
  const menuItems = await getMenuItems(session?.user?.role);

  return (
    <div className="flex">
      <Sidebar menuItems={menuItems} />
      <main>{children}</main>
    </div>
  );
}
```

```typescript
// lib/navigation.ts
// ロール別メニュー定義
export async function getMenuItems(role: UserRole): Promise<MenuItem[]> {
  const allMenuItems = MENU_DEFINITIONS;
  return allMenuItems.filter(item =>
    hasPermission(role, item.requiredPermission)
  );
}
```

---

## 5. フロントエンド権限チェック実装方針

### 5.1 二重権限チェック原則

```
フロントエンド権限チェック:
- 目的: UXの向上（不要なボタン・メニューの非表示）
- 責務: 表示制御のみ（セキュリティ強制はバックエンドが担当）

バックエンド権限チェック:
- 目的: セキュリティ強制
- 責務: 全APIエンドポイントでの認可確認
- 原則: フロントエンドを信頼しない（Never Trust Client）
```

### 5.2 権限チェックフック

```typescript
// hooks/usePermissions.ts
interface Permissions {
  canCreate: (resource: ResourceType) => boolean;
  canRead: (resource: ResourceType) => boolean;
  canUpdate: (resource: ResourceType) => boolean;
  canDelete: (resource: ResourceType) => boolean;
  canApprove: (resource: ResourceType) => boolean;
  hasRole: (role: UserRole) => boolean;
  hasAnyRole: (roles: UserRole[]) => boolean;
}

export function usePermissions(): Permissions {
  const { data: session } = useSession();
  const role = session?.user?.role as UserRole;

  return {
    canCreate: (resource) => checkPermission(role, 'create', resource),
    canRead: (resource) => checkPermission(role, 'read', resource),
    canUpdate: (resource) => checkPermission(role, 'update', resource),
    canDelete: (resource) => checkPermission(role, 'delete', resource),
    canApprove: (resource) => checkPermission(role, 'approve', resource),
    hasRole: (targetRole) => role === targetRole,
    hasAnyRole: (roles) => roles.includes(role),
  };
}
```

### 5.3 権限制御コンポーネント

```typescript
// components/shared/PermissionGuard.tsx
interface PermissionGuardProps {
  permission: Permission;
  resource: ResourceType;
  fallback?: ReactNode;       // 権限なし時の代替表示
  hideWhenDenied?: boolean;   // 非表示（デフォルト: true）
  children: ReactNode;
}

export function PermissionGuard({
  permission,
  resource,
  fallback = null,
  hideWhenDenied = true,
  children,
}: PermissionGuardProps) {
  const permissions = usePermissions();
  const hasAccess = permissions[`can${capitalize(permission)}`](resource);

  if (!hasAccess) {
    return hideWhenDenied ? null : <>{fallback}</>;
  }
  return <>{children}</>;
}

// 使用例
<PermissionGuard permission="approve" resource="changes">
  <ApproveButton changeId={change.id} />
</PermissionGuard>
```

### 5.4 権限エラー時のUI表現

| 状況 | UI表現 | 実装 |
|---|---|---|
| アクセス不可画面への直接URL遷移 | 403ページへリダイレクト | Next.js middleware |
| 操作ボタン（権限なし） | ボタン非表示 | PermissionGuard |
| 閲覧のみ権限 | フォーム・ボタンをdisabled | ReadOnlyWrapper |
| SoD違反検知 | ボタン非活性 + ツールチップで理由説明 | SoDGuard |
| AI操作制限 | 操作ブロック + 人間操作者への委譲案内 | AIRestrictionGuard |

### 5.5 ページレベル権限チェック（Next.js Middleware）

```typescript
// middleware.ts
import { withAuth } from 'next-auth/middleware';
import { NextResponse } from 'next/server';

export default withAuth(
  function middleware(req) {
    const token = req.nextauth.token;
    const pathname = req.nextUrl.pathname;

    // ロール別アクセス制御マッピング
    const routePermissions: Record<string, UserRole[]> = {
      '/dashboard/audit': ['Auditor', 'SystemAdmin'],
      '/dashboard/management': ['SystemAdmin', 'ProcessOwner'],
      '/dashboard/ai-monitoring': ['SystemAdmin', 'ProcessOwner'],
      '/admin': ['SystemAdmin'],
      '/audit': ['Auditor', 'SystemAdmin'],
    };

    for (const [route, allowedRoles] of Object.entries(routePermissions)) {
      if (pathname.startsWith(route)) {
        if (!allowedRoles.includes(token?.role as UserRole)) {
          return NextResponse.redirect(new URL('/403', req.url));
        }
      }
    }

    return NextResponse.next();
  },
  {
    callbacks: {
      authorized: ({ token }) => !!token,
    },
  }
);
```

---

## 6. 職務分掌（SoD）ルール

### 6.1 排他的職務分離ルール

| SoDルールID | 職務A | 職務B | 違反時の処理 |
|---|---|---|---|
| SoD-01 | 変更リクエスト作成（RFC申請） | 同一変更の承認 | 承認ボタン非活性化 + ブロック |
| SoD-02 | インシデント登録 | 同一インシデントのクローズ確認 | クローズボタン非活性化 |
| SoD-03 | ユーザー作成 | ロール割り当て（同一ユーザーへ） | システム側で制御 |
| SoD-04 | 監査ログ参照 | 監査対象操作の実行 | Auditorは操作ロール兼任禁止 |
| SoD-05 | AI自律レベル変更 | AI活動実行対象の変更 | SystemAdminのみAI設定変更可 |
| SoD-06 | サービスリクエスト申請 | 同一リクエストの承認・完了処理 | 別担当者での完了確認を強制 |

### 6.2 SoD実装方針

```typescript
// lib/sod.ts
// SoD違反チェックユーティリティ
export async function checkSoDViolation(
  userId: string,
  action: SoDAction,
  resourceId: string
): Promise<SoDCheckResult> {
  // RFC自己承認チェック
  if (action === 'approve_change') {
    const change = await getChange(resourceId);
    if (change.requesterId === userId) {
      return {
        isViolation: true,
        rule: 'SoD-01',
        message: '変更申請者は同一変更を承認できません。別の承認者が必要です。',
      };
    }
  }
  return { isViolation: false };
}
```

---

## 7. 改訂履歴

| バージョン | 日付 | 変更概要 | 変更者 |
|---|---|---|---|
| 1.0 | 2026-03-02 | 初版作成 | - |
| 2.0 | 2026-03-02 | 6ロール定義への拡充、メニュー動的生成要件追加、フロントエンド実装方針詳細化 | - |

---

*本ドキュメントはServiceMatrixプロジェクトの統治原則に基づき管理される。*
*変更はChange Issue → PR → CI検証 → 承認のフローに従うこと。*
