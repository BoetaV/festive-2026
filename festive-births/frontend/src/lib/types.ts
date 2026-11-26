export type Role = "superuser" | "province" | "admin" | "user"

export interface User {
  id: number
  persal_number: string
  first_name: string
  last_name: string
  email: string | null
  title: string | null
  designation: string | null
  mobile_number: string | null
  role: Role
  district: string | null
  local_municipality: string | null
  facility: string | null
  is_active: boolean
  must_change_password: boolean
  last_login_at: string | null
  locked_until: string | null
  failed_login_attempts: number
  created_at: string
  /** The season's data is read-only (after DATA_LOCK_AT). */
  data_locked: boolean
}

export interface Paged<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface Baby {
  id?: number
  gender: "Male" | "Female" | null
  weight: number | null
}

export interface Delivery {
  id: number
  district: string
  local_municipality: string | null
  facility: string | null
  facility_type: string | null
  report_date: string
  time_slot: string | null
  no_births_to_report: boolean
  born_before_arrival: boolean
  delivery_time: string | null
  mother_name: string | null
  mother_surname: string | null
  mother_dob: string | null
  mother_age: number | null
  birth_mode: string | null
  gravidity: number | null
  parity: number | null
  babies: Baby[]
  captured_by_name: string | null
  created_at: string
  updated_at: string
}

export interface Meta {
  districts: string[]
  municipalities: Record<string, string[]>
  facilities: Record<string, string[]>
  facility_types: Record<string, string>
  report_dates: string[]
  time_slots: string[]
  birth_modes: string[]
  data_lock_at: string | null
  data_locked: boolean
}

export interface MF {
  name: string
  male: number
  female: number
  total: number
}

export interface Dashboard {
  scope: { name: string; level: string }
  kpis: {
    total_births: number
    males: number
    females: number
    deliveries: number
    nil_reports: number
    facilities_reporting: number
    multiple_birth_sets: number
    low_birth_weight: number
    low_birth_weight_rate: number | null
    teen_births: number
    teen_birth_rate: number | null
    caesarean_rate: number | null
    born_before_arrival: number
    average_weight: number | null
  }
  by_area: MF[]
  age_groups: MF[]
  birth_modes: MF[]
  time_slots: MF[]
  facility_types: MF[]
  weight_bands: MF[]
  by_date: MF[]
  by_hour: { hour: number; total: number }[]
  teen_by_facility: { facility: string; age_10_14: number; age_15_19: number }[]
  multiple_births: { facility: string; twins: number; triplets: number; quadruplets: number; quintuplets: number }[]
  last_updated: string | null
}

export interface AuditEntry {
  id: number
  created_at: string
  user_id: number | null
  persal_number: string | null
  user_name: string | null
  action: string
  success: boolean
  ip_address: string | null
  user_agent: string | null
  detail: string | null
}

export const ROLE_LABEL: Record<Role, string> = {
  superuser: "Superuser",
  province: "Province",
  admin: "District User",
  user: "Facility User",
}

// ---------------------------------------------------------------- reporting per time slot
export type SlotStatus = "births" | "nil" | "missing" | "pending"
export type SlotCounts = Record<SlotStatus, number>
export interface ReportingFacility {
  name: string; facility_type: string | null; outstanding: number
  slots: { status: SlotStatus; births: number }[]
}
export interface ReportingArea { name: string; facility_count: number; slots: SlotCounts[]; outstanding: number }
export interface ReportingMunicipality extends ReportingArea { facilities: ReportingFacility[] }
export interface ReportingDistrict extends ReportingArea { municipalities: ReportingMunicipality[] }
export interface Reporting {
  report_date: string; time_slots: string[]; as_at: string; slots_due: boolean[]
  facility_count: number; totals: SlotCounts[]; outstanding: number; districts: ReportingDistrict[]
}
