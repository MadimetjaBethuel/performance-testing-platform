"use client"

import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Activity, Clock, Target, TrendingUp, CheckCircle } from "lucide-react"
import Link from "next/link"

export function DashboardOverview() {
  // Mock data - will be replaced with real data
  const stats = [
    {
      label: "Total Tests",
      value: "127",
      change: "+12%",
      trend: "up",
      icon: Target,
    },
    {
      label: "Avg Success Rate",
      value: "98.4%",
      change: "+2.1%",
      trend: "up",
      icon: CheckCircle,
    },
    {
      label: "Avg Response Time",
      value: "245ms",
      change: "-15ms",
      trend: "up",
      icon: TrendingUp,
    },
    {
      label: "Active Tests",
      value: "0",
      change: "No tests running",
      trend: "neutral",
      icon: Activity,
    },
  ]

  const recentTests = [
    {
      id: "1",
      timestamp: "2025-01-09T14:30:00Z",
      duration: "3600s",
      requests: 45234,
      successRate: 98.7,
      status: "completed",
    },
    {
      id: "2",
      timestamp: "2025-01-08T10:15:00Z",
      duration: "3600s",
      requests: 43891,
      successRate: 97.2,
      status: "completed",
    },
    {
      id: "3",
      timestamp: "2025-01-07T16:45:00Z",
      duration: "3600s",
      requests: 47120,
      successRate: 99.1,
      status: "completed",
    },
  ]

  return (
    <div className="container mx-auto px-6 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2 text-balance">Performance Testing Dashboard</h1>
        <p className="text-muted-foreground">Monitor and analyze your load testing results in real-time</p>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4 mb-8">
        {stats.map((stat) => {
          const Icon = stat.icon
          return (
            <Card key={stat.label} className="p-6 border-border bg-card">
              <div className="flex items-start justify-between mb-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                  <Icon className="h-5 w-5 text-primary" />
                </div>
                {stat.trend !== "neutral" && (
                  <Badge variant="secondary" className="text-xs">
                    {stat.change}
                  </Badge>
                )}
              </div>
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">{stat.label}</p>
                <p className="text-3xl font-bold">{stat.value}</p>
              </div>
            </Card>
          )
        })}
      </div>

      {/* Quick Actions */}
      <div className="grid gap-6 md:grid-cols-2 mb-8">
        <Card className="p-6 border-border bg-card">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary">
              <Target className="h-6 w-6 text-primary-foreground" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold mb-1">Run New Test</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Start a new load test with custom concurrency patterns
              </p>
              <Link href="/test">
                <Button className="w-full sm:w-auto">Start Test</Button>
              </Link>
            </div>
          </div>
        </Card>

        <Card className="p-6 border-border bg-card">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-secondary">
              <Clock className="h-6 w-6 text-secondary-foreground" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold mb-1">View Recent Results</h3>
              <p className="text-sm text-muted-foreground mb-4">Analyze historical test data and performance metrics</p>
              <Link href="/results">
                <Button variant="secondary" className="w-full sm:w-auto">
                  View Results
                </Button>
              </Link>
            </div>
          </div>
        </Card>
      </div>

      {/* Recent Tests Table */}
      <Card className="border-border bg-card">
        <div className="p-6 border-b border-border">
          <h2 className="text-xl font-semibold">Recent Tests</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="border-b border-border bg-muted/50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Timestamp
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Duration
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Requests
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Success Rate
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {recentTests.map((test) => (
                <tr key={test.id} className="hover:bg-accent/50 transition-colors">
                  <td className="px-6 py-4 text-sm">{new Date(test.timestamp).toLocaleString()}</td>
                  <td className="px-6 py-4 text-sm text-muted-foreground">{test.duration}</td>
                  <td className="px-6 py-4 text-sm font-mono">{test.requests.toLocaleString()}</td>
                  <td className="px-6 py-4 text-sm">
                    <span
                      className={
                        test.successRate >= 95
                          ? "text-chart-2"
                          : test.successRate >= 90
                            ? "text-chart-3"
                            : "text-destructive"
                      }
                    >
                      {test.successRate}%
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <Badge variant="secondary">{test.status}</Badge>
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <Link href={`/results/${test.id}`}>
                      <Button variant="ghost" size="sm">
                        View Details
                      </Button>
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
