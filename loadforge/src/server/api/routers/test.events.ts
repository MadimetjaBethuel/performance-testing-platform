import { observable } from "@trpc/server/observable";
import { subscribe } from "../../socket/eventbus";
import { tracked } from "@trpc/server";
import { getSocket } from "../../socket/engine.socket";
import { createTRPCRouter, publicProcedure } from "../trpc";
import EventEmitter, { on } from "events";
const ee = new EventEmitter();

export const testsRouter = createTRPCRouter({
  startTest: publicProcedure
    .input((v) => v as any)
    .mutation(({ input }) => {
      const socket = getSocket();
      console.log("Starting test with input:", input);
      console.log(
        "🔌 [MUTATION] Socket ID:",
        socket.id,
        "Connected:",
        socket.connected
      );
      socket.emit("start_test", { urls: input.urls });
      return { status: "Test started" };
    }),
  onProgress: publicProcedure.subscription(async function* (opts) {
    console.log("🔌 [TRPC] Client subscribed to events");

    // Create a promise-based queue
    let pendingResolve: ((value: any) => void) | null = null;
    const queue: any[] = [];

    const unsubscribe = subscribe((event) => {
      console.log("📥 [TRPC] Event received from bus:", event);

      // Filter by event types if specified
      if (
        opts.input?.eventTypes &&
        !opts.input.eventTypes.includes(event.type)
      ) {
        console.log("⏭️ [TRPC] Event filtered out");
        return;
      }

      // If someone is waiting, resolve immediately
      if (pendingResolve) {
        console.log("📤 [TRPC] Resolving pending promise with event");
        pendingResolve(event);
        pendingResolve = null;
      } else {
        // Otherwise add to queue
        console.log(
          "📦 [TRPC] Adding to queue, queue length:",
          queue.length + 1
        );
        queue.push(event);
      }
    });

    console.log("✅ [TRPC] Event listener registered");

    try {
      while (!opts.signal?.aborted) {
        // Get event from queue or wait for next one
        let event: any;

        if (queue.length > 0) {
          event = queue.shift()!;
          console.log(
            "📤 [TRPC] Got event from queue, remaining:",
            queue.length
          );
        } else {
          console.log("⏳ [TRPC] Waiting for next event...");
          event = await new Promise<any>((resolve) => {
            pendingResolve = resolve;

            // Handle abort while waiting
            if (opts.signal?.aborted) {
              resolve(null);
            }
          });
        }

        if (!event || opts.signal?.aborted) {
          console.log("🛑 [TRPC] Stopping subscription");
          break;
        }

        const eventId = event.id || `${event.type}-${Date.now()}`;
        console.log("✅ [TRPC] Yielding event to client:", eventId);
        yield tracked(eventId, event);
      }
    } finally {
      unsubscribe();
      console.log("🔌 [TRPC] Unsubscribed from event bus");
    }
  }),
});
