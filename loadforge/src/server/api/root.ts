import { createCallerFactory, createTRPCRouter } from "~/server/api/trpc"
import { loadTestRouter } from "~/server/api/routers/loadtest"
import { settingsRouter } from "~/server/api/routers/settings"
import { testsRouter } from "./routers/test.events"

export const appRouter = createTRPCRouter({
  loadTest: loadTestRouter,
  settings: settingsRouter,
  test: testsRouter,
})

export type AppRouter = typeof appRouter

export const createCaller = createCallerFactory(appRouter)
