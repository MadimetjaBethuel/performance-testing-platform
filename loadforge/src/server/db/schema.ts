import { sql } from "drizzle-orm"
import { pgTableCreator, serial, varchar, text, timestamp, integer, jsonb } from "drizzle-orm/pg-core"

export const createTable = pgTableCreator((name) => `loadforge_${name}`)

export const loadTests = createTable("load_test", {
  id: serial("id").primaryKey(),
  name: varchar("name", { length: 256 }).notNull(),
  urls: jsonb("urls").notNull(), // Array of URL strings
  concurrencyPattern: jsonb("concurrency_pattern").notNull(), // Array of concurrency values
  duration: integer("duration").notNull(), // in seconds
  rampUpTime: integer("ramp_up_time").notNull(), // in seconds
  rampDownTime: integer("ramp_down_time").notNull(), // in seconds
  status: varchar("status", { length: 50 }).default("pending").notNull(), // pending, running, completed, failed
  createdAt: timestamp("created_at").default(sql`CURRENT_TIMESTAMP`).notNull(),
  completedAt: timestamp("completed_at"),
})

export const testResults = createTable("test_result", {
  id: serial("id").primaryKey(),
  testId: integer("test_id").references(() => loadTests.id),
  totalRequests: integer("total_requests").notNull(),
  successfulRequests: integer("successful_requests").notNull(),
  failedRequests: integer("failed_requests").notNull(),
  avgResponseTime: integer("avg_response_time").notNull(), // in ms
  minResponseTime: integer("min_response_time").notNull(),
  maxResponseTime: integer("max_response_time").notNull(),
  p50ResponseTime: integer("p50_response_time").notNull(),
  p95ResponseTime: integer("p95_response_time").notNull(),
  p99ResponseTime: integer("p99_response_time").notNull(),
  requestsPerSecond: integer("requests_per_second").notNull(),
  urlBreakdown: jsonb("url_breakdown").notNull(), // Per-URL metrics
  phaseMetrics: jsonb("phase_metrics").notNull(), // Ramp-up, steady, ramp-down metrics
  createdAt: timestamp("created_at").default(sql`CURRENT_TIMESTAMP`).notNull(),
})

export const settings = createTable("setting", {
  id: serial("id").primaryKey(),
  key: varchar("key", { length: 256 }).notNull().unique(),
  value: text("value").notNull(),
  updatedAt: timestamp("updated_at").default(sql`CURRENT_TIMESTAMP`).notNull(),
})
