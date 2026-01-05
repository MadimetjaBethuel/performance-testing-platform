import { TestResults } from "@/components/test-results"
import { DashboardNav } from "@/components/dashboard-nav"
import { ProtectedRoute } from "@/components/protected-route"

export default function ResultsPage() {
  return (
    <ProtectedRoute>
      <div className="min-h-screen">
        <DashboardNav />
        <TestResults />
      </div>
    </ProtectedRoute>
  )
}
