export interface Guard {
  id: number;
  name: string;
  phone: string | null;
  role: string | null;
  is_active: boolean;
  past: number;
  future: number;
  total: number;
  overloaded: boolean;
}

export interface Shift {
  id: number;
  start_time: string;
  end_time: string;
  names: string[];
  is_past: boolean;
}

export interface Stats {
  total_shifts: number;
  total_past: number;
  total_future: number;
  active_guards: number;
  overload_threshold: number;
  guards: GuardStat[];
}

export interface GuardStat {
  name: string;
  past: number;
  future: number;
  total: number;
  overloaded: boolean;
}

export interface Suggestion {
  name: string;
  past: number;
  future: number;
  total: number;
  last_past_date: string | null;
  overloaded: boolean;
}

export interface StagedShift {
  start_time: string;
  end_time: string;
  names: string[];
}

