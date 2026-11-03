"use client";

import { FormEvent, useEffect, useState } from "react";
import { AppShell, PageHeader } from "@/components/shell";
import { Badge, Banner, Button, Card, EmptyState, Field, Select, TextInput } from "@/components/ui";
import { api, patch, post } from "@/lib/api";
import { RequireSession, useSession, type User } from "@/lib/auth";
import { shortDateTime } from "@/lib/format";

export default function TeamPage() {
  return (
    <RequireSession>
      <TeamScreen />
    </RequireSession>
  );
}

function TeamScreen() {
  const session = useSession();
  const [users, setUsers] = useState<User[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "analyst" as User["role"] });
  const [resetting, setResetting] = useState<{ id: string; password: string } | null>(null);
  const isAdmin = session.user?.role === "admin";

  useEffect(() => {
    if (!isAdmin) return;
    api<User[]>("/v1/users")
      .then(setUsers)
      .catch((caught: unknown) => setError(caught instanceof Error ? caught.message : "Unable to load users."));
  }, [isAdmin]);

  async function run(key: string, action: () => Promise<void>) {
    setBusy(key);
    setError(null);
    setNotice(null);
    try {
      await action();
      setUsers(await api<User[]>("/v1/users"));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The request could not be completed.");
    } finally {
      setBusy(null);
    }
  }

  async function createUser(event: FormEvent) {
    event.preventDefault();
    await run("create", async () => {
      await post<User>("/v1/users", form);
      setNotice(`Created ${form.email}. Share the password with them directly; they can change it after signing in.`);
      setForm({ name: "", email: "", password: "", role: "analyst" });
    });
  }

  if (!session.required) {
    return (
      <AppShell crumbs={[{ label: "Team and access" }]}>
        <EmptyState title="Sign-in is off in this environment" description="Accounts and roles apply when the deployment runs with APP_REQUIRE_AUTH=true. The local launcher enables it with a demo administrator." />
      </AppShell>
    );
  }
  if (!isAdmin) {
    return (
      <AppShell crumbs={[{ label: "Team and access" }]}>
        <EmptyState title="Administrator access required" description="Ask a Deal Scope administrator to manage team members." />
      </AppShell>
    );
  }

  return (
    <AppShell crumbs={[{ label: "Team and access" }]}>
      <PageHeader title="Team and access" description="Administrators manage who can sign in. Analysts work deals; administrators also manage accounts. Every saved version records who created it." />
      {error && (
        <div className="mb-4">
          <Banner tone="error" onDismiss={() => setError(null)}>
            {error}
          </Banner>
        </div>
      )}
      {notice && (
        <div className="mb-4">
          <Banner tone="success" onDismiss={() => setNotice(null)}>
            {notice}
          </Banner>
        </div>
      )}
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <Card title="Members" description={users ? `${users.length} account${users.length === 1 ? "" : "s"}` : undefined}>
          {users === null ? (
            <p className="py-8 text-center text-sm text-ink-muted">Loading…</p>
          ) : (
            <div className="-mx-5 overflow-x-auto sm:-mx-6">
              <table className="data-table min-w-[720px]">
                <thead>
                  <tr>
                    <th>Member</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th>Last sign-in</th>
                    <th aria-label="Actions" />
                  </tr>
                </thead>
                <tbody>
                  {users.map((user) => {
                    const self = user.id === session.user?.id;
                    return (
                      <tr key={user.id}>
                        <td className="!text-left">
                          <p className="font-semibold text-ink">
                            {user.name} {self && <Badge tone="neutral">you</Badge>}
                          </p>
                          <p className="text-xs text-ink-muted">{user.email}</p>
                        </td>
                        <td className="!text-left">
                          <Select
                            value={user.role}
                            disabled={self || busy !== null}
                            onChange={(event) => void run("role-" + user.id, async () => void (await patch("/v1/users/" + user.id, { role: event.target.value })))}
                            className="h-8 w-32"
                          >
                            <option value="analyst">Analyst</option>
                            <option value="admin">Admin</option>
                          </Select>
                        </td>
                        <td className="!text-left">{user.is_active ? <Badge tone="good">Active</Badge> : <Badge tone="warn">Deactivated</Badge>}</td>
                        <td className="text-ink-muted">{user.last_login_at ? shortDateTime(user.last_login_at) : "Never"}</td>
                        <td>
                          <div className="flex justify-end gap-1">
                            {resetting?.id === user.id ? (
                              <form
                                className="flex items-center gap-2"
                                onSubmit={(event) => {
                                  event.preventDefault();
                                  void run("reset-" + user.id, async () => {
                                    await patch("/v1/users/" + user.id, { password: resetting.password });
                                    setResetting(null);
                                    setNotice(`Password reset for ${user.email}.`);
                                  });
                                }}
                              >
                                <TextInput type="password" autoFocus required minLength={8} placeholder="New password (8+)" value={resetting.password} onChange={(event) => setResetting({ id: user.id, password: event.target.value })} className="h-8 w-44" />
                                <Button size="sm" type="submit" busy={busy === "reset-" + user.id}>
                                  Save
                                </Button>
                                <Button size="sm" type="button" variant="ghost" onClick={() => setResetting(null)}>
                                  Cancel
                                </Button>
                              </form>
                            ) : (
                              <>
                                <Button size="sm" variant="ghost" onClick={() => setResetting({ id: user.id, password: "" })}>
                                  Reset password
                                </Button>
                                {!self && (
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    className={user.is_active ? "text-critical" : ""}
                                    busy={busy === "active-" + user.id}
                                    onClick={() => void run("active-" + user.id, async () => void (await patch("/v1/users/" + user.id, { is_active: !user.is_active })))}
                                  >
                                    {user.is_active ? "Deactivate" : "Reactivate"}
                                  </Button>
                                )}
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>
        <Card title="Add a member" description="Create the account, then share the password with the person directly. Each new member starts with their own copy of the Maple Street example deal and sees only the deals they create.">
          <form onSubmit={createUser} className="space-y-4">
            <Field label="Name">
              <TextInput required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
            </Field>
            <Field label="Email">
              <TextInput required type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} />
            </Field>
            <Field label="Temporary password" help="At least 8 characters. They can change it after signing in.">
              <TextInput required type="password" minLength={8} autoComplete="new-password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} />
            </Field>
            <Field label="Role">
              <Select value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value as User["role"] })}>
                <option value="analyst">Analyst — works deals</option>
                <option value="admin">Administrator — also manages accounts</option>
              </Select>
            </Field>
            <Button type="submit" className="w-full" busy={busy === "create"}>
              Create account
            </Button>
          </form>
        </Card>
      </div>
    </AppShell>
  );
}
