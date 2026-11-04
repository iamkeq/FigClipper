const form = document.getElementById("job-form");
const jobsEl = document.getElementById("jobs");

const STATUS_LABEL = {
  queued: "Queued",
  downloading: "Downloading",
  uploading: "Uploading",
  analyzing: "Analyzing with Gemini",
  clipping: "Cutting clips",
  done: "Done",
  error: "Error",
};

function clipCard(jobId, clip) {
  return `
    <div class="clip-card">
      <video controls preload="metadata" src="/api/jobs/${jobId}/clips/${clip.filename}"></video>
      <h4>${escapeHtml(clip.title)}</h4>
      <p>${formatTime(clip.start_s)} - ${formatTime(clip.end_s)}</p>
      <p>${escapeHtml(clip.reason)}</p>
      <a href="/api/jobs/${jobId}/clips/${clip.filename}" download>Download</a>
    </div>
  `;
}

function formatTime(s) {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60).toString().padStart(2, "0");
  return `${m}:${sec}`;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

function jobCard(job) {
  const badgeClass = job.status === "done" ? "done" : job.status === "error" ? "error" : "";
  const label = STATUS_LABEL[job.status] || job.status;
  const clips = (job.clips || []).map((c) => clipCard(job.id, c)).join("");
  const error = job.error ? `<p class="job-error">${escapeHtml(job.error)}</p>` : "";

  return `
    <div class="job-card" data-job-id="${job.id}">
      <div class="job-header">
        <div>
          <div class="job-source">${escapeHtml(job.source)}</div>
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
          <span class="status-badge ${badgeClass}">${label}</span>
          <button class="delete-btn" data-delete="${job.id}">Delete</button>
        </div>
      </div>
      ${error}
      ${clips ? `<div class="clip-grid">${clips}</div>` : ""}
    </div>
  `;
}

async function refreshJobs() {
  const res = await fetch("/api/jobs");
  const jobs = await res.json();
  jobsEl.innerHTML = jobs.map(jobCard).join("");
}

jobsEl.addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-delete]");
  if (!btn) return;
  await fetch(`/api/jobs/${btn.dataset.delete}`, { method: "DELETE" });
  refreshJobs();
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const url = document.getElementById("url").value.trim();
  const fileInput = document.getElementById("file");
  const vertical = document.getElementById("vertical").checked;

  if (!url && !fileInput.files.length) {
    alert("Provide a URL or choose a file");
    return;
  }

  const fd = new FormData();
  if (url) fd.append("url", url);
  if (fileInput.files.length) fd.append("file", fileInput.files[0]);
  fd.append("vertical", vertical ? "true" : "false");

  const submitBtn = form.querySelector("button[type=submit]");
  submitBtn.disabled = true;
  try {
    const res = await fetch("/api/jobs", { method: "POST", body: fd });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      throw new Error(detail.detail || "Failed to create job");
    }
    form.reset();
    document.getElementById("vertical").checked = true;
    await refreshJobs();
  } catch (err) {
    alert(err.message);
  } finally {
    submitBtn.disabled = false;
  }
});

refreshJobs();
setInterval(refreshJobs, 2500);
