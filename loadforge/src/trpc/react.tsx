"use client"

import React, { useState } from "react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { createTRPCReact } from "@trpc/react-query"
import { loggerLink, splitLink, httpBatchLink, wsLink, createWSClient } from "@trpc/client"
import superjson from "superjson"
import type { AppRouter } from "~/server/api/root"

export const api = createTRPCReact<AppRouter>()

const createQueryClient = () => new QueryClient()

let clientQueryClientSingleton: QueryClient | undefined = undefined
const getQueryClient = () => {
  if (typeof window === "undefined") {
    return createQueryClient()
  }
  return clientQueryClientSingleton ??= createQueryClient()
}

// --- Create a WebSocket client for subscriptions ---
const wsClient = createWSClient({
  url: "ws://localhost:3001"
  
})
const wsLinkWithTransformer = wsLink({
  client: wsClient,
  transformer: superjson, // <-- must match your router
});

export function TRPCReactProvider(props: { children: React.ReactNode }) {
  const queryClient = getQueryClient()

  const [trpcClient] = useState(() =>
    api.createClient({
      links: [
        loggerLink({
          enabled: (op) =>
            process.env.NODE_ENV === "development" || (op.direction === "down" && op.result instanceof Error),
        }),
        // --- split between HTTP and WS ---
        splitLink({
          condition(op) {
            return op.type === "subscription"
          },
          true: wsLinkWithTransformer,
          false: httpBatchLink({
            url: getBaseUrl() + "/api/trpc",
            transformer: superjson,
            headers: () => {
              const headers = new Headers()
              headers.set("x-trpc-source", "nextjs-react")
              return headers
            },
          }),
        }),
      ],
    }),
  )

  return (
    <QueryClientProvider client={queryClient}>
      <api.Provider client={trpcClient} queryClient={queryClient}>
        {props.children}
      </api.Provider>
    </QueryClientProvider>
  )
}

function getBaseUrl() {
  if (typeof window !== "undefined") return window.location.origin
  if (process.env.VERCEL_URL) return `https://${process.env.VERCEL_URL}`
  return `http://localhost:${process.env.PORT ?? 3000}`
}
