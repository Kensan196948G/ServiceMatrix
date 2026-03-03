/**
 * ローディングスピナーコンポーネント
 * データ取得中の待機表示に使用
 */

interface LoadingSpinnerProps {
  /** スピナーのサイズ */
  size?: "sm" | "md" | "lg";
  /** 表示メッセージ */
  message?: string;
}

const sizeClasses = {
  sm: "h-4 w-4",
  md: "h-8 w-8",
  lg: "h-12 w-12",
};

export default function LoadingSpinner({
  size = "md",
  message,
}: LoadingSpinnerProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12">
      <div
        className={`animate-spin rounded-full border-2 border-gray-300 border-t-primary-600 ${sizeClasses[size]}`}
      />
      {message && <p className="text-sm text-gray-500">{message}</p>}
    </div>
  );
}
