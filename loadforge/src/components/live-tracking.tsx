"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "~/components/ui/card"
import { Badge } from "~/components/ui/badge"
import { Progress } from "~/components/ui/progress"
import { Activity, Clock, TrendingUp, AlertCircle, CheckCircle2, Loader2 } from "lucide-react"

interface LiveTest {
  id: number
  name: string
  status: "running" | "completed" | "failed"
  progress: number
  startTime: string
  currentPhase: string
  metrics: {
    totalRequests: number
    successRate: number
    avgResponseTime: number
    currentConcurrency: number
  }
}

export function LiveTracking() {
  const [liveTests, setLiveTests] = useState<LiveTest[]>([
    {
      id: 1,
      name: "API Performance Test - Production",
      status: "running",
      progress: 45,
      startTime: new Date().toISOString(),
      currentPhase: "Ramp Up (Phase 2/4)",
      metrics: {
        totalRequests: 1240,
        successRate: 98.5,
        avgResponseTime: 245,
        currentConcurrency: 20,
      },
    },
    {
      id: 2,
      name: "Homepage Load Test",
      status: "running",
      progress: 72,
      startTime: new Date(Date.now() - 300000).toISOString(),
      currentPhase: "Steady State (Phase 3/4)",
      metrics: {
        totalRequests: 3450,
        successRate: 99.2,
        avgResponseTime: 180,
        currentConcurrency: 30,
      },
    },
  ])

  // Simulate real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      setLiveTests((tests) =>
        tests.map((test) => ({
          ...test,
          progress: Math.min(test.progress + Math.random() * 5, 100),
          metrics: {
            ...test.metrics,
            totalRequests: test.metrics.totalRequests + Math.floor(Math.random() * 50),
            avgResponseTime: Math.max(100, test.metrics.avgResponseTime + (Math.random() - 0.5) * 20),
            successRate: Math.min(100, Math.max(95, test.metrics.successRate + (Math.random() - 0.5) * 0.5)),
          },
        })),
      )
    }, 2000)

    return () => clearInterval(interval)
  }, [])

  const getStatusBadge = (status: LiveTest["status"]) => {
    switch (status) {
      case "running":
        return (
          <Badge className="bg-blue-100 text-blue-700 hover:bg-blue-100">
            <Loader2 className="mr-1 h-3 w-3 animate-spin" />
            Running
          </Badge>
        )
      case "completed":
        return (
          <Badge className="bg-green-100 text-green-700 hover:bg-green-100">
            <CheckCircle2 className="mr-1 h-3 w-3" />
            Completed
          </Badge>
        )
      case "failed":
        return (
          <Badge className="bg-red-100 text-red-700 hover:bg-red-100">
            <AlertCircle className="mr-1 h-3 w-3" />
            Failed
          </Badge>
        )
    }
  }

  const formatTime = (isoString: string) => {
    const date = new Date(isoString)
    return date.toLocaleTimeString()
  }

  const getElapsedTime = (startTime: string) => {
    const elapsed = Date.now() - new Date(startTime).getTime()
    const seconds = Math.floor(elapsed / 1000)
    const minutes = Math.floor(seconds / 60)
    const hours = Math.floor(minutes / 60)

    if (hours > 0) return `${hours}h ${minutes % 60}m`
    if (minutes > 0) return `${minutes}m ${seconds % 60}s`
    return `${seconds}s`
  }

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Live Test Tracking</h1>
        <p className="mt-1 text-sm text-gray-600">Monitor your running load tests in real-time</p>
      </div>

      {liveTests.length === 0 ? (
        <Card className="border-gray-200">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Activity className="mb-4 h-12 w-12 text-gray-400" />
            <p className="text-lg font-medium text-gray-900">No tests running</p>
            <p className="mt-1 text-sm text-gray-600">Start a new test to see live tracking here</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {liveTests.map((test) => (
            <Card key={test.id} className="border-gray-200">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="text-gray-900">{test.name}</CardTitle>
                    <CardDescription className="mt-1 flex items-center gap-4 text-gray-600">
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        Started: {formatTime(test.startTime)}
                      </span>
                      <span>Elapsed: {getElapsedTime(test.startTime)}</span>
                    </CardDescription>
                  </div>
                  {getStatusBadge(test.status)}
                </div>
              </CardHeader>
              <CardContent className="space-y-6">
                <div>
                  <div className="mb-2 flex items-center justify-between text-sm">
                    <span className="font-medium text-gray-700">{test.currentPhase}</span>
                    <span className="text-gray-600">{Math.round(test.progress)}%</span>
                  </div>
                  <Progress value={test.progress} className="h-2" />
                </div>

                <div className="grid gap-4 sm:grid-cols-4">
                  <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                      <Activity className="h-4 w-4" />
                      Total Requests
                    </div>
                    <div className="mt-2 text-2xl font-bold text-gray-900">
                      {test.metrics.totalRequests.toLocaleString()}
                    </div>
                  </div>

                  <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                      <CheckCircle2 className="h-4 w-4" />
                      Success Rate
                    </div>
                    <div className="mt-2 text-2xl font-bold text-gray-900">{test.metrics.successRate.toFixed(1)}%</div>
                  </div>

                  <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                      <Clock className="h-4 w-4" />
                      Avg Response
                    </div>
                    <div className="mt-2 text-2xl font-bold text-gray-900">
                      {Math.round(test.metrics.avgResponseTime)}ms
                    </div>
                  </div>

                  <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                      <TrendingUp className="h-4 w-4" />
                      Concurrency
                    </div>
                    <div className="mt-2 text-2xl font-bold text-gray-900">{test.metrics.currentConcurrency}</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </main>
  )
}
