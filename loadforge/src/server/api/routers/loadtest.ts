// loadforge/src/server/api/routers/loadtest.ts
import { z } from "zod"
import { createTRPCRouter, publicProcedure } from "~/server/api/trpc"
import { testResults, completeTests } from "~/server/db/schema" // Import your schema tables
import { eq } from "drizzle-orm" // Import eq for equality comparisons

export const loadTestRouter = createTRPCRouter({
  // Get all load tests
  getAll: publicProcedure.query(async () => {
    // TODO: Replace with actual database query
    return [
      {
        id: 1,
        name: "Homepage Performance Test",
        status: "completed",
        createdAt: new Date(),
        duration: 300,
        successRate: 99.2,
      },
      {
        id: 2,
        name: "API Endpoint Stress Test",
        status: "completed",
        createdAt: new Date(Date.now() - 86400000),
        duration: 600,
        successRate: 98.5,
      },
    ]
  }),

  // Get test by ID
  getById: publicProcedure.input(z.object({ id: z.number() })).query(async ({ input }) => {
    // TODO: Replace with actual database query
    return {
      id: input.id,
      name: "Homepage Performance Test",
      urls: ["https://example.com", "https://example.com/api"],
      concurrencyPattern: [10, 50, 100, 50, 10],
      duration: 300,
      status: "completed",
    }
  }),

  // Create new load test
  create: publicProcedure
    .input(
      z.object({
        name: z.string().min(1),
        urls: z.array(z.string().url()),
        concurrencyPattern: z.array(z.number().positive()),
        duration: z.number().positive(),
        rampUpTime: z.number().min(0),
        rampDownTime: z.number().min(0),
      }),
    )
    .mutation(async ({ input }) => {
      // TODO: Replace with actual database mutation and trigger Python script
      console.log("[v0] Creating load test:", input)
      return {
        id: Math.floor(Math.random() * 1000),
        ...input,
        status: "pending",
        createdAt: new Date(),
      }
    }),

  // Get test results
  getResults: publicProcedure.input(z.object({ testId: z.string() })).query(async ({ ctx, input }) => {
    // We expect testId to be a string, matching the varchar type in the schema
    const result = await ctx.db.query.testResults.findFirst({
      where: eq(testResults.test_id, input.testId),
    });

    if (!result) {
      // Handle case where no results are found for the given testId
      throw new Error("Test results not found for the given test ID.");
    }

    // Since our database schema fields match the frontend interface,
    // we can directly return the result.
    // Drizzle will handle the mapping from snake_case (DB) to camelCase (JS) if configured,
    // otherwise, you might need to manually map. Assuming direct mapping for now.
    return {
      testId: result.test_id,
      totalRequests: result.total_requests,
      successfulRequests: result.successful_requests,
      failedRequests: result.failed_requests,
      avgResponseTime: result.avg_response_time,
      minResponseTime: result.min_response_time,
      maxResponseTime: result.max_response_time,
      p50ResponseTime: result.p50_response_time,
      p95ResponseTime: result.p95_response_time,
      p99ResponseTime: result.p99_response_time,
      requestsPerSecond: result.requests_per_second,
      urlBreakdown: result.url_breakdown as any, // Cast to any or define a more specific type if necessary
      phaseMetrics: result.phase_metrics as any, // Cast to any or define a more specific type if necessary
    };
  }),
})