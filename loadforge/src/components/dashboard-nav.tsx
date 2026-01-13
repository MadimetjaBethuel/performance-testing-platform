"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { Activity, Settings, Zap, BarChart3, Radio } from "lucide-react"
import { Button } from "~/components/ui/button"

export function DashboardNav() {
  const pathname = usePathname()

  const links = [
    { href: "/", label: "Dashboard", icon: Activity },
    { href: "/test", label: "New Test", icon: Zap },
    { href: "/live", label: "Live Tests", icon: Radio },
    { href: "/results", label: "Results", icon: BarChart3 },
    { href: "/settings", label: "Settings", icon: Settings },
  ]

  return (
    <nav className="border-b bg-white " >
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-linear-to-br from-purple-600 to-indigo-600">
            <Zap className="h-5 w-5 text-white" />
          </div>
          <span className="bg-linear-to-r from-purple-600 to-indigo-600 bg-clip-text text-xl font-bold text-transparent">
            LoadForge
          </span>
        </div>
        <div className="flex items-center gap-1">
          {links.map((link) => {
            const Icon = link.icon
            const isActive = pathname === link.href
            return (
              <Link key={link.href} href={link.href}>
                <Button
                  variant="ghost"
                  className={
                    isActive
                      ? "bg-purple-50 text-purple-700 hover:bg-purple-100 hover:text-purple-800"
                      : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                  }
                >
                  <Icon className="mr-2 h-4 w-4" />
                  {link.label}
                </Button>
              </Link>
            )
          })}
        </div>
      </div>
    </nav>
  )
}
