import { SettingsPage } from "@/components/settings-page"
import { DashboardNav } from "@/components/dashboard-nav"
import { ProtectedRoute } from "@/components/protected-route"

export default function Settings() {
  return (
    <ProtectedRoute>
      <div className="min-h-screen">
        <DashboardNav />
        <SettingsPage />
      </div>
    </ProtectedRoute>
  )
}
