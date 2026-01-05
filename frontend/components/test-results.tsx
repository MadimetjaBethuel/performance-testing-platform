"use client"

import { useState } from "react"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  Legend,
} from "recharts"
import { Download, Calendar, Clock, Target, TrendingUp, AlertTriangle } from "lucide-react"

export function TestResults() {
  const [selectedTest, setSelectedTest] = useState<string | null>("test-1")

  // Mock data - would come from your Python backend
  const tests = [
    {
      id: "test-1",
      timestamp: "2025-01-09T14:30:00Z",
      duration: 3600,
      totalRequests: 45234,
      successCount: 44657,
      errorCount: 577,
      successRate: 98.7,
      avgResponseTime: 245,
      minResponseTime: 89,
      maxResponseTime: 1240,
      percentiles: { p50: 210, p90: 420, p95: 580, p99: 890 },
      urlsCount: 6,
      concurrencyPattern: [1000, 3000, 5000, 10000, 5000],
    },
    {
      id: "test-2",
      timestamp: "2025-01-08T10:15:00Z",
      duration: 3600,
      totalRequests: 43891,
      successCount: 42675,
      errorCount: 1216,
      successRate: 97.2,
      avgResponseTime: 280,
      minResponseTime: 95,
      maxResponseTime: 1580,
      percentiles: { p50: 230, p90: 480, p95: 650, p99: 1020 },
      urlsCount: 6,
      concurrencyPattern: [1000, 3000, 5000, 10000, 5000],
    },
  ]

  // Mock per-URL data
  const perUrlMetrics = [
    {
      url: "https://gpglook.gauteng.gov.za:443/Pages/wall-of-history.aspx",
      requests: 7542,
      successRate: 98.9,
      avgResponseTime: 220,
    },
    {
      url: "https://gpglook.gauteng.gov.za:443/Pages/videos.aspx",
      requests: 7523,
      successRate: 98.5,
      avgResponseTime: 245,
    },
    {
      url: "https://gpglook.gauteng.gov.za:443/Pages/test-page.aspx",
      requests: 7498,
      successRate: 97.8,
      avgResponseTime: 280,
    },
    {
      url: "https://gpglook.gauteng.gov.za:443/Pages/speeches.aspx",
      requests: 7556,
      successRate: 99.2,
      avgResponseTime: 210,
    },
    {
      url: "https://gpglook.gauteng.gov.za:443/Pages/services.aspx",
      requests: 7589,
      successRate: 98.3,
      avgResponseTime: 250,
    },
    {
      url: "https://gpglook.gauteng.gov.za:443/Pages/search-box.aspx",
      requests: 7526,
      successRate: 97.5,
      avgResponseTime: 270,
    },
  ]

  // Mock phase data for charts
  const phaseData = [
    { phase: "Phase 1", concurrency: 1000, requests: 8500, avgTime: 180, successRate: 99.5 },
    { phase: "Phase 2", concurrency: 3000, requests: 9200, avgTime: 210, successRate: 99.1 },
    { phase: "Phase 3", concurrency: 5000, requests: 9800, avgTime: 250, successRate: 98.8 },
    { phase: "Phase 4", concurrency: 10000, requests: 10100, avgTime: 320, successRate: 97.2 },
    { phase: "Phase 5", concurrency: 5000, requests: 7634, avgTime: 240, successRate: 99.0 },
  ]

  const currentTest = tests.find((t) => t.id === selectedTest) || tests[0]

  const handleExportResults = () => {
    const data = JSON.stringify(
      {
        test: currentTest,
        perUrlMetrics,
        phaseData,
      },
      null,
      2,
    )
    const blob = new Blob([data], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `test-results-${currentTest.id}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="container mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold mb-2 text-balance">Test Results</h1>
          <p className="text-muted-foreground">Analyze performance metrics and identify bottlenecks</p>
        </div>
        <Button onClick={handleExportResults}>
          <Download className="h-4 w-4 mr-2" />
          Export Results
        </Button>
      </div>

      {/* Test Selector */}
      <div className="mb-6 flex gap-2 overflow-x-auto pb-2">
        {tests.map((test) => (
          <Button
            key={test.id}
            onClick={() => setSelectedTest(test.id)}
            variant={selectedTest === test.id ? "default" : "outline"}
            className="flex-shrink-0"
          >
            <Calendar className="h-4 w-4 mr-2" />
            {new Date(test.timestamp).toLocaleDateString()}
          </Button>
        ))}
      </div>

      {/* Summary Cards */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4 mb-8">
        <Card className="p-6 border-border bg-card">
          <div className="flex items-start justify-between mb-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <Target className="h-5 w-5 text-primary" />
            </div>
            <Badge variant={currentTest.successRate >= 95 ? "secondary" : "destructive"}>
              {currentTest.successRate}%
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mb-1">Success Rate</p>
          <p className="text-2xl font-bold">
            {currentTest.successCount.toLocaleString()} / {currentTest.totalRequests.toLocaleString()}
          </p>
        </Card>

        <Card className="p-6 border-border bg-card">
          <div className="flex items-start justify-between mb-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-chart-2/10">
              <Clock className="h-5 w-5 text-chart-2" />
            </div>
          </div>
          <p className="text-sm text-muted-foreground mb-1">Avg Response Time</p>
          <p className="text-2xl font-bold">{currentTest.avgResponseTime}ms</p>
          <p className="text-xs text-muted-foreground mt-1">
            Range: {currentTest.minResponseTime}ms - {currentTest.maxResponseTime}ms
          </p>
        </Card>

        <Card className="p-6 border-border bg-card">
          <div className="flex items-start justify-between mb-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-chart-3/10">
              <TrendingUp className="h-5 w-5 text-chart-3" />
            </div>
          </div>
          <p className="text-sm text-muted-foreground mb-1">Total Requests</p>
          <p className="text-2xl font-bold">{currentTest.totalRequests.toLocaleString()}</p>
          <p className="text-xs text-muted-foreground mt-1">Over {(currentTest.duration / 60).toFixed(0)} minutes</p>
        </Card>

        <Card className="p-6 border-border bg-card">
          <div className="flex items-start justify-between mb-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-destructive/10">
              <AlertTriangle className="h-5 w-5 text-destructive" />
            </div>
          </div>
          <p className="text-sm text-muted-foreground mb-1">Failed Requests</p>
          <p className="text-2xl font-bold">{currentTest.errorCount.toLocaleString()}</p>
          <p className="text-xs text-muted-foreground mt-1">{(100 - currentTest.successRate).toFixed(1)}% error rate</p>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid gap-6 lg:grid-cols-2 mb-8">
        <Card className="p-6 border-border bg-card">
          <h3 className="text-lg font-semibold mb-4">Response Time by Phase</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={phaseData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="phase" stroke="hsl(var(--muted-foreground))" fontSize={12} />
              <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--popover))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "8px",
                }}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="avgTime"
                stroke="hsl(var(--chart-1))"
                name="Avg Response Time (ms)"
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        </Card>

        <Card className="p-6 border-border bg-card">
          <h3 className="text-lg font-semibold mb-4">Success Rate by Phase</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={phaseData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="phase" stroke="hsl(var(--muted-foreground))" fontSize={12} />
              <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} domain={[95, 100]} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--popover))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "8px",
                }}
              />
              <Legend />
              <Bar dataKey="successRate" fill="hsl(var(--chart-2))" name="Success Rate (%)" />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* Percentiles */}
      <Card className="p-6 border-border bg-card mb-8">
        <h3 className="text-lg font-semibold mb-4">Response Time Percentiles</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <div>
            <p className="text-sm text-muted-foreground mb-1">50th Percentile (Median)</p>
            <p className="text-3xl font-bold">{currentTest.percentiles.p50}ms</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground mb-1">90th Percentile</p>
            <p className="text-3xl font-bold">{currentTest.percentiles.p90}ms</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground mb-1">95th Percentile</p>
            <p className="text-3xl font-bold">{currentTest.percentiles.p95}ms</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground mb-1">99th Percentile</p>
            <p className="text-3xl font-bold">{currentTest.percentiles.p99}ms</p>
          </div>
        </div>
      </Card>

      {/* Per-URL Metrics Table */}
      <Card className="border-border bg-card">
        <div className="p-6 border-b border-border">
          <h2 className="text-xl font-semibold">Per-URL Performance</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="border-b border-border bg-muted/50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  URL
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Requests
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Success Rate
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Avg Response Time
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {perUrlMetrics.map((metric, index) => (
                <tr key={index} className="hover:bg-accent/50 transition-colors">
                  <td className="px-6 py-4 text-sm max-w-md truncate" title={metric.url}>
                    {metric.url}
                  </td>
                  <td className="px-6 py-4 text-sm font-mono">{metric.requests.toLocaleString()}</td>
                  <td className="px-6 py-4 text-sm">
                    <span
                      className={
                        metric.successRate >= 95
                          ? "text-chart-2"
                          : metric.successRate >= 90
                            ? "text-chart-3"
                            : "text-destructive"
                      }
                    >
                      {metric.successRate}%
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm font-mono">{metric.avgResponseTime}ms</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
