export interface AbsenceStatus {
  guard_id: number;
  name: string;
  is_out: boolean;
  left_at: string | null;
  absence_id: number | null;
  total_exits: number;
}
