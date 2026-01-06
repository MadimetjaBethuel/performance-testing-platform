import { createCallerFactory, createTRPCRouter } from "~/server/api/trpc"
import { loadTestRouter } from "~/server/api/routers/loadtest"
import { settingsRouter } from "~/server/api/routers/settings"

export const appRouter = createTRPCRouter({
  loadTest: loadTestRouter,
  settings: settingsRouter,
})

export type AppRouter = typeof appRouter

export const createCaller = createCallerFactory(appRouter)
