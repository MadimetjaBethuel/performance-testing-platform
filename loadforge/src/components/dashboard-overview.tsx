"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "~/components/ui/card"
import { Badge } from "~/components/ui/badge"
import { Button } from "~/components/ui/button"
import { Activity, Clock, TrendingUp, CheckCircle2, XCircle, Play } from "lucide-react"
import Link from "next/link"

export function DashboardOverview() {
  const metrics = [
    {
      title: "Total Tests Run",
      value: "248",
      change: "+12%",
      trend: "up",
      icon: Activity,
    },
    {
      title: "Avg Response Time",
      value: "142ms",
      change: "-8%",
      trend: "down",
      icon: Clock,
    },
    {
      title: "Success Rate",
      value: "99.7%",
      change: "+0.3%",
      trend: "up",
      icon: CheckCircle2,
    },
    {
      title: "Failed Requests",
      value: "23",
      change: "-15%",
      trend: "down",
      icon: XCircle,
    },
  ]

  const recentTests = [
    {
      id: 1,
      name: "API Endpoint Stress Test",
      status: "completed",
      duration: "5m 23s",
      requests: "15,240",
      successRate: "99.8%",
      timestamp: "2 hours ago",
    },
    {
      id: 2,
      name: "Homepage Load Test",
      status: "completed",
      duration: "3m 45s",
      requests: "8,920",
      successRate: "100%",
      timestamp: "5 hours ago",
    },
    {
      id: 3,
      name: "Checkout Flow Test",
      status: "failed",
      duration: "2m 12s",
      requests: "4,560",
      successRate: "94.2%",
      timestamp: "1 day ago",
    },
  ]

  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="mt-1 text-sm text-gray-600">Monitor your load testing performance</p>
        </div>
        <Link href="/test">
          <Button className="bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700">
            <Play className="mr-2 h-4 w-4" />
            New Test
          </Button>
        </Link>
      </div>

      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {metrics.map((metric) => {
          const Icon = metric.icon
          return (
            <Card key={metric.title} className="border-gray-200">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-gray-600">{metric.title}</CardTitle>
                <Icon className="h-4 w-4 text-gray-400" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-gray-900">{metric.value}</div>
                <p className="flex items-center text-xs text-gray-600">
                  <TrendingUp className={`mr-1 h-3 w-3 ${metric.trend === "up" ? "text-green-600" : "text-red-600"}`} />
                  <span className={metric.trend === "up" ? "text-green-600" : "text-red-600"}>{metric.change}</span>
                  <span className="ml-1">from last week</span>
                </p>
              </CardContent>
            </Card>
          )
        })}
      </div>

      <Card className="border-gray-200">
        <CardHeader>
          <CardTitle className="text-gray-900">Recent Tests</CardTitle>
          <CardDescription className="text-gray-600">Your latest load testing runs</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {recentTests.map((test) => (
              <div key={test.id} className="flex items-center justify-between rounded-lg border border-gray-200 p-4">
                <div className="flex items-center gap-4">
                  <div
                    className={`flex h-10 w-10 items-center justify-center rounded-lg ${
                      test.status === "completed" ? "bg-green-100" : "bg-red-100"
                    }`}
                  >
                    {test.status === "completed" ? (
                      <CheckCircle2 className="h-5 w-5 text-green-600" />
                    ) : (
                      <XCircle className="h-5 w-5 text-red-600" />
                    )}
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">{test.name}</p>
                    <p className="text-sm text-gray-600">
                      {test.duration} • {test.requests} requests • {test.timestamp}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge
                    variant={test.status === "completed" ? "default" : "destructive"}
                    className={
                      test.status === "completed"
                        ? "bg-green-100 text-green-700 hover:bg-green-200"
                        : "bg-red-100 text-red-700 hover:bg-red-200"
                    }
                  >
                    {test.successRate}
                  </Badge>
                  <Link href="/results">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-purple-600 hover:bg-purple-50 hover:text-purple-700"
                    >
                      View Details
                    </Button>
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </main>
  )
}
