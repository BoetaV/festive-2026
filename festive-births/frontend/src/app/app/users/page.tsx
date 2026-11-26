"use client"

import { useState } from "react"
import useSWR from "swr"
import { toast } from "sonner"
import {
  CopyIcon, DownloadIcon, FileSignatureIcon, KeyRoundIcon, LockIcon, LockOpenIcon, LogOutIcon, MoreHorizontalIcon, PencilIcon,
  PlusIcon, SearchIcon, Trash2Icon,
} from "lucide-react"
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import { Switch } from "@/components/ui/switch"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Field, NativeSelect } from "@/components/form-controls"
import { PageHeader, Pagination } from "@/components/page-header"
import { api, ApiError, download, qs } from "@/lib/api"
import { can, useAuth } from "@/lib/auth"
import { timeAgo } from "@/lib/format"
import { ROLE_LABEL, type Meta, type Paged, type Role, type User } from "@/lib/types"

type Form = {
  first_name: string; last_name: string; email: string; title: string; designation: string
  persal_number: string; mobile_number: string; role: Role; district: string; local_municipality: string
  facility: string; is_active: boolean
}

const blank: Form = {
  first_name: "", last_name: "", email: "", title: "", designation: "", persal_number: "", mobile_number: "",
  role: "user", district: "", local_municipality: "", facility: "", is_active: true,
}

const isLocked = (u: User) => !!u.locked_until && new Date(u.locked_until) > new Date()

