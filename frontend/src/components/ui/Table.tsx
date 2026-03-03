/**
 * データテーブルコンポーネント
 * ITSMデータの一覧表示に使用する汎用テーブル
 */

interface Column<T> {
  /** カラムヘッダーのラベル */
  header: string;
  /** データのキー */
  accessor: keyof T | ((row: T) => React.ReactNode);
  /** カラム幅のCSSクラス */
  className?: string;
}

interface TableProps<T> {
  /** カラム定義 */
  columns: Column<T>[];
  /** テーブルデータ */
  data: T[];
  /** 行クリック時のコールバック */
  onRowClick?: (row: T) => void;
  /** データ0件時のメッセージ */
  emptyMessage?: string;
}

export default function Table<T>({
  columns,
  data,
  onRowClick,
  emptyMessage = "データがありません",
}: TableProps<T>) {
  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            {columns.map((col, i) => (
              <th
                key={i}
                className={`px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 ${col.className || ""}`}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 bg-white">
          {data.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="px-6 py-12 text-center text-sm text-gray-500"
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row, rowIndex) => (
              <tr
                key={rowIndex}
                className={
                  onRowClick
                    ? "cursor-pointer hover:bg-gray-50 transition-colors"
                    : ""
                }
                onClick={() => onRowClick?.(row)}
              >
                {columns.map((col, colIndex) => (
                  <td
                    key={colIndex}
                    className={`whitespace-nowrap px-6 py-4 text-sm text-gray-900 ${col.className || ""}`}
                  >
                    {typeof col.accessor === "function"
                      ? col.accessor(row)
                      : (row[col.accessor] as React.ReactNode) ?? "-"}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
