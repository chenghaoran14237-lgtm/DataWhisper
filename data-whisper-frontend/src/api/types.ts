export interface ExcelProfile {
  rows: number;
  cols: number;
  columns: string[];
  dtypes: Record<string, string>;
  missing_rate: Record<string, number>;
  preview: Record<string, any>[];
}

export interface ExcelUploadResponse {
  session_id: string;
  upload_id: string;
  filename: string;
  profile: ExcelProfile;
}

export interface ChartSpecLine {
  type: "line";
  x: { name: string; values: string[] };
  series: { name: string; values: (number | null)[] }[];
}

export interface Artifact {
  kind: "chart";
  spec: ChartSpecLine; 
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  artifacts: Artifact[];
}

export interface MessagesPage {
  items: ChatMessage[];
  next_cursor: string | null;
  has_more: boolean;
}