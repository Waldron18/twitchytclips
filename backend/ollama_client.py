"""
ollama_client.py - Local LLM integration for ClipForge Local via Ollama REST API (11434).
Evaluates viral hooks, trims dead air at word boundaries, and generates high-CTR titles and hashtags.
Includes a robust offline rule-based NLP fallback if Ollama is not active.
"""
import json
import logging
import re
from typing import Dict, Any, List, Optional
import requests
from backend.config import OLLAMA_BASE_URL
from backend.hardware_profiler import detect_hardware_profile

logger = logging.getLogger("clipforge.ollama")

class OllamaClient:
    def __init__(self, base_url: str = OLLAMA_BASE_URL):
        self.base_url = base_url.rstrip("/")

    def is_online(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    def get_installed_models(self) -> List[str]:
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=3)
            if r.status_code == 200:
                models = r.json().get("models", [])
                return [m.get("name") for m in models if m.get("name")]
        except Exception:
            pass
        return []

    def pull_model(self, model_name: str) -> bool:
        """Requests Ollama to pull a model."""
        try:
            r = requests.post(f"{self.base_url}/api/pull", json={"name": model_name, "stream": False}, timeout=120)
            return r.status_code == 200
        except Exception as e:
            logger.warning(f"Failed to pull model {model_name}: {e}")
            return False

    def query(self, prompt: str, system_prompt: str = "", model_override: Optional[str] = None) -> Optional[str]:
        if not self.is_online():
            return None

        profile = detect_hardware_profile()
        model = model_override or profile.ollama_model

        # Check if model exists, if not fallback to any installed model
        installed = self.get_installed_models()
        if installed and model not in installed and not any(m.startswith(model.split(":")[0]) for m in installed):
            # Fallback to first available model
            model = installed[0]

        payload = {
            "model": model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": 0.4,
                "top_p": 0.9,
                "num_ctx": 4096
            }
        }

        try:
            res = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=45)
            if res.status_code == 200:
                return res.json().get("response", "").strip()
        except Exception as e:
            logger.warning(f"Ollama query failed: {e}")
        return None

    def rank_viral_hooks(self, transcript_segments: List[Dict[str, Any]], max_candidates: int = 5) -> List[Dict[str, Any]]:
        """
        Uses Ollama LLM to evaluate transcript windows for viral potential.
        Returns ranked clip recommendations with start/end timestamps and hook summaries.
        """
        # Prepare readable transcript with timestamp blocks
        formatted_blocks = []
        for seg in transcript_segments:
            formatted_blocks.append(f"[{round(seg['start'], 1)}s - {round(seg['end'], 1)}s]: {seg['text']}")
        transcript_text = "\n".join(formatted_blocks)

        system_prompt = (
            "You are an elite short-form video producer specializing in YouTube Shorts and Instagram Reels. "
            "Your job is to identify high-retention, viral moments from stream transcripts. "
            "A viral clip MUST have: a punchy opening hook (0-3s), rising tension/humor/drama, and a satisfying punchline or resolution. "
            "Target clip length is strictly between 15 and 60 seconds. "
            "Always return strictly valid JSON format matching the schema."
        )

        prompt = (
            f"Analyze the following timestamped video transcript and identify the top {max_candidates} viral clip opportunities:\n\n"
            f"{transcript_text[:5000]}\n\n"
            "Respond ONLY with a JSON array of objects with the following keys:\n"
            "[\n"
            "  {\n"
            '    "start_time": float,\n'
            '    "end_time": float,\n'
            '    "hook": "exact opening hook line",\n'
            '    "title": "High-CTR click-worthy title (under 50 chars) with emojis",\n'
            '    "reason": "why this clip will perform well",\n'
            '    "score": float between 70 and 100\n'
            "  }\n"
            "]\n"
            "No markdown, no explanation, only raw JSON."
        )

        response = self.query(prompt, system_prompt)
        if response:
            try:
                # Clean possible markdown fence
                clean = re.sub(r"^```json\s*", "", response)
                clean = re.sub(r"^```\s*", "", clean)
                clean = re.sub(r"```$", "", clean).strip()
                data = json.loads(clean)
                if isinstance(data, list) and len(data) > 0:
                    return data
            except Exception as e:
                logger.warning(f"Could not parse Ollama JSON response: {e}")

        # Fallback to heuristic scoring if Ollama is offline or unparseable
        return self._heuristic_hook_detection(transcript_segments, max_candidates)

    def generate_clip_metadata(self, clip_text: str) -> Dict[str, str]:
        """Generates viral title, description, and hashtags for an extracted clip."""
        system_prompt = (
            "You are a social media copywriter. Generate high-CTR titles, engaging captions, "
            "and trending hashtags for YouTube Shorts and Instagram Reels."
        )
        prompt = (
            f"Transcript of the clip:\n\"{clip_text}\"\n\n"
            "Generate optimized metadata in JSON format:\n"
            "{\n"
            '  "title": "High-CTR title with emojis (max 60 chars)",\n'
            '  "description": "2-sentence punchy engaging video description",\n'
            '  "hashtags": "#shorts #reels #viral #gaming (5-8 relevant tags)"\n'
            "}\n"
            "Output JSON only."
        )
        resp = self.query(prompt, system_prompt)
        if resp:
            try:
                clean = re.sub(r"^```json\s*", "", resp)
                clean = re.sub(r"^```\s*", "", clean)
                clean = re.sub(r"```$", "", clean).strip()
                return json.loads(clean)
            except Exception:
                pass

        # Heuristic fallback
        words = clip_text.split()
        short_title = " ".join(words[:6]).upper() + " 😱🔥"
        return {
            "title": short_title if len(short_title) < 55 else short_title[:50] + "... 🔥",
            "description": f"You won't believe what happened here! Watch until the end. Like and subscribe for more daily clips!",
            "hashtags": "#shorts #reels #gaming #viral #funny #clipforge"
        }

    def _heuristic_hook_detection(self, segments: List[Dict[str, Any]], max_candidates: int) -> List[Dict[str, Any]]:
        """
        Algorithmic fallback for when Ollama is offline.
        Uses keyword sentiment, punctuation markers, speech velocity, and duration constraints.
        """
        HYPE_KEYWORDS = {
            "what": 1.5, "no way": 3.0, "insane": 3.0, "omg": 3.0, "bro": 1.8,
            "look": 2.0, "holy": 2.5, "clutch": 3.0, "hacker": 2.5, "dead": 1.5,
            "funny": 1.5, "crazy": 2.5, "win": 2.0, "fail": 2.5, "shut up": 2.0,
            "oh my god": 3.0, "wow": 2.0, "impossible": 2.5, "cheat": 2.0
        }

        candidates = []
        n = len(segments)
        if n == 0:
            return []

        # Sliding window across segments targeting 20-45 second chunks
        for i in range(n):
            cur_start = segments[i]["start"]
            for j in range(i, min(i + 15, n)):
                cur_end = segments[j]["end"]
                dur = cur_end - cur_start
                if 18.0 <= dur <= 55.0:
                    text_chunk = " ".join(s["text"] for s in segments[i:j+1])
                    lower_text = text_chunk.lower()

                    score = 65.0
                    for kw, weight in HYPE_KEYWORDS.items():
                        if kw in lower_text:
                            score += weight * 4.0

                    # Punctuation indicators
                    score += text_chunk.count("!") * 3.5
                    score += text_chunk.count("?") * 2.0

                    # First segment hook quality
                    first_seg = segments[i]["text"]
                    hook_phrase = " ".join(first_seg.split()[:8])

                    candidates.append({
                        "start_time": cur_start,
                        "end_time": cur_end,
                        "hook": hook_phrase,
                        "title": f"NO WAY THIS HAPPENED?! 😱 #{i+1}",
                        "reason": "High density of speech reactions and excitement markers",
                        "score": min(round(score, 1), 99.0)
                    })

        # Sort by score descending and deduplicate overlapping candidates
        candidates.sort(key=lambda x: x["score"], reverse=True)
        filtered = []
        for c in candidates:
            # Check overlap with existing chosen candidates
            overlap = False
            for existing in filtered:
                # If overlap > 12 seconds, skip
                if not (c["end_time"] <= existing["start_time"] or c["start_time"] >= existing["end_time"]):
                    overlap = True
                    break
            if not overlap:
                filtered.append(c)
            if len(filtered) >= max_candidates:
                break

        # If none matched 18-55s duration, take the whole duration or segments
        if not filtered and n > 0:
            total_dur = segments[-1]["end"] - segments[0]["start"]
            clip_len = min(total_dur, 45.0)
            filtered.append({
                "start_time": segments[0]["start"],
                "end_time": segments[0]["start"] + clip_len,
                "hook": segments[0]["text"][:40],
                "title": "INSANE MOMENT CAUGHT ON STREAM 🔥",
                "reason": "Opening segment of the clip",
                "score": 85.0
            })

        return filtered

# Singleton instance
ollama_client = OllamaClient()
