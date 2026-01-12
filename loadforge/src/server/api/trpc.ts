import { initTRPC } from "@trpc/server";
import superjson from "superjson";
import { ZodError } from "zod";
import { eventBind } from "../socket/events.bind";
import { onPhaseComplete } from "../socket/phase.complete";
import { onTestComplete } from "../socket/test.complete";
import { db } from "../db/index";

eventBind();
onPhaseComplete();
onTestComplete();
export const createTRPCContext = async (opts: { headers: Headers }) => {
  return {
    ...opts,
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
