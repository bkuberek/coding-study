// A work order: one job of maintenance at one site.

export type Priority = "low" | "normal" | "high";

export interface WorkOrder {
  readonly id: string;
  readonly siteId: string;
  title: string;
  priority: Priority;
  assignee: string | null;
  laborMinutes: number;
  version: number;
}

export interface NewWorkOrder {
  readonly title: string;
  readonly siteId: string;
  readonly priority: Priority;
  readonly assignee: string | null;
  readonly laborMinutes: number;
}
