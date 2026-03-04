'use client'

import dynamic from 'next/dynamic'
import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Link from 'next/link'
import { CalendarDays, List, X } from 'lucide-react'
import apiClient from '@/lib/api'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import type { EventClickArg, EventDropArg } from '@fullcalendar/core'
import type { EventResizeDoneArg } from '@fullcalendar/interaction'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import interactionPlugin from '@fullcalendar/interaction'

const FullCalendar = dynamic(() => import('@fullcalendar/react'), { ssr: false })

interface RawCalendarEvent {
  id: string
  title: string
  start: string | null
  end: string | null
  status: string
  color: string
  extendedProps: {
    change_number: string
    change_type: string
    risk_level: string | null
    assigned_to: string | null
    requested_by: string | null
  }
}

interface CalendarEvent {
  id: string
  title: string
  start: string | undefined
  end: string | undefined
  status: string
  color: string
  extendedProps: RawCalendarEvent['extendedProps']
}

interface SelectedEvent {
  id: string
  title: string
  start: string | null
  end: string | null
  extendedProps: RawCalendarEvent['extendedProps']
}

export default function CalendarPage() {
  const queryClient = useQueryClient()
  const [selectedEvent, setSelectedEvent] = useState<SelectedEvent | null>(null)

  const { data: events, isLoading } = useQuery<CalendarEvent[]>({
    queryKey: ['changes-calendar'],
    queryFn: () =>
      apiClient.get<RawCalendarEvent[]>('/changes/calendar').then(r =>
        r.data.map(e => ({
          ...e,
          start: e.start ?? undefined,
          end: e.end ?? undefined,
        }))
      ),
  })

  const rescheduleMutation = useMutation({
    mutationFn: ({ id, start, end }: { id: string; start: string; end: string | null }) =>
      apiClient.patch(`/changes/${id}/reschedule`, {
        scheduled_start: start,
        scheduled_end: end,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['changes-calendar'] })
    },
  })

  const handleEventClick = useCallback((info: EventClickArg) => {
    const ep = info.event.extendedProps as RawCalendarEvent['extendedProps']
    setSelectedEvent({
      id: info.event.id,
      title: info.event.title,
      start: info.event.start?.toISOString() ?? null,
      end: info.event.end?.toISOString() ?? null,
      extendedProps: ep,
    })
  }, [])

  const handleEventDrop = useCallback(
    (info: EventDropArg) => {
      const { id, start, end } = info.event
      if (!start) { info.revert(); return }
      rescheduleMutation.mutate(
        { id, start: start.toISOString(), end: end?.toISOString() ?? null },
        { onError: () => info.revert() }
      )
    },
    [rescheduleMutation]
  )

  const handleEventResize = useCallback(
    (info: EventResizeDoneArg) => {
      const { id, start, end } = info.event
      if (!start) { info.revert(); return }
      rescheduleMutation.mutate(
        { id, start: start.toISOString(), end: end?.toISOString() ?? null },
        { onError: () => info.revert() }
      )
    },
    [rescheduleMutation]
  )

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <CalendarDays className="h-5 w-5 text-blue-500" />
            変更カレンダー
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">承認済み・スケジュール済み変更の一覧</p>
        </div>
        <Link
          href="/changes"
          className="inline-flex items-center gap-1.5 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50"
        >
          <List className="h-4 w-4" />
          変更一覧
        </Link>
      </div>

      <div className="flex items-center gap-4 rounded-lg border border-gray-200 bg-white px-4 py-2 shadow-sm text-xs text-gray-600">
        <span className="font-medium">凡例:</span>
        <span className="flex items-center gap-1.5">
          <span className="h-3 w-3 rounded-full bg-blue-500 inline-block" />Approved
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-3 w-3 rounded-full bg-violet-500 inline-block" />Scheduled
        </span>
        <span className="ml-auto text-gray-400">イベントをドラッグして日程変更できます</span>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        {isLoading ? (
          <div className="flex h-96 items-center justify-center"><LoadingSpinner size="lg" /></div>
        ) : (
          <FullCalendar
            plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
            initialView="dayGridMonth"
            headerToolbar={{ left: 'prev,next today', center: 'title', right: 'dayGridMonth,timeGridWeek' }}
            locale="ja"
            events={events ?? []}
            editable={true}
            droppable={true}
            eventClick={handleEventClick}
            eventDrop={handleEventDrop}
            eventResize={handleEventResize}
            height="auto"
            buttonText={{ today: '今日', month: '月', week: '週' }}
          />
        )}
      </div>

      {selectedEvent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-2xl">
            <div className="flex items-start justify-between mb-4">
              <h2 className="text-base font-bold text-gray-900 pr-4">{selectedEvent.title}</h2>
              <button onClick={() => setSelectedEvent(null)} className="rounded-full p-1 hover:bg-gray-100 text-gray-400">
                <X className="h-4 w-4" />
              </button>
            </div>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-gray-500">変更番号</dt>
                <dd className="font-mono font-medium">{selectedEvent.extendedProps.change_number}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">タイプ</dt>
                <dd>{selectedEvent.extendedProps.change_type}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">リスクレベル</dt>
                <dd>{selectedEvent.extendedProps.risk_level ?? '-'}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">開始</dt>
                <dd>{selectedEvent.start ? new Date(selectedEvent.start).toLocaleString('ja-JP') : '-'}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">終了</dt>
                <dd>{selectedEvent.end ? new Date(selectedEvent.end).toLocaleString('ja-JP') : '-'}</dd>
              </div>
            </dl>
            <div className="mt-5 flex justify-end gap-2">
              <Link
                href={`/changes/${selectedEvent.id}`}
                className="rounded-md bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
                onClick={() => setSelectedEvent(null)}
              >
                詳細を開く
              </Link>
              <button
                onClick={() => setSelectedEvent(null)}
                className="rounded-md border border-gray-300 px-4 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                閉じる
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
