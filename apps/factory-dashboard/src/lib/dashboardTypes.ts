export type TruthLayer = "canonical" | "advisory" | "derived";

export interface DashboardItem {
  id: string;
  title?: string;
  label?: string;
  summary: string;
  status?: string;
  truth_layer?: TruthLayer;
  details?: string[];
  environment?: string;
  source_kind?: string;
  source_path?: string[];
}

export interface DashboardSection {
  title?: string;
  items?: DashboardItem[];
  cards?: DashboardItem[];
  warnings?: string[];
}

export interface DashboardSnapshot {
  schema_version: string;
  dashboard_build_id: string;
  generated_at: string;
  source_trace: unknown[];
  what_matters_most: DashboardItem;
  environment_board: DashboardSection;
  quality_now: DashboardSection;
  automation_now: DashboardSection;
  factory_learning: DashboardSection;
  agent_memory: DashboardSection;
  ideas_lab: DashboardSection;
  recent_motion: DashboardSection;
  focused_portfolio: Record<string, DashboardItem[]>;
  mismatch_warnings: string[];
}
