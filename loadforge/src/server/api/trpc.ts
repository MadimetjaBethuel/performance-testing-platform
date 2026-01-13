import { initTRPC } from "@trpc/server";
import superjson from "superjson";
import { ZodError } from "zod";
import { eventBind } from "../socket/events.bind";
import { onPhaseComplete } from "../socket/phase.complete";
import { onTestComplete } from "../socket/test.complete";
import { db } from "../db/index";
import { CreateWSSContextFnOptions } from "@trpc/server/adapters/ws";
import { type CreateNextContextOptions } from "@trpc/server/adapters/next";
import type { IncomingHttpHeaders } from "http";

eventBind();
onPhaseComplete();
onTestComplete();
export const createWSContext = async (opts: CreateWSSContextFnOptions) => {
  // Try to extract HTTP headers from available fields (req or connection), fallback to empty object
  const headers: IncomingHttpHeaders = (opts as any)?.req?.headers ?? (opts as any)?.connection?.headers ?? {};
  return {
    headers,
    db,
  };
};
export const createTRPCContext = async (opts: CreateNextContextOptions | { headers?: any } = {}) => {
  // Accept either the Next.js context (with req.headers) or a simple object with headers
  const headers = (opts as any)?.req?.headers ?? (opts as any)?.headers ?? {};
  return {
    headers,
    db,
  };
};

const t = initTRPC.context<typeof createTRPCContext>().create({
  transformer: superjson,
  errorFormatter({ shape, error }) {
    return {
      ...shape,
      data: {
        ...shape.data,
        zodError:
          error.cause instanceof ZodError ? error.cause.flatten() : null,
      },
    };
  },
});

export const createCallerFactory = t.createCallerFactory;
export const createTRPCRouter = t.router;
export const publicProcedure = t.procedure;
