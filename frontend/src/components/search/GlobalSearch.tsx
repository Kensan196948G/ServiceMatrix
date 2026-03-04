'use client';

/**
 * GlobalSearch - Ctrl+K または / キーで開くモーダル検索ダイアログ
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  AlertCircle,
  AlertTriangle,
  GitBranch,
  Server,
  Search,
  X,
  Loader2,
} from 'lucide-react';

interface SearchResultItem {
  id: string;
  title: string;
  status?: string;
  ci_type?: string;
  type: 'incident' | 'problem' | 'change' | 'cmdb';
}

interface SearchResults {
  query: string;
  total: number;
  results: {
    incidents?: SearchResultItem[];
    problems?: SearchResultItem[];
    changes?: SearchResultItem[];
    cmdb?: SearchResultItem[];
  };
}

const GROUP_META = {
  incidents: {
    label: 'インシデント',
    icon: AlertCircle,
    color: 'text-red-500',
    bg: 'bg-red-50',
    href: (id: string) => `/incidents/${id}`,
  },
  problems: {
    label: '問題',
    icon: AlertTriangle,
    color: 'text-orange-500',
    bg: 'bg-orange-50',
    href: (id: string) => `/problems/${id}`,
  },
  changes: {
    label: '変更',
    icon: GitBranch,
    color: 'text-blue-500',
    bg: 'bg-blue-50',
    href: (id: string) => `/changes/${id}`,
  },
  cmdb: {
    label: 'CMDB',
    icon: Server,
    color: 'text-green-500',
    bg: 'bg-green-50',
    href: (id: string) => `/cmdb/${id}`,
  },
} as const;

type GroupKey = keyof typeof GROUP_META;

interface GlobalSearchProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function GlobalSearch({ isOpen, onClose }: GlobalSearchProps) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResults | null>(null);
  const [activeIndex, setActiveIndex] = useState(-1);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // フラットな結果リスト（キーボードナビ用）
  const flatItems: { href: string; item: SearchResultItem }[] = [];
  if (results) {
    for (const key of Object.keys(GROUP_META) as GroupKey[]) {
      const items = results.results[key] ?? [];
      for (const item of items) {
        flatItems.push({ href: GROUP_META[key].href(item.id), item });
      }
    }
  }

  // モーダルが開いたときにフォーカス
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQuery('');
      setResults(null);
      setActiveIndex(-1);
    }
  }, [isOpen]);

  const fetchResults = useCallback(async (q: string) => {
    if (q.length < 2) {
      setResults(null);
      return;
    }
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'}/api/v1/search?q=${encodeURIComponent(q)}&limit=5`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (res.ok) {
        setResults(await res.json());
      }
    } catch {
      // ネットワークエラーは無視
    } finally {
      setLoading(false);
    }
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setQuery(val);
    setActiveIndex(-1);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchResults(val), 300);
  };

  const navigate = useCallback(
    (href: string) => {
      router.push(href);
      onClose();
    },
    [router, onClose]
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
      return;
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, flatItems.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, -1));
    } else if (e.key === 'Enter' && activeIndex >= 0) {
      e.preventDefault();
      navigate(flatItems[activeIndex].href);
    }
  };

  if (!isOpen) return null;

  const hasResults = results && results.total > 0;
  const noResults = results && results.total === 0 && query.length >= 2 && !loading;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh] px-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Dialog */}
      <div
        className="relative w-full max-w-xl rounded-xl bg-white shadow-2xl ring-1 ring-gray-200 overflow-hidden"
        onKeyDown={handleKeyDown}
      >
        {/* Search Input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-100">
          {loading ? (
            <Loader2 className="h-4 w-4 text-gray-400 animate-spin flex-shrink-0" />
          ) : (
            <Search className="h-4 w-4 text-gray-400 flex-shrink-0" />
          )}
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={handleChange}
            placeholder="インシデント、変更、CI名などを検索..."
            className="flex-1 text-sm text-gray-800 placeholder-gray-400 focus:outline-none"
          />
          {query && (
            <button
              onClick={() => { setQuery(''); setResults(null); inputRef.current?.focus(); }}
              className="rounded p-0.5 text-gray-400 hover:text-gray-600"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
          <kbd className="hidden sm:inline text-[11px] text-gray-400 border border-gray-200 rounded px-1.5 py-0.5">
            Esc
          </kbd>
        </div>

        {/* Results */}
        {hasResults && (
          <div className="max-h-[60vh] overflow-y-auto py-2">
            {(Object.keys(GROUP_META) as GroupKey[]).map((key) => {
              const items = results.results[key];
              if (!items || items.length === 0) return null;
              const meta = GROUP_META[key];
              const Icon = meta.icon;
              return (
                <div key={key} className="mb-2">
                  <div className="px-4 py-1 text-[11px] font-semibold uppercase tracking-wide text-gray-400">
                    {meta.label}
                  </div>
                  {items.map((item) => {
                    const globalIdx = flatItems.findIndex((f) => f.item.id === item.id && f.item.type === item.type);
                    const isActive = globalIdx === activeIndex;
                    return (
                      <button
                        key={item.id}
                        onClick={() => navigate(meta.href(item.id))}
                        className={`flex w-full items-center gap-3 px-4 py-2.5 text-left transition-colors ${
                          isActive ? 'bg-blue-50' : 'hover:bg-gray-50'
                        }`}
                      >
                        <span className={`flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-md ${meta.bg}`}>
                          <Icon className={`h-3.5 w-3.5 ${meta.color}`} />
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium text-gray-800">{item.title}</p>
                          {item.status && (
                            <p className="text-xs text-gray-400">{item.status}</p>
                          )}
                          {item.ci_type && (
                            <p className="text-xs text-gray-400">{item.ci_type}</p>
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>
              );
            })}
          </div>
        )}

        {noResults && (
          <div className="py-10 text-center text-sm text-gray-400">
            「{query}」に一致する結果が見つかりませんでした
          </div>
        )}

        {!query && (
          <div className="py-8 text-center text-sm text-gray-400">
            キーワードを入力してください（2文字以上）
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center gap-4 border-t border-gray-100 px-4 py-2 text-[11px] text-gray-400">
          <span><kbd className="border border-gray-200 rounded px-1">↑↓</kbd> 移動</span>
          <span><kbd className="border border-gray-200 rounded px-1">Enter</kbd> 開く</span>
          <span><kbd className="border border-gray-200 rounded px-1">Esc</kbd> 閉じる</span>
        </div>
      </div>
    </div>
  );
}
