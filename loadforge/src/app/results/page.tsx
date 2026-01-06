import { TestResults } from "~/components/test-results"
import { DashboardNav } from "~/components/dashboard-nav"

export default function ResultsPage() {
  return (
    <div className="min-h-screen">
      <DashboardNav />
      <TestResults />
    </div>
  )
}
