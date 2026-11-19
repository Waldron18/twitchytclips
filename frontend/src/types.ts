export interface HardwareProfile {
  tier: 'LOW' | 'MID' | 'HIGH';
  gpu_name: string;
  vram_gb: number;
  ram_gb: number;
  has_nvenc: boolean;
  whisper_model: string;
  whisper_compute_type: string;
  whisper_device: string;
  ollama_model: string;
  ffmpeg_video_encoder: string;
  storage_saver_mode: boolean;
  free_disk_gb: number;
  recommendations: string[];
}

export interface WordToken {
  word: string;
  start: number;
  end: number;
  probability?: number;
  deleted?: boolean;
}

export interface FacecamRect {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface Clip {
  id: string;
  project_id: string;
  title: string;
  hook_summary: string | null;
  description: string | null;
  hashtags: string;
  start_time: number;
  end_time: number;
  duration: number;
  hype_score: number;
  viral_rank: number;
  facecam_rect: FacecamRect | null;
  has_facecam: boolean;
  subtitle_style: 'karaoke_yellow' | 'clean_white' | 'neon_green';
  bgm_track: string;
  bgm_volume_db: number;
  rendered_video_path: string | null;
  has_rendered: boolean;
  status: 'candidate' | 'rendering' | 'ready' | 'failed';
  error_message?: string;
  words: WordToken[];
  created_at: string;
}

export interface Project {
  id: string;
  title: string;
  source_url: string;
  platform: string;
  duration: number;
  status: 'created' | 'ingesting' | 'transcribing' | 'analyzing' | 'ready' | 'failed';
  error_message?: string;
  created_at: string;
  clip_count: number;
  clips?: Clip[];
}

export interface Job {
  id: string;
  project_id?: string;
  clip_id?: string;
  job_type: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  progress: number;
  current_step: string;
  error?: string;
  created_at: string;
}

export interface MusicTrack {
  filename: string;
  name: string;
  url: string;
}

export interface CleanupStats {
  temp_usage_mb: number;
  exports_usage_mb: number;
  free_disk_gb: number;
}

export interface OllamaStatus {
  online: boolean;
  base_url: string;
  recommended_model: string;
  installed_models: string[];
}
