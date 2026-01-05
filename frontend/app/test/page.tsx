import { TestConfiguration } from "@/components/test-configuration"
import { DashboardNav } from "@/components/dashboard-nav"
import { ProtectedRoute } from "@/components/protected-route"

export default function TestPage() {
  return (
    <ProtectedRoute>
      <div className="min-h-screen">
        <DashboardNav />
        <TestConfiguration />
      </div>
    </ProtectedRoute>
  )
}
