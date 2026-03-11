export interface RotationRole {
  id: number;
  name: string;
  position: number;
  slots: string[][]; // [slot0_names, slot1_names, slot2_names]
}

export interface RotationConfig {
  start_date: string;   // "YYYY-MM-DD"
  period_days: number;
  roles: RotationRole[];
}

export interface RotationPeriod {
  start: Date;
  end: Date;
  slotIndex: number; // 0, 1, or 2
  label: string;     // "08/3-10/3"
  isActive: boolean; // current period
}