function UserDialog({
  open, onClose, editing, meta, actor, onSaved,
}: {
  open: boolean; onClose: () => void; editing: User | null; meta?: Meta; actor: User | null
  onSaved: (tempPassword?: string, user?: User) => void
}) {
  const [f, setF] = useState<Form>(blank)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)
  const [lastOpen, setLastOpen] = useState<number | null | undefined>(undefined)

  const isAdmin = actor?.role === "admin"
  // Superuser: any role. Province: district and facility users. District: facility users only.
  const roles: Role[] =
    actor?.role === "province" ? ["admin", "user"] : isAdmin ? ["user"] : ["superuser", "province", "admin", "user"]

  // Reset form whenever the dialog opens for a different target.
  const key = open ? (editing?.id ?? null) : undefined
  if (key !== lastOpen) {
    setLastOpen(key)
    if (open) {
      setErrors({})
      setF(editing
        ? {
            ...(Object.fromEntries(
              Object.keys(blank).map((k) => [k, (editing as unknown as Record<string, unknown>)[k] ?? ""]),
            ) as Form),
            role: editing.role, is_active: editing.is_active,
          }
        : { ...blank, role: roles[0], district: actor?.role === "admin" ? (actor.district ?? "") : "" })
    }
  }

  const needsDistrict = f.role === "admin" || f.role === "user"
  const needsFacility = f.role === "user"
  const set = (k: keyof Form, v: string | boolean) => setF((s) => ({ ...s, [k]: v }))

  async function save() {
    setBusy(true)
    setErrors({})
    try {
      if (editing) {
        const u = await api<User>(`/api/users/${editing.id}`, { method: "PUT", json: f })
        onSaved(undefined, u)
      } else {
        const r = await api<{ user: User; temporary_password: string }>("/api/users", { method: "POST", json: f })
        onSaved(r.temporary_password, r.user)
      }
    } catch (e) {
      const apiErr = e as ApiError
      setErrors(apiErr.fieldErrors)
      toast.error(apiErr.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{editing ? "Edit user" : "Create user"}</DialogTitle>
          <DialogDescription>
            {editing ? "Update details, role or allocation." : "A random one-time password is shown after saving. Give it to the user in person or by phone; they must change it at first sign-in."}
          </DialogDescription>
        </DialogHeader>
        <form className="grid gap-4 sm:grid-cols-2" onSubmit={(e) => { e.preventDefault(); save() }}>
          <Field label="Title" error={errors.title}>
            <NativeSelect value={f.title} placeholder="–" options={["Mr", "Ms", "Mrs", "Miss", "Dr", "Prof"]} onChange={(e) => set("title", e.target.value)} />
          </Field>
          <Field label="Persal number" error={errors.persal_number}>
            <Input inputMode="numeric" maxLength={8} value={f.persal_number} aria-invalid={!!errors.persal_number}
              onChange={(e) => set("persal_number", e.target.value.replace(/\D/g, ""))} />
          </Field>
          <Field label="First name" error={errors.first_name}>
            <Input value={f.first_name} aria-invalid={!!errors.first_name} onChange={(e) => set("first_name", e.target.value)} />
          </Field>
          <Field label="Surname" error={errors.last_name}>
            <Input value={f.last_name} aria-invalid={!!errors.last_name} onChange={(e) => set("last_name", e.target.value)} />
          </Field>
          <Field label="Email" error={errors.email}>
            <Input type="email" value={f.email} aria-invalid={!!errors.email} onChange={(e) => set("email", e.target.value)} />
          </Field>
          <Field label="Mobile number" error={errors.mobile_number}>
            <Input inputMode="tel" maxLength={10} value={f.mobile_number} aria-invalid={!!errors.mobile_number}
              onChange={(e) => set("mobile_number", e.target.value.replace(/\D/g, ""))} />
          </Field>
          <Field label="Designation" error={errors.designation} className="sm:col-span-2">
            <Input value={f.designation} onChange={(e) => set("designation", e.target.value)} />
          </Field>
          <Field label="Role" error={errors.role}>
            <NativeSelect value={f.role} options={roles.map((r) => ({ value: r, label: ROLE_LABEL[r] }))}
              onChange={(e) => setF((s) => ({ ...s, role: e.target.value as Role }))} />
          </Field>
          {needsDistrict ? (
            <Field label="District" error={errors.district}>
              <NativeSelect value={f.district} disabled={isAdmin} placeholder="Select district" options={meta?.districts ?? []}
                aria-invalid={!!errors.district}
                onChange={(e) => setF((s) => ({ ...s, district: e.target.value, local_municipality: "", facility: "" }))} />
            </Field>
          ) : <div className="hidden sm:block" />}
          {needsFacility && (
            <>
              <Field label="Sub-district" error={errors.local_municipality}>
                <NativeSelect value={f.local_municipality} disabled={!f.district} placeholder="Select sub-district"
                  options={meta?.municipalities[f.district] ?? []} aria-invalid={!!errors.local_municipality}
                  onChange={(e) => setF((s) => ({ ...s, local_municipality: e.target.value, facility: "" }))} />
              </Field>
              <Field label="Facility" error={errors.facility}>
                <NativeSelect value={f.facility} disabled={!f.local_municipality} placeholder="Select facility"
                  options={meta?.facilities[f.local_municipality] ?? []} aria-invalid={!!errors.facility}
                  onChange={(e) => set("facility", e.target.value)} />
              </Field>
            </>
          )}
          {editing && (
            <label className="flex items-center gap-3 rounded-lg border p-3 text-sm sm:col-span-2">
              <Switch checked={f.is_active} onCheckedChange={(v) => set("is_active", !!v)} />
              <span>
                Account active
                <span className="block text-xs text-muted-foreground">Deactivating signs the user out immediately.</span>
              </span>
            </label>
          )}
          <DialogFooter className="sm:col-span-2">
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={busy}>{editing ? "Save changes" : "Create user"}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export default function UsersPage() {
  const { user: actor } = useAuth()
  const [q, setQ] = useState("")
  const [page, setPage] = useState(1)
  const [dialog, setDialog] = useState<{ open: boolean; editing: User | null }>({ open: false, editing: null })
  const [temp, setTemp] = useState<{ user: User; password: string } | null>(null)
  const [toDelete, setToDelete] = useState<User | null>(null)
  const { data: meta } = useSWR<Meta>("/api/meta")
  const { data, mutate } = useSWR<Paged<User>>(`/api/users${qs({ q, page, page_size: 20 })}`, { keepPreviousData: true })

  async function action(u: User, path: string, msg: string) {
    try {
      const r = await api<User | { temporary_password: string }>(`/api/users/${u.id}/${path}`, { method: "POST" })
      if ("temporary_password" in r) setTemp({ user: u, password: r.temporary_password })
      else toast.success(msg)
      mutate()
    } catch (e) {
      toast.error((e as Error).message)
    }
  }

  async function confirmDelete() {
    if (!toDelete) return
    try {
      await api(`/api/users/${toDelete.id}`, { method: "DELETE" })
      toast.success("User deleted")
      mutate()
    } catch (e) {
      toast.error((e as Error).message)
    } finally {
      setToDelete(null)
    }
  }

  return (
    <>
      <PageHeader
        title="Users"
        description={actor?.role === "admin" ? `Facility users in ${actor.district} and district users in the province (view only)` : actor?.role === "province" ? "District and facility users in the province" : "All accounts in the province"}
        actions={
          <>
            {can.exportUsers(actor) && (
              <Button variant="outline" onClick={() => download("/api/users/export", "users.xlsx").catch(() => toast.error("Export failed"))}>
                <DownloadIcon /> Excel
              </Button>
            )}
            <Button variant="outline" onClick={() => download("/api/users/application-form", "user_account_application_form.pdf").catch(() => toast.error("Download failed"))}>
              <FileSignatureIcon /> Application form
            </Button>
            {can.changeUsers(actor) && <Button onClick={() => setDialog({ open: true, editing: null })}><PlusIcon /> New user</Button>}
          </>
        }
      />

      <div className="relative mb-3">
        <SearchIcon className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input className="pl-8" placeholder="Search name, Persal number, district or facility…" value={q}
          onChange={(e) => { setQ(e.target.value); setPage(1) }} />
      </div>

      <Card className="py-0">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead><TableHead>Persal</TableHead><TableHead>Role</TableHead>
                <TableHead>Allocation</TableHead><TableHead>Status</TableHead><TableHead>Last sign-in</TableHead>
                <TableHead className="w-12" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.items.length === 0 && <TableRow><TableCell colSpan={7} className="py-10 text-center text-muted-foreground">No users found.</TableCell></TableRow>}
              {data?.items.map((u) => (
                <TableRow key={u.id}>
                  <TableCell>
                    <div className="font-medium">{u.title} {u.first_name} {u.last_name}</div>
                    <div className="text-xs text-muted-foreground">{u.designation ?? u.email ?? ""}</div>
                  </TableCell>
                  <TableCell className="font-mono text-sm">{u.persal_number}</TableCell>
                  <TableCell><Badge variant="outline">{ROLE_LABEL[u.role]}</Badge></TableCell>
                  <TableCell className="max-w-56 text-sm">
                    <div className="truncate">{u.facility ?? u.district ?? "Province"}</div>
                    {u.facility && <div className="truncate text-xs text-muted-foreground">{u.district}</div>}
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {!u.is_active && <Badge variant="secondary">Inactive</Badge>}
                      {isLocked(u) && <Badge variant="destructive"><LockIcon /> Locked</Badge>}
                      {u.must_change_password && <Badge variant="outline"><KeyRoundIcon /> Temp password</Badge>}
                      {u.is_active && !isLocked(u) && !u.must_change_password && <Badge variant="outline" className="text-status-good">Active</Badge>}
                    </div>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">{timeAgo(u.last_login_at)}</TableCell>
                  <TableCell>
                    {!can.manageUser(actor, u) ? (
                      <span className="text-xs whitespace-nowrap text-muted-foreground">View only</span>
                    ) : (
                    <DropdownMenu>
                      <DropdownMenuTrigger render={<Button variant="ghost" size="icon-sm" aria-label="Actions" />}>
                        <MoreHorizontalIcon />
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-52">
                        {can.changeUsers(actor) && <DropdownMenuItem onClick={() => setDialog({ open: true, editing: u })}><PencilIcon /> Edit</DropdownMenuItem>}
                        <DropdownMenuItem onClick={() => action(u, "reset-password", "")}><KeyRoundIcon /> Reset password</DropdownMenuItem>
                        {isLocked(u) && <DropdownMenuItem onClick={() => action(u, "unlock", "Account unlocked")}><LockOpenIcon /> Unlock account</DropdownMenuItem>}
                        <DropdownMenuItem onClick={() => action(u, "revoke-sessions", "Sessions revoked")}><LogOutIcon /> Sign out all sessions</DropdownMenuItem>
                        {u.id !== actor?.id && can.changeUsers(actor) && (
                          <>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem variant="destructive" onClick={() => setToDelete(u)}><Trash2Icon /> Delete</DropdownMenuItem>
                          </>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </Card>
      {data && <Pagination page={page} pageSize={20} total={data.total} onPage={setPage} />}

      <UserDialog
        open={dialog.open}
        editing={dialog.editing}
        meta={meta}
        actor={actor}
        onClose={() => setDialog({ open: false, editing: null })}
        onSaved={(pw, u) => {
          setDialog({ open: false, editing: null })
          mutate()
          if (pw && u) setTemp({ user: u, password: pw })
          else toast.success("User updated")
        }}
      />

      <Dialog open={!!temp} onOpenChange={(o) => !o && setTemp(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>One-time password</DialogTitle>
            <DialogDescription>
              {temp?.user.first_name} {temp?.user.last_name} can now sign in with their Persal number and this password. It is shown only once: give it to them in person or by phone, never by e-mail or group chat. They must change it at first sign-in.
            </DialogDescription>
          </DialogHeader>
          <div className="flex items-center gap-2 rounded-lg border bg-muted/50 p-3">
            <code className="flex-1 font-mono text-lg tracking-wider">{temp?.password}</code>
            <Button variant="outline" size="sm" onClick={() => { navigator.clipboard.writeText(temp?.password ?? ""); toast.success("Copied") }}>
              <CopyIcon /> Copy
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">Sign-in: Persal number {temp?.user.persal_number}</p>
          <DialogFooter><Button onClick={() => setTemp(null)}>Done</Button></DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={!!toDelete} onOpenChange={(o) => !o && setToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete {toDelete?.first_name} {toDelete?.last_name}?</AlertDialogTitle>
            <AlertDialogDescription>
              Records they captured are kept. Consider deactivating instead if they may return.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={confirmDelete}>Delete user</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
