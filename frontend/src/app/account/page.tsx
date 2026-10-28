"use client";

import { FormEvent, useState } from "react";
import { AppShell, PageHeader } from "@/components/shell";
import { Banner, Button, Card, EmptyState, Field, KeyValue, TextInput } from "@/components/ui";
import { post } from "@/lib/api";
import { RequireSession, useSession } from "@/lib/auth";
import { shortDateTime } from "@/lib/format";

export default function AccountPage() {
  return (
    <RequireSession>
      <AccountScreen />
    </RequireSession>
  );
}

function AccountScreen() {
  const session = useSession();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    if (next !== confirm) {
      setError("The new passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      await post("/v1/auth/password", { current_password: current, new_password: next });
      setNotice("Password changed.");
      setCurrent("");
      setNext("");
      setConfirm("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to change the password.");
    } finally {
      setBusy(false);
    }
  }

  if (!session.required || !session.user) {
    return (
      <AppShell crumbs={[{ label: "Account" }]}>
        <EmptyState title="Sign-in is off in this environment" description="Accounts apply when the deployment runs with APP_REQUIRE_AUTH=true. The local launcher enables it with a demo administrator." />
      </AppShell>
    );
  }
  return (
    <AppShell crumbs={[{ label: "Account" }]}>
      <PageHeader title="Your account" />
      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Profile">
          <KeyValue
            rows={[
              ["Name", session.user.name],
              ["Email", session.user.email],
              ["Role", session.user.role === "admin" ? "Administrator" : "Analyst"],
              ["Last sign-in", session.user.last_login_at ? shortDateTime(session.user.last_login_at) : "—"],
            ]}
          />
        </Card>
        <Card title="Change password">
          <form onSubmit={submit} className="space-y-4">
            {error && <Banner tone="error">{error}</Banner>}
            {notice && <Banner tone="success">{notice}</Banner>}
            <Field label="Current password">
              <TextInput required type="password" autoComplete="current-password" value={current} onChange={(event) => setCurrent(event.target.value)} />
            </Field>
            <Field label="New password" help="At least 8 characters.">
              <TextInput required type="password" minLength={8} autoComplete="new-password" value={next} onChange={(event) => setNext(event.target.value)} />
            </Field>
            <Field label="Confirm new password">
              <TextInput required type="password" minLength={8} autoComplete="new-password" value={confirm} onChange={(event) => setConfirm(event.target.value)} />
            </Field>
            <Button type="submit" busy={busy}>
              Update password
            </Button>
          </form>
        </Card>
      </div>
    </AppShell>
  );
}
