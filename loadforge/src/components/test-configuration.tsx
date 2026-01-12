"use client";

import type React from "react";

import { useState, useEffect } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "~/components/ui/card";
import { Button } from "~/components/ui/button";
import { Input } from "~/components/ui/input";
import { Label } from "~/components/ui/label";
import { Plus, X, Upload, Download, Play, Loader2 } from "lucide-react";
import { api } from "~/trpc/react";

interface TestProgress {
  phase: number;
  total_phases: number;
  concurrency: number;
  requests: number;
  success_count: number;
  error_count: number;
  percentiles: { p50: number; p95: number; p99: number };
}

interface TestEvent {
  type:
    | "test_started"
    | "phase_complete"
    | "test_completed"
    | "error"
    | "connected";
  data: any;
}

export function TestConfiguration() {
  const [urls, setUrls] = useState([{ id: 1, url: "" }]);
  const [concurrency, setConcurrency] = useState("10,20,30");
  const [rampDuration, setRampDuration] = useState("60");
  const [holdDuration, setHoldDuration] = useState("120");
  const [isConnected, setIsConnected] = useState(false);
  const [isTestRunning, setIsTestRunning] = useState(false);
  const [currentPhase, setCurrentPhase] = useState<TestProgress | null>(null);
  const [testStatus, setTestStatus] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  api.test.onProgress.useSubscription(undefined, {
    onStarted() {
      console.log("🔌 [CLIENT] Subscription started");
      setIsConnected(true);
    },
    onData(trackedData) {
      const data = trackedData.data as TestEvent;

      if (data.type === "phase_complete") {
        setCurrentPhase(data.data);
        setTestStatus(
          `Phase ${data.data.phase} of ${data.data.total_phases} completed`
        );
      } else if (data.type === "test_completed") {
        setIsTestRunning(false);
        setTestStatus("Test completed");
        setCurrentPhase(null);
      } else if (data.type === "error") {
        setError(data.data.error || "An unknown error occurred");
        setIsTestRunning(false);
        setTestStatus("Test failed");
        setCurrentPhase(null);
      }
    },
    onError(err) {
      console.error("❌ [CLIENT] Subscription error:", err);
      setIsConnected(false);
      setError(err.message || "An unknown error occurred");
    },
  });
  const start = api.test.startTest.useMutation({
    onSuccess() {
      setIsTestRunning(true);
      setTestStatus("Test started");
      setCurrentPhase(null);
      setError(null);
    },
    onError(err) {
      setError(err.message || "An unknown error occurred");
      setIsTestRunning(false);
      setTestStatus("");
      setCurrentPhase(null);
    },
  });

  const addUrl = () => {
    setUrls([...urls, { id: Date.now(), url: "" }]);
  };

  const removeUrl = (id: number) => {
    setUrls(urls.filter((u) => u.id !== id));
  };

  const updateUrl = (id: number, value: string) => {
    setUrls(urls.map((u) => (u.id === id ? { ...u, url: value } : u)));
  };

  const handleStartTest = () => {
    const validUrls = urls.map((u) => u.url).filter((u) => u.trim());
    if (validUrls.length === 0) {
      setError("Please add at least one URL");
      return;
    }
    const concurrencyArray = concurrency
      .split(",")
      .map((c) => Number.parseInt(c.trim()))
      .filter((c) => !isNaN(c) && c > 0);

    if (concurrencyArray.length === 0) {
      setError("please provide at least one concurrency level");
      return;
    }
    const rampDurationNum = Number.parseInt(rampDuration);
    const holdDurationNum = Number.parseFloat(holdDuration);

    if (Number.isNaN(rampDurationNum) || Number.isNaN(holdDurationNum)) {
      setError("please provide valid duration values");
      return;
    }
    if (rampDurationNum <= 0 || holdDurationNum <= 0) {
      setError("duration values must be greater than 0");
      return;
    }

    setError(null);
    setIsTestRunning(true);
    setTestStatus("Test started");
    setCurrentPhase(null);

    const totalDuration = rampDurationNum + holdDurationNum + rampDurationNum;

    start.mutate({
      urls: validUrls,
      concurrency: concurrencyArray,
      ramp_up_time: rampDurationNum,
      ramp_down_time: holdDurationNum,
      total_duration: totalDuration,
      phase_length: rampDurationNum,
      hold_duration: holdDurationNum,
    });
  };

  const exportConfig = () => {
    const config = {
      urls: urls.map((u) => u.url).filter((u) => u),
      concurrency: concurrency.split(",").map((c) => Number.parseInt(c.trim())),
      rampDuration: Number.parseInt(rampDuration),
      holdDuration: Number.parseInt(holdDuration),
    };
    const blob = new Blob([JSON.stringify(config, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "loadtest-config.json";
    a.click();
  };

  const importConfig = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        try {
          const config = JSON.parse(event.target?.result as string);
          setUrls(
            config.urls.map((url: string, i: number) => ({
              id: Date.now() + i,
              url,
            }))
          );
          setConcurrency(config.concurrency.join(","));
          setRampDuration(config.rampDuration.toString());
          setHoldDuration(config.holdDuration.toString());
        } catch (error) {
          console.error("Invalid config file");
        }
      };
      reader.readAsText(file);
    }
  };

  return (
    <main className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">New Load Test</h1>
        <p className="mt-1 text-sm text-gray-600">
          Configure and run a new performance test
        </p>
      </div>

      {/* Connection Status */}
      <div className="mb-4">
        <div
          className={`inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-sm ${
            isConnected
              ? "bg-green-50 text-green-700"
              : "bg-yellow-50 text-yellow-700"
          }`}
        >
          <div
            className={`h-2 w-2 rounded-full ${
              isConnected ? "bg-green-500" : "bg-yellow-500"
            }`}
          />
          {isConnected
            ? "Connected to Testing Server"
            : "Connecting to Testing Server..."}
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-4 rounded-md bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}
      {/* Test Status */}
      {testStatus && (
        <Card className="mb-6 border-purple-200 bg-purple-50">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-semibold text-purple-900">{testStatus}</p>
                {currentPhase && (
                  <div className="mt-2 space-y-1 text-sm text-purple-700">
                    <p>
                      Phase {currentPhase.phase}/{currentPhase.total_phases} -
                      Concurrency: {currentPhase.concurrency}
                    </p>
                    <p>
                      Requests: {currentPhase.requests} | Success:{" "}
                      {currentPhase.success_count} | Errors:{" "}
                      {currentPhase.error_count}
                    </p>
                    {currentPhase.percentiles && (
                      <p className="text-xs">
                        P50: {currentPhase.percentiles.p50}ms | P95:{" "}
                        {currentPhase.percentiles.p95}ms | P99:{" "}
                        {currentPhase.percentiles.p99}ms
                      </p>
                    )}
                  </div>
                )}
              </div>
              {isTestRunning && (
                <Loader2 className="h-5 w-5 animate-spin text-purple-600" />
              )}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="space-y-6">
        <Card className="border-gray-200">
          <CardHeader>
            <CardTitle className="text-gray-900">Test URLs</CardTitle>
            <CardDescription className="text-gray-600">
              Add the endpoints you want to test
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {urls.map((urlObj, index) => (
              <div key={urlObj.id} className="flex gap-2">
                <div className="flex-1">
                  <Label htmlFor={`url-${urlObj.id}`} className="text-gray-700">
                    URL {index + 1}
                  </Label>
                  <Input
                    id={`url-${urlObj.id}`}
                    placeholder="https://api.example.com/endpoint"
                    value={urlObj.url}
                    onChange={(e) => updateUrl(urlObj.id, e.target.value)}
                    className="border-gray-300"
                    disabled={isTestRunning}
                  />
                </div>
                {urls.length > 1 && (
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => removeUrl(urlObj.id)}
                    className="mt-7 text-red-600 hover:bg-red-50 hover:text-red-700"
                    disabled={isTestRunning}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                )}
              </div>
            ))}
            <div className="flex gap-2">
              <Button
                onClick={addUrl}
                variant="outline"
                className="border-purple-300 text-purple-700 hover:bg-purple-50 bg-transparent"
                disabled={isTestRunning}
              >
                <Plus className="mr-2 h-4 w-4" />
                Add URL
              </Button>
              <label>
                <input
                  type="file"
                  accept=".json"
                  onChange={importConfig}
                  className="hidden"
                  disabled={isTestRunning}
                />
                <Button
                  variant="outline"
                  className="border-gray-300 bg-transparent"
                  asChild
                  disabled={isTestRunning}
                >
                  <span>
                    <Upload className="mr-2 h-4 w-4" />
                    Import
                  </span>
                </Button>
              </label>
              <Button
                onClick={exportConfig}
                variant="outline"
                className="border-gray-300 bg-transparent"
                disabled={isTestRunning}
              >
                <Download className="mr-2 h-4 w-4" />
                Export
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="border-gray-200">
          <CardHeader>
            <CardTitle className="text-gray-900">Concurrency Pattern</CardTitle>
            <CardDescription className="text-gray-600">
              Define how load will ramp up during the test
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="concurrency" className="text-gray-700">
                Concurrency Levels (comma-separated)
              </Label>
              <Input
                id="concurrency"
                placeholder="10,20,30,40"
                value={concurrency}
                onChange={(e) => setConcurrency(e.target.value)}
                className="border-gray-300"
                disabled={isTestRunning}
              />
              <p className="mt-1 text-xs text-gray-600">
                Number of concurrent requests at each phase
              </p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <Label htmlFor="ramp-duration" className="text-gray-700">
                  Ramp Duration (seconds)
                </Label>
                <Input
                  id="ramp-duration"
                  type="number"
                  value={rampDuration}
                  onChange={(e) => setRampDuration(e.target.value)}
                  className="border-gray-300"
                  disabled={isTestRunning}
                />
              </div>
              <div>
                <Label htmlFor="hold-duration" className="text-gray-700">
                  Hold Duration (seconds)
                </Label>
                <Input
                  id="hold-duration"
                  type="number"
                  value={holdDuration}
                  onChange={(e) => setHoldDuration(e.target.value)}
                  className="border-gray-300"
                  disabled={isTestRunning}
                />
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-end gap-3">
          <Button
            variant="outline"
            className="border-gray-300 bg-transparent"
            disabled={isTestRunning}
          >
            Save as Template
          </Button>
          <Button
            onClick={handleStartTest}
            className="bg-linear-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700"
            disabled={isTestRunning || !isConnected || start.isPending}
          >
            {isTestRunning ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin text-purple-600" />
                Running...
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                Run Test
              </>
            )}
          </Button>
        </div>
      </div>
    </main>
  );
}
