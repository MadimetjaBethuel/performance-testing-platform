"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "~/components/ui/card"
import { Badge } from "~/components/ui/badge"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts"
import { CheckCircle2, Clock, TrendingUp, AlertCircle } from "lucide-react"

export function TestResults() {
  const performanceData = [
    { phase: "10 users", avgTime: 120, p95: 180, p99: 250 },
    { phase: "20 users", avgTime: 145, p95: 210, p99: 290 },
    { phase: "30 users", avgTime: 168, p95: 245, p99: 335 },
    { phase: "40 users", avgTime: 195, p95: 280, p99: 385 },
  ]

  const urlBreakdown = [
    { url: "/api/users", requests: 4820, avgTime: 142, success: 100 },
    { url: "/api/products", requests: 3650, avgTime: 168, success: 99.8 },
    { url: "/api/orders", requests: 2890, avgTime: 195, success: 98.5 },
    { url: "/api/checkout", requests: 1560, avgTime: 234, success: 97.2 },
  ]

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Test Results</h1>
            <p className="mt-1 text-sm text-gray-600">API Endpoint Stress Test • Completed 2 hours ago</p>
          </div>
          <Badge className="bg-green-100 text-green-700 hover:bg-green-200">
            <CheckCircle2 className="mr-1 h-3 w-3" />
            Success
          </Badge>
        </div>
      </div>

      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { title: "Total Requests", value: "15,240", icon: TrendingUp, color: "text-purple-600" },
          { title: "Avg Response Time", value: "168ms", icon: Clock, color: "text-blue-600" },
          { title: "Success Rate", value: "99.8%", icon: CheckCircle2, color: "text-green-600" },
          { title: "Errors", value: "28", icon: AlertCircle, color: "text-red-600" },
        ].map((metric) => {
          const Icon = metric.icon
          return (
            <Card key={metric.title} className="border-gray-200">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-gray-600">{metric.title}</CardTitle>
                <Icon className={`h-4 w-4 ${metric.color}`} />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-gray-900">{metric.value}</div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      <div className="mb-6">
        <Card className="border-gray-200">
          <CardHeader>
            <CardTitle className="text-gray-900">Response Times by Phase</CardTitle>
            <CardDescription className="text-gray-600">Performance metrics across concurrency levels</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={performanceData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="phase" stroke="#6b7280" />
                <YAxis stroke="#6b7280" />
                <Tooltip
                  contentStyle={{ backgroundColor: "#ffffff", border: "1px solid #e5e7eb", borderRadius: "8px" }}
                />
                <Legend />
                <Line type="monotone" dataKey="avgTime" stroke="#9333ea" name="Average" strokeWidth={2} />
                <Line type="monotone" dataKey="p95" stroke="#6366f1" name="P95" strokeWidth={2} />
                <Line type="monotone" dataKey="p99" stroke="#ec4899" name="P99" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <Card className="border-gray-200">
        <CardHeader>
          <CardTitle className="text-gray-900">Performance by URL</CardTitle>
          <CardDescription className="text-gray-600">
            Breakdown of requests and response times per endpoint
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {urlBreakdown.map((url) => (
              <div key={url.url} className="rounded-lg border border-gray-200 p-4">
                <div className="mb-3 flex items-center justify-between">
                  <code className="text-sm font-medium text-gray-900">{url.url}</code>
                  <Badge
                    variant={url.success >= 99 ? "default" : "destructive"}
                    className={
                      url.success >= 99
                        ? "bg-green-100 text-green-700 hover:bg-green-200"
                        : "bg-yellow-100 text-yellow-700 hover:bg-yellow-200"
                    }
                  >
                    {url.success}% success
                  </Badge>
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600">Requests:</span>
                    <span className="ml-2 font-medium text-gray-900">{url.requests.toLocaleString()}</span>
                  </div>
                  <div>
                    <span className="text-gray-600">Avg Time:</span>
                    <span className="ml-2 font-medium text-gray-900">{url.avgTime}ms</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </main>
  )
}
