"use client"

import type React from "react"

import { useState } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Play, Plus, Trash2, Info, Upload, Download } from "lucide-react"

export function TestConfiguration() {
  const [urls, setUrls] = useState<string[]>(["https://example.com"])
  const [concurrencyPattern, setConcurrencyPattern] = useState<number[]>([1000, 3000, 5000, 10000])
  const [testDuration, setTestDuration] = useState(3600)
  const [phaseDuration, setPhaseDuration] = useState(720)
  const [isRunning, setIsRunning] = useState(false)
  const [showBulkImport, setShowBulkImport] = useState(false)
  const [bulkUrls, setBulkUrls] = useState("")

  const addUrl = () => {
    setUrls([...urls, ""])
  }

  const removeUrl = (index: number) => {
    setUrls(urls.filter((_, i) => i !== index))
  }

  const updateUrl = (index: number, value: string) => {
    const newUrls = [...urls]
    newUrls[index] = value
    setUrls(newUrls)
  }

  const handleBulkImport = () => {
    const importedUrls = bulkUrls
      .split("\n")
      .map((url) => url.trim())
      .filter((url) => url.length > 0)

    if (importedUrls.length > 0) {
      setUrls(importedUrls)
      setBulkUrls("")
      setShowBulkImport(false)
    }
  }

  const handleExportUrls = () => {
    const data = JSON.stringify(
      urls.filter((u) => u.trim()).map((url) => ({ url })),
      null,
      2,
    )
    const blob = new Blob([data], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "test-urls.json"
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleImportFile = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const content = e.target?.result as string
        const data = JSON.parse(content)

        if (Array.isArray(data)) {
          const importedUrls = data.map((item) => (typeof item === "string" ? item : item.url)).filter(Boolean)
          if (importedUrls.length > 0) {
            setUrls(importedUrls)
          }
        }
      } catch (error) {
        alert("Error parsing JSON file. Please ensure it's a valid JSON array.")
      }
    }
    reader.readAsText(file)
  }

  const addConcurrencyStep = () => {
    setConcurrencyPattern([...concurrencyPattern, 1000])
  }

  const removeConcurrencyStep = (index: number) => {
    setConcurrencyPattern(concurrencyPattern.filter((_, i) => i !== index))
  }

  const updateConcurrencyStep = (index: number, value: number) => {
    const newPattern = [...concurrencyPattern]
    newPattern[index] = value
    setConcurrencyPattern(newPattern)
  }

  const handleRunTest = async () => {
    setIsRunning(true)
    console.log("[v0] Starting test with configuration:", {
      urls,
      concurrencyPattern,
      testDuration,
      phaseDuration,
    })

    setTimeout(() => {
      setIsRunning(false)
      alert("Test completed! Check the Results page for details.")
    }, 3000)
  }

  return (
    <div className="container mx-auto px-6 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2 text-balance">Configure Load Test</h1>
        <p className="text-muted-foreground">Set up your test parameters and run comprehensive performance tests</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Configuration Form */}
        <div className="lg:col-span-2 space-y-6">
          {/* URLs Section */}
          <Card className="p-6 border-border bg-card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">Target URLs</h2>
              <div className="flex gap-2">
                <Button onClick={handleExportUrls} size="sm" variant="outline">
                  <Download className="h-4 w-4 mr-2" />
                  Export
                </Button>
                <Button onClick={() => setShowBulkImport(!showBulkImport)} size="sm" variant="outline">
                  <Upload className="h-4 w-4 mr-2" />
                  Import
                </Button>
                <Button onClick={addUrl} size="sm" variant="outline">
                  <Plus className="h-4 w-4 mr-2" />
                  Add
                </Button>
              </div>
            </div>

            {showBulkImport && (
              <div className="mb-4 p-4 bg-accent rounded-lg space-y-3">
                <div className="flex items-center justify-between">
                  <Label>Bulk Import URLs</Label>
                  <input type="file" accept=".json" onChange={handleImportFile} className="hidden" id="file-import" />
                  <Button onClick={() => document.getElementById("file-import")?.click()} size="sm" variant="secondary">
                    Import from JSON
                  </Button>
                </div>
                <Textarea
                  placeholder="Paste URLs here (one per line)"
                  value={bulkUrls}
                  onChange={(e) => setBulkUrls(e.target.value)}
                  rows={5}
                  className="font-mono text-sm"
                />
                <div className="flex gap-2">
                  <Button onClick={handleBulkImport} size="sm">
                    Import URLs
                  </Button>
                  <Button onClick={() => setShowBulkImport(false)} size="sm" variant="ghost">
                    Cancel
                  </Button>
                </div>
              </div>
            )}

            <div className="space-y-3">
              {urls.map((url, index) => (
                <div key={index} className="flex gap-2">
                  <Input
                    value={url}
                    onChange={(e) => updateUrl(index, e.target.value)}
                    placeholder="https://example.com/api/endpoint"
                    className="flex-1"
                  />
                  {urls.length > 1 && (
                    <Button onClick={() => removeUrl(index)} variant="ghost" size="icon">
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  )}
                </div>
              ))}
            </div>
            <p className="text-xs text-muted-foreground mt-3">
              Add one or more URLs to test. The load will be distributed randomly across all URLs.
            </p>
          </Card>

          {/* Concurrency Pattern */}
          <Card className="p-6 border-border bg-card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">Concurrency Pattern</h2>
              <Button onClick={addConcurrencyStep} size="sm" variant="outline">
                <Plus className="h-4 w-4 mr-2" />
                Add Step
              </Button>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              {concurrencyPattern.map((value, index) => (
                <div key={index} className="flex items-center gap-2">
                  <Label className="w-16 text-muted-foreground text-sm">Phase {index + 1}</Label>
                  <Input
                    type="number"
                    value={value}
                    onChange={(e) => updateConcurrencyStep(index, Number.parseInt(e.target.value) || 0)}
                    className="flex-1"
                    min={1}
                  />
                  <span className="text-sm text-muted-foreground w-12">users</span>
                  {concurrencyPattern.length > 1 && (
                    <Button onClick={() => removeConcurrencyStep(index)} variant="ghost" size="icon">
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  )}
                </div>
              ))}
            </div>
            <p className="text-xs text-muted-foreground mt-3">
              Define the number of concurrent users for each test phase. The test will ramp through these values.
            </p>
          </Card>

          {/* Duration Settings */}
          <Card className="p-6 border-border bg-card">
            <h2 className="text-xl font-semibold mb-4">Duration Settings</h2>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="testDuration">Total Test Duration (seconds)</Label>
                <Input
                  id="testDuration"
                  type="number"
                  value={testDuration}
                  onChange={(e) => setTestDuration(Number.parseInt(e.target.value) || 0)}
                  min={1}
                />
                <p className="text-xs text-muted-foreground">{(testDuration / 60).toFixed(1)} minutes</p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="phaseDuration">Phase Duration (seconds)</Label>
                <Input
                  id="phaseDuration"
                  type="number"
                  value={phaseDuration}
                  onChange={(e) => setPhaseDuration(Number.parseInt(e.target.value) || 0)}
                  min={1}
                />
                <p className="text-xs text-muted-foreground">{(phaseDuration / 60).toFixed(1)} minutes per phase</p>
              </div>
            </div>
          </Card>

          {/* Run Test Button */}
          <Button
            onClick={handleRunTest}
            className="w-full h-12 text-base"
            disabled={isRunning || urls.some((u) => !u.trim())}
          >
            {isRunning ? (
              <>
                <div className="h-4 w-4 mr-2 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                Running Test...
              </>
            ) : (
              <>
                <Play className="h-5 w-5 mr-2" />
                Run Load Test
              </>
            )}
          </Button>
        </div>

        {/* Configuration Summary Sidebar */}
        <div className="space-y-6">
          <Card className="p-6 border-border bg-card">
            <div className="flex items-center gap-2 mb-4">
              <Info className="h-5 w-5 text-primary" />
              <h3 className="font-semibold">Test Summary</h3>
            </div>
            <div className="space-y-4">
              <div>
                <p className="text-sm text-muted-foreground mb-1">Total URLs</p>
                <p className="text-2xl font-bold">{urls.filter((u) => u.trim()).length}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground mb-1">Test Phases</p>
                <p className="text-2xl font-bold">{concurrencyPattern.length}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground mb-1">Max Concurrency</p>
                <p className="text-2xl font-bold">{Math.max(...concurrencyPattern)} users</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground mb-1">Total Duration</p>
                <p className="text-2xl font-bold">{(testDuration / 60).toFixed(0)} min</p>
              </div>
              <div className="pt-2 border-t border-border">
                <p className="text-sm text-muted-foreground mb-2">Estimated Requests</p>
                <p className="text-lg font-mono">
                  ~
                  {(
                    (concurrencyPattern.reduce((a, b) => a + b, 0) / concurrencyPattern.length) *
                    (testDuration / 2)
                  ).toLocaleString()}
                </p>
              </div>
            </div>
          </Card>

          <Card className="p-6 border-border bg-card">
            <h3 className="font-semibold mb-3">Configuration Tips</h3>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li className="flex gap-2">
                <span className="text-primary">•</span>
                <span>Start with lower concurrency to establish a baseline</span>
              </li>
              <li className="flex gap-2">
                <span className="text-primary">•</span>
                <span>Use realistic URLs from your production environment</span>
              </li>
              <li className="flex gap-2">
                <span className="text-primary">•</span>
                <span>Monitor your backend resources during the test</span>
              </li>
              <li className="flex gap-2">
                <span className="text-primary">•</span>
                <span>Results will be saved automatically and available in the Results page</span>
              </li>
            </ul>
          </Card>
        </div>
      </div>
    </div>
  )
}
