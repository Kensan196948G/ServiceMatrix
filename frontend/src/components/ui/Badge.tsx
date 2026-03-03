/**
 * ステータスバッジコンポーネント
 * ITSMの各ステータスや優先度を色分けして表示
 */

/** バッジの表示バリアント */
type BadgeVariant =
  | "default"
  | "success"
  | "warning"
  | "danger"
  | "info"
  | "neutral";

interface BadgeProps {
  /** 表示テキスト */
  children: React.ReactNode;
  /** バリアント（色の種類） */
  variant?: BadgeVariant;
  /** 追加CSSクラス */
  className?: string;
}

/** バリアントごとのTailwindクラス */
const variantClasses: Record<BadgeVariant, string> = {
  default: "bg-gray-100 text-gray-800",
  success: "bg-green-100 text-green-800",
  warning: "bg-yellow-100 text-yellow-800",
  danger: "bg-red-100 text-red-800",
  info: "bg-blue-100 text-blue-800",
  neutral: "bg-gray-100 text-gray-600",
};

export default function Badge({
  children,
  variant = "default",
  className = "",
}: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${variantClasses[variant]} ${className}`}
    >
      {children}
    </span>
  );
}

/**
 * 優先度に応じたバッジバリアントを返す
 */
export function getPriorityVariant(priority: string): BadgeVariant {
  switch (priority) {
    case "P1":
      return "danger";
    case "P2":
      return "warning";
    case "P3":
      return "info";
    case "P4":
      return "neutral";
    default:
      return "default";
  }
}

/**
 * インシデントステータスに応じたバッジバリアントを返す
 */
export function getStatusVariant(status: string): BadgeVariant {
  const lower = status.toLowerCase().replace(/_/g, " ");
  if (lower.includes("closed") || lower.includes("resolved")) return "success";
  if (lower.includes("new") || lower.includes("open")) return "info";
  if (
    lower.includes("investigation") ||
    lower.includes("progress") ||
    lower.includes("review")
  )
    return "warning";
  if (lower.includes("rejected") || lower.includes("failed")) return "danger";
  return "default";
}
