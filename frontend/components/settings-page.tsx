"use client"

import { useState } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Save, Mail, Database, Globe, Bell } from "lucide-react"

export function SettingsPage() {
  const [emailSettings, setEmailSettings] = useState({
    enabled: true,
    sender: "performance-tests@yourcompany.com",
    recipients: "team@yourcompany.com",
    smtpHost: "smtp.gmail.com",
    smtpPort: "587",
    smtpUser: "",
    smtpPassword: "",
  })

  const [awsSettings, setAwsSettings] = useState({
    s3Bucket: "performance-results-bucket",
    s3Prefix: "ramp-test-results/",
    useSES: true,
  })

  const [testDefaults, setTestDefaults] = useState({
    totalDuration: 3600,
    phaseLength: 720,
    requestTimeout: 10,
    maxThreadPoolSize: 500,
  })

  const [notifications, setNotifications] = useState({
    emailOnComplete: true,
    emailOnError: true,
    slackNotifications: false,
  })

  const handleSave = () => {
    console.log("[v0] Saving settings:", {
      emailSettings,
      awsSettings,
      testDefaults,
      notifications,
    })
    alert("Settings saved successfully!")
  }

  return (
    <div className="container mx-auto px-6 py-8 max-w-4xl">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2 text-balance">Settings</h1>
        <p className="text-muted-foreground">Configure your testing environment and notification preferences</p>
      </div>

      <div className="space-y-6">
        {/* Email Settings */}
        <Card className="p-6 border-border bg-card">
          <div className="flex items-center gap-3 mb-6">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <Mail className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h2 className="text-xl font-semibold">Email Configuration</h2>
              <p className="text-sm text-muted-foreground">SMTP settings for sending test reports</p>
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <Label>Enable Email Reports</Label>
                <p className="text-sm text-muted-foreground">Send automated email reports after tests complete</p>
              </div>
              <Switch
                checked={emailSettings.enabled}
                onCheckedChange={(checked) => setEmailSettings({ ...emailSettings, enabled: checked })}
              />
            </div>

            {emailSettings.enabled && (
              <div className="grid gap-4 pt-4 border-t border-border">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="sender">Sender Email</Label>
                    <Input
                      id="sender"
                      type="email"
                      value={emailSettings.sender}
                      onChange={(e) => setEmailSettings({ ...emailSettings, sender: e.target.value })}
                      placeholder="sender@example.com"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="recipients">Recipient Emails</Label>
                    <Input
                      id="recipients"
                      type="text"
                      value={emailSettings.recipients}
                      onChange={(e) => setEmailSettings({ ...emailSettings, recipients: e.target.value })}
                      placeholder="team@example.com, user@example.com"
                    />
                  </div>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="smtpHost">SMTP Host</Label>
                    <Input
                      id="smtpHost"
                      value={emailSettings.smtpHost}
                      onChange={(e) => setEmailSettings({ ...emailSettings, smtpHost: e.target.value })}
                      placeholder="smtp.gmail.com"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="smtpPort">SMTP Port</Label>
                    <Input
                      id="smtpPort"
                      value={emailSettings.smtpPort}
                      onChange={(e) => setEmailSettings({ ...emailSettings, smtpPort: e.target.value })}
                      placeholder="587"
                    />
                  </div>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="smtpUser">SMTP Username</Label>
                    <Input
                      id="smtpUser"
                      value={emailSettings.smtpUser}
                      onChange={(e) => setEmailSettings({ ...emailSettings, smtpUser: e.target.value })}
                      placeholder="username"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="smtpPassword">SMTP Password</Label>
                    <Input
                      id="smtpPassword"
                      type="password"
                      value={emailSettings.smtpPassword}
                      onChange={(e) => setEmailSettings({ ...emailSettings, smtpPassword: e.target.value })}
                      placeholder="••••••••"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        </Card>

        {/* AWS Settings */}
        <Card className="p-6 border-border bg-card">
          <div className="flex items-center gap-3 mb-6">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-chart-3/10">
              <Database className="h-5 w-5 text-chart-3" />
            </div>
            <div>
              <h2 className="text-xl font-semibold">AWS Configuration</h2>
              <p className="text-sm text-muted-foreground">S3 storage and SES email settings</p>
            </div>
          </div>

          <div className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="s3Bucket">S3 Bucket Name</Label>
                <Input
                  id="s3Bucket"
                  value={awsSettings.s3Bucket}
                  onChange={(e) => setAwsSettings({ ...awsSettings, s3Bucket: e.target.value })}
                  placeholder="performance-results-bucket"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="s3Prefix">S3 Prefix</Label>
                <Input
                  id="s3Prefix"
                  value={awsSettings.s3Prefix}
                  onChange={(e) => setAwsSettings({ ...awsSettings, s3Prefix: e.target.value })}
                  placeholder="ramp-test-results/"
                />
              </div>
            </div>

            <div className="flex items-center justify-between pt-2">
              <div>
                <Label>Use Amazon SES</Label>
                <p className="text-sm text-muted-foreground">Use SES instead of SMTP for email delivery</p>
              </div>
              <Switch
                checked={awsSettings.useSES}
                onCheckedChange={(checked) => setAwsSettings({ ...awsSettings, useSES: checked })}
              />
            </div>
          </div>
        </Card>

        {/* Test Defaults */}
        <Card className="p-6 border-border bg-card">
          <div className="flex items-center gap-3 mb-6">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-chart-2/10">
              <Globe className="h-5 w-5 text-chart-2" />
            </div>
            <div>
              <h2 className="text-xl font-semibold">Default Test Parameters</h2>
              <p className="text-sm text-muted-foreground">Default values for new tests</p>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="totalDuration">Total Duration (seconds)</Label>
              <Input
                id="totalDuration"
                type="number"
                value={testDefaults.totalDuration}
                onChange={(e) =>
                  setTestDefaults({ ...testDefaults, totalDuration: Number.parseInt(e.target.value) || 0 })
                }
                min={1}
              />
              <p className="text-xs text-muted-foreground">{(testDefaults.totalDuration / 60).toFixed(0)} minutes</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="phaseLength">Phase Length (seconds)</Label>
              <Input
                id="phaseLength"
                type="number"
                value={testDefaults.phaseLength}
                onChange={(e) =>
                  setTestDefaults({ ...testDefaults, phaseLength: Number.parseInt(e.target.value) || 0 })
                }
                min={1}
              />
              <p className="text-xs text-muted-foreground">{(testDefaults.phaseLength / 60).toFixed(0)} minutes</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="requestTimeout">Request Timeout (seconds)</Label>
              <Input
                id="requestTimeout"
                type="number"
                value={testDefaults.requestTimeout}
                onChange={(e) =>
                  setTestDefaults({ ...testDefaults, requestTimeout: Number.parseInt(e.target.value) || 0 })
                }
                min={1}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="maxThreadPoolSize">Max Thread Pool Size</Label>
              <Input
                id="maxThreadPoolSize"
                type="number"
                value={testDefaults.maxThreadPoolSize}
                onChange={(e) =>
                  setTestDefaults({ ...testDefaults, maxThreadPoolSize: Number.parseInt(e.target.value) || 0 })
                }
                min={1}
              />
            </div>
          </div>
        </Card>

        {/* Notifications */}
        <Card className="p-6 border-border bg-card">
          <div className="flex items-center gap-3 mb-6">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-chart-4/10">
              <Bell className="h-5 w-5 text-chart-4" />
            </div>
            <div>
              <h2 className="text-xl font-semibold">Notifications</h2>
              <p className="text-sm text-muted-foreground">Configure when to receive alerts</p>
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <Label>Email on Test Completion</Label>
                <p className="text-sm text-muted-foreground">Receive email when tests finish successfully</p>
              </div>
              <Switch
                checked={notifications.emailOnComplete}
                onCheckedChange={(checked) => setNotifications({ ...notifications, emailOnComplete: checked })}
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <Label>Email on Test Error</Label>
                <p className="text-sm text-muted-foreground">Receive email when tests encounter errors</p>
              </div>
              <Switch
                checked={notifications.emailOnError}
                onCheckedChange={(checked) => setNotifications({ ...notifications, emailOnError: checked })}
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <Label>Slack Notifications</Label>
                <p className="text-sm text-muted-foreground">Send notifications to Slack workspace</p>
              </div>
              <Switch
                checked={notifications.slackNotifications}
                onCheckedChange={(checked) => setNotifications({ ...notifications, slackNotifications: checked })}
              />
            </div>
          </div>
        </Card>

        {/* Save Button */}
        <Button onClick={handleSave} className="w-full h-12 text-base">
          <Save className="h-5 w-5 mr-2" />
          Save All Settings
        </Button>
      </div>
    </div>
  )
}
