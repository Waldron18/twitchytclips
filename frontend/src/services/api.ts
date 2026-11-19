import { HardwareProfile, Project, Clip, Job, MusicTrack, CleanupStats, OllamaStatus } from '../types';

const API_BASE = '/api';

export const api = {
  async getHardware(): Promise<HardwareProfile> {
    const res = await fetch(`${API_BASE}/hardware`);
    if (!res.ok) throw new Error('Failed to fetch hardware profile');
    return res.json();
  },

  async overrideTier(tier: string): Promise<HardwareProfile> {
    const res = await fetch(`${API_BASE}/hardware/override`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tier })
    });
    return res.json();
  },

  async getOllamaStatus(): Promise<OllamaStatus> {
    const res = await fetch(`${API_BASE}/ollama/status`);
    return res.json();
  },

  async pullOllamaModel(model?: string): Promise<{ model: string; success: boolean }> {
    const res = await fetch(`${API_BASE}/ollama/pull`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model })
    });
    return res.json();
  },

  async createProject(
    sourceUrl: string,
    storageSaver?: boolean,
    targetClips: number = 5,
    liveCaptureMinutes: number = 1,
    liveCaptureSeconds?: number
  ): Promise<{ project_id: string; job_id: string }> {
    const res = await fetch(`${API_BASE}/projects/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source_url: sourceUrl,
        storage_saver: storageSaver,
        target_clips: targetClips,
        live_capture_duration_minutes: liveCaptureMinutes,
        live_capture_seconds: liveCaptureSeconds
      })
    });
    if (!res.ok) throw new Error('Failed to create project');
    return res.json();
  },

  async uploadFile(file: File): Promise<{ project_id: string; job_id: string }> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/projects/upload`, {
      method: 'POST',
      body: formData
    });
    if (!res.ok) throw new Error('Upload failed');
    return res.json();
  },

  async getProjects(): Promise<Project[]> {
    const res = await fetch(`${API_BASE}/projects`);
    return res.json();
  },

  async getProject(id: string): Promise<Project> {
    const res = await fetch(`${API_BASE}/projects/${id}`);
    if (!res.ok) throw new Error('Project not found');
    return res.json();
  },

  async deleteProject(id: string): Promise<void> {
    await fetch(`${API_BASE}/projects/${id}`, { method: 'DELETE' });
  },

  async updateClip(clipId: string, data: Partial<Clip>): Promise<Clip> {
    const res = await fetch(`${API_BASE}/clips/${clipId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return res.json();
  },

  async renderClip(clipId: string): Promise<{ job_id: string; status: string }> {
    const res = await fetch(`${API_BASE}/clips/${clipId}/render`, { method: 'POST' });
    return res.json();
  },

  async getMusicTracks(): Promise<MusicTrack[]> {
    const res = await fetch(`${API_BASE}/music/tracks`);
    return res.json();
  },

  async getJobs(): Promise<Job[]> {
    const res = await fetch(`${API_BASE}/jobs`);
    return res.json();
  },

  async cancelJob(jobId: string): Promise<{ job_id: string; success: boolean }> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/cancel`, { method: 'POST' });
    return res.json();
  },

  async clearJobs(): Promise<{ cleared: number }> {
    const res = await fetch(`${API_BASE}/jobs/clear`, { method: 'POST' });
    return res.json();
  },

  async getCleanupStats(): Promise<CleanupStats> {
    const res = await fetch(`${API_BASE}/system/cleanup`);
    return res.json();
  },

  async executeCleanup(): Promise<{ status: string; freed_mb: number; current_free_disk_gb: number }> {
    const res = await fetch(`${API_BASE}/system/cleanup`, { method: 'POST' });
    return res.json();
  }
};
