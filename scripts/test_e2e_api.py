"""
test_e2e_api.py - Tests end-to-end API pipeline creation and clip extraction.
"""
import time
import requests

def test_api():
    print("Testing ClipForge Local API on http://127.0.0.1:8001 ...")
    # 1. Create project with synthetic video
    res = requests.post("http://127.0.0.1:8001/api/projects/create", json={
        "source_url": "temp/synthetic_test.mp4",
        "storage_saver": False,
        "target_clips": 1
    }).json()
    print("Project submission response:", res)
    project_id = res["project_id"]
    job_id = res["job_id"]

    # 2. Poll job status
    print(f"Monitoring Job {job_id}...")
    for _ in range(30):
        time.sleep(1.0)
        jobs = requests.get("http://127.0.0.1:8001/api/jobs").json()
        matching = [j for j in jobs if j["id"] == job_id]
        if not matching:
            continue
        job = matching[0]
        print(f" -> Progress: {job['progress']}%, Status: {job['status']}, Step: {job['current_step']}")
        if job["status"] in ["completed", "failed"]:
            break

    # 3. Verify Project and Clips
    project = requests.get(f"http://127.0.0.1:8001/api/projects/{project_id}").json()
    print("\nProject Details:")
    print(f" - Title: {project['title']}")
    print(f" - Platform: {project['platform']}")
    print(f" - Status: {project['status']}")
    print(f" - Extracted Clips: {len(project.get('clips', []))}")

    if project.get("clips"):
        c = project["clips"][0]
        print(f" -> Clip 1 Title: {c['title']}")
        print(f" -> Duration: {c['duration']}s ({c['start_time']}s -> {c['end_time']}s)")
        print(f" -> Hype Score: {c['hype_score']}")
        print(f" -> Facecam: {c['facecam_rect']}")
        print(f" -> Words aligned: {len(c['words'])}")

        # 4. Trigger 9:16 Render
        print("\nTriggering 9:16 vertical render for Clip 1...")
        r_res = requests.post(f"http://127.0.0.1:8001/api/clips/{c['id']}/render").json()
        render_job_id = r_res["job_id"]
        for _ in range(30):
            time.sleep(1.0)
            jobs = requests.get("http://127.0.0.1:8001/api/jobs").json()
            matching = [j for j in jobs if j["id"] == render_job_id]
            if not matching:
                continue
            r_job = matching[0]
            print(f" -> Render Progress: {r_job['progress']}%, Step: {r_job['current_step']}")
            if r_job["status"] in ["completed", "failed"]:
                break

        updated_project = requests.get(f"http://127.0.0.1:8001/api/projects/{project_id}").json()
        rendered_clip = updated_project["clips"][0]
        print(f"Rendered Clip Status: {rendered_clip['status']}")
        print(f"Rendered Video Path: {rendered_clip['rendered_video_path']}")
        assert rendered_clip["has_rendered"] is True, "Render flag was not updated to True!"
        print("\n[SUCCESS] Full End-to-End API Pipeline Verified 100%!")

if __name__ == "__main__":
    test_api()
