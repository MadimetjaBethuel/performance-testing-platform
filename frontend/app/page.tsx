import { DashboardOverview } from "@/components/dashboard-overview"
import { DashboardNav } from "@/components/dashboard-nav"
import { ProtectedRoute } from "@/components/protected-route"

export default function HomePage() {
  return (
    <ProtectedRoute>
      <div className="min-h-screen">
        <DashboardNav />
        <DashboardOverview />
      </div>
    </ProtectedRoute>
  )
}
