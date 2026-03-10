export interface AbsenceStatus {
  guard_id: number;
  name: string;
  is_out: boolean;
  left_at: string | null;
  absence_id: number | null;
  reason: string | null;
  total_exits: number;
}

export interface AbsenceHistory {
  id: number;
  guard_id: number;
  name: string;
  left_at: string;
  returned_at: string | null;
  reason: string | null;
  duration_min: number | null;
}

export interface Settings {
  alert_minutes: number | null;
}
