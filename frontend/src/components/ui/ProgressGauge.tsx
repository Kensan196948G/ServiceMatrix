/**
 * SLA進捗ゲージコンポーネント
 * SVG円グラフによるSLA達成率・経過率の視覚表示
 */

interface ProgressGaugeProps {
  /** 進捗率（0-100） */
  value: number;
  /** ゲージ直径（px） */
  size?: number;
  /** 線の太さ（px） */
  strokeWidth?: number;
  /** ラベルテキスト（中央に表示） */
  label?: string;
}

/** 値に応じた色を返す（高い=緑、70%以上=黄、90%以上=赤） */
function getGaugeColor(value: number, isComplianceRate: boolean): string {
  if (isComplianceRate) {
    // コンプライアンス率: 高い方が良い
    if (value >= 90) return "#10b981"; // green-500
    if (value >= 70) return "#f59e0b"; // amber-500
    return "#ef4444"; // red-500
  }
  // 経過率: 低い方が良い
  if (value >= 90) return "#ef4444";
  if (value >= 70) return "#f59e0b";
  return "#10b981";
}

export default function ProgressGauge({
  value,
  size = 120,
  strokeWidth = 10,
  label,
}: ProgressGaugeProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const clampedValue = Math.min(Math.max(value, 0), 100);
  const offset = circumference - (clampedValue / 100) * circumference;

  // label に "達成" が含まれる場合はコンプライアンス率と判定
  const isComplianceRate = label ? label.includes("達成") : value <= 100;
  const color = getGaugeColor(clampedValue, isComplianceRate);

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          {/* 背景円 */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="#e5e7eb"
            strokeWidth={strokeWidth}
          />
          {/* 進捗円 */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className="transition-all duration-500 ease-out"
          />
        </svg>
        {/* 中央テキスト */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-xl font-bold text-gray-900">
            {clampedValue.toFixed(1)}%
          </span>
        </div>
      </div>
      {label && (
        <span className="mt-1 text-xs font-medium text-gray-500">{label}</span>
      )}
    </div>
  );
}
