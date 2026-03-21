import { useEffect, useRef, useCallback } from "react"
import { fetchEventSource } from "@microsoft/fetch-event-source"

import { OpenAPI } from "@/client"

export type SSEEventHandler = (eventType: string, data: unknown) => void

interface UseSSEOptions {
  onEvent?: SSEEventHandler
  onOpen?: () => void
  onClose?: () => void
  onError?: (error: unknown) => void
  enabled?: boolean
}

/**
 * Subscribe to a Server-Sent Events endpoint.
 * Carries the Authorization header (native EventSource doesn't support it).
 * Auto-reconnects on transient errors; stops on terminal events.
 */
export function useSSE(url: string | null, options: UseSSEOptions = {}) {
  const { onEvent, onOpen, onClose, onError, enabled = true } = options
  const abortRef = useRef<AbortController | null>(null)
  const stableOnEvent = useRef(onEvent)
  const stableOnOpen = useRef(onOpen)
  const stableOnClose = useRef(onClose)
  const stableOnError = useRef(onError)

  // Keep refs up-to-date without restarting the connection
  stableOnEvent.current = onEvent
  stableOnOpen.current = onOpen
  stableOnClose.current = onClose
  stableOnError.current = onError

  const stop = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
  }, [])

  useEffect(() => {
    if (!url || !enabled) return

    const token = localStorage.getItem("access_token")
    const controller = new AbortController()
    abortRef.current = controller

    const baseUrl =
      typeof OpenAPI.BASE === "string" ? OpenAPI.BASE : "http://localhost:8000"
    const fullUrl = url.startsWith("http") ? url : `${baseUrl}${url}`

    fetchEventSource(fullUrl, {
      headers: {
        Authorization: token ? `Bearer ${token}` : "",
        Accept: "text/event-stream",
      },
      signal: controller.signal,

      onopen: async (response) => {
        if (!response.ok) {
          throw new Error(`SSE open failed: ${response.status}`)
        }
        stableOnOpen.current?.()
      },

      onmessage: (ev) => {
        try {
          const data = JSON.parse(ev.data)
          stableOnEvent.current?.(ev.event || "message", data)

          // Stop listening on terminal events
          if (ev.event === "workflow_done" || ev.event === "workflow_error") {
            stop()
            stableOnClose.current?.()
          }
        } catch {
          // non-JSON keepalive; ignore
        }
      },

      onerror: (err) => {
        stableOnError.current?.(err)
        // Return undefined to let fetchEventSource retry automatically
      },

      onclose: () => {
        stableOnClose.current?.()
      },
    })

    return () => {
      controller.abort()
    }
  }, [url, enabled, stop])

  return { stop }
}
