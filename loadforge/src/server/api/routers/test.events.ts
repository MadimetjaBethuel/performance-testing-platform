import { subscribe } from "../../socket/eventbus";
import { tracked } from "@trpc/server";
import { getSocket } from "../../socket/engine.socket";
import { createTRPCRouter, publicProcedure } from "../trpc";
import { z } from "zod";
import { completeTests, testPhases, testResults } from "../../db/schema";
import { v4 as uuidv4 } from "uuid";
const DEFAULT_USER_ID = "default-user-001";

export const testsRouter = createTRPCRouter({
  startTest: publicProcedure
    .input(
      z.object({
        urls: z.array(z.string().url()),
        concurrency: z.array(z.number().positive()),
        phase_length: z.number().positive(),
        ramp_up_time: z.number().min(0),
        ramp_down_time: z.number().min(0),
        hold_duration: z.number().min(0),
        total_duration: z.number().positive(),
        name: z.string().optional(),
      })
    )
    .mutation(async ({ input, ctx }) => {
      const socket = getSocket();

      if (!socket.connected) {
        throw new Error(
          "Socket not connected. PLease ensure the backend is running ."
        );
      }
      console.log(
        "🔌 [MUTATION] Socket ID:",
        socket.id,
        "Connected:",
        socket.connected
      );
      const id = uuidv4();

      try {
        await ctx.db.insert(completeTests).values({
          id: id.toString(),
          user_id: DEFAULT_USER_ID,
          name: input.name || "Load test for now",
          urls: input.urls,
          concurrency_pattern: input.concurrency,
          duration: input.total_duration,
          ramp_up_time: input.ramp_up_time,
          ramp_down_time: input.ramp_down_time,
          status: "running",
        });

        socket.emit("start_test", {
          urls: input.urls,
          concurrency: input.concurrency,
          phase_length: input.phase_length,
          test_id: id,
        });

        return {
          status: "Test Started",
          test_id: id,
        };
      } catch (error) {
        console.log("Failed to start test");
        throw new Error(
          "Failed to start test. please check db connection or socket connection"
        );
      }

      return { status: "Test started" };
    }),
  onProgress: publicProcedure.subscription(async function* (opts) {
    console.log("🔌 [TRPC] Client subscribed to events");

    // Create a promise-based queue
    let pendingResolve: ((value: any) => void) | null = null;
    const queue: any[] = [];

    const unsubscribe = subscribe((event) => {
      console.log("🔥 [TRPC] Eventbus callback triggered with event:", event);
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
