import { createTRPCRouter, publicProcedure } from "~/server/api/trpc";
import { z } from "zod";


export const dashboardRouter = createTRPCRouter({
  // Get overview metrics
  getOverview: publicProcedure.query(async ({ctx}) => {

    const tests = await ctx.db.query.completeTests.findMany({
        orderBy: (t,{desc}) => [desc(t.created_at)],
    })
    const results = await ctx.db.query.testResults.findMany()


     const totalTests = tests.length;
    const avgResponseTime = results.length
      ? Math.round(results.reduce((s, r) => s + r.avg_response_time, 0) / results.length)
      : 0;
    const totalRequests = results.reduce((s, r) => s + r.total_requests, 0);
    const successfulRequests = results.reduce((s, r) => s + r.successful_requests, 0);
    const failedRequests = results.reduce((s, r) => s + r.failed_requests, 0);
    const successRate = totalRequests ? Number(((successfulRequests / totalRequests) * 100).toFixed(1)) : 0;

    const recentTests = tests.slice(0, 5).map((t) => {
      const r = results.find((res) => res.test_id === t.id);
      return {
        id: t.id,
        name: t.name,
        status: t.status,
        duration: t.duration,
        requests: r?.total_requests ?? 0,
        successRate: r && r.total_requests ? Number(((r.successful_requests / r.total_requests) * 100).toFixed(1)) : null,
        createdAt: t.created_at?.toISOString?.() ?? null,
      };
    });
    return {
        metrics:{
        totalTests,
        avgResponseTime,
        successRate,
        failedRequests,
      },
      recentTests,  
        }
   }),
});