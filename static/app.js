const form = document.getElementById("job-form");
const jobsEl = document.getElementById("jobs");

const STATUS_LABEL = {
  queued: "Queued",
  downloading: "Downloading video",
  uploading: "Uploading",
  analyzing: "Analyzing with Gemini (can take a minute or two)",
  clipping: "Cutting clips",
  done: "Done",
  error: "Error",
};

const ACTIVE_STATUSES = new Set(["queued", "downloading", "uploading", "analyzing", "clipping"]);
let currentJobId = null;
let pollTimer = null;

function clipCard(jobId, clip) {
  return `
    <div class="clip-card">
      <video controls preload="metadata" src="/api/jobs/${jobId}/clips/${clip.filename}"></video>
      <h4>${escapeHtml(clip.title)}</h4>
      <p>${formatTime(clip.start_s)} - ${formatTime(clip.end_s)}</p>
      <p>${escapeHtml(clip.reason)}</p>
      <p class="clip-filename">${escapeHtml(clip.filename)}</p>
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
  const isActive = ACTIVE_STATUSES.has(job.status);
  const badgeClass = job.status === "done" ? "done" : job.status === "error" ? "error" : "";
  const label = STATUS_LABEL[job.status] || job.status;
  const clips = (job.clips || []).map((c) => clipCard(job.id, c)).join("");
  const error = job.error ? `<p class="job-error">${escapeHtml(job.error)}</p>` : "";

  const downloadAll =
    (job.clips || []).length > 1
      ? `<a class="download-all-btn" href="/api/jobs/${job.id}/clips.zip" download>Download all (${job.clips.length})</a>`
      : "";

  const statusLine = isActive
    ? `<div class="status-line"><span class="spinner"></span>${escapeHtml(label)}&hellip;</div>`
    : "";

  return `
    <div class="job-card" data-job-id="${job.id}">
      <div class="job-header">
        <div>
          <div class="job-source">${escapeHtml(job.source)}</div>
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
          <span class="status-badge ${badgeClass}">${label}</span>
          ${downloadAll}
          <button class="delete-btn" data-delete="${job.id}">Delete</button>
        </div>
      </div>
      ${statusLine}
      ${error}
      ${clips ? `<div class="clip-grid">${clips}</div>` : ""}
    </div>
  `;
}

function renderJob(job) {
  jobsEl.innerHTML = job ? jobCard(job) : "";
}

async function pollCurrentJob() {
  if (!currentJobId) return;
  try {
    const res = await fetch(`/api/jobs/${currentJobId}`);
    if (!res.ok) {
      currentJobId = null;
      renderJob(null);
      return;
    }
    const job = await res.json();
    renderJob(job);
    if (!ACTIVE_STATUSES.has(job.status) && pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  } catch {
    // transient fetch failure, retry on next tick
  }
}

function startPolling() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(pollCurrentJob, 2000);
}

async function loadMostRecentJob() {
  const res = await fetch("/api/jobs");
  const jobs = await res.json();
  if (jobs.length) {
    currentJobId = jobs[0].id;
    renderJob(jobs[0]);
    if (ACTIVE_STATUSES.has(jobs[0].status)) startPolling();
  }
}

jobsEl.addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-delete]");
  if (!btn) return;
  await fetch(`/api/jobs/${btn.dataset.delete}`, { method: "DELETE" });
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
  currentJobId = null;
  renderJob(null);
});

const maxClipsInput = document.getElementById("max-clips");
const minLengthInput = document.getElementById("min-length");
const maxLengthInput = document.getElementById("max-length");
let defaults = { max_clips: 5, hard_max_clips: 20, min_length_s: 15, max_length_s: 90 };

async function loadDefaults() {
  try {
    const res = await fetch("/api/defaults");
    defaults = await res.json();
  } catch {
    // keep built-in fallback defaults
  }
  maxClipsInput.value = defaults.max_clips;
  maxClipsInput.max = defaults.hard_max_clips;
  minLengthInput.value = defaults.min_length_s;
  maxLengthInput.value = defaults.max_length_s;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const url = document.getElementById("url").value.trim();
  const fileInput = document.getElementById("file");
  const vertical = document.getElementById("vertical").checked;
  const maxClips = Number(maxClipsInput.value);
  const minLength = Number(minLengthInput.value);
  const maxLength = Number(maxLengthInput.value);

  if (!url && !fileInput.files.length) {
    alert("Provide a URL or choose a file");
    return;
  }
  if (minLength > maxLength) {
    alert("Min length cannot be greater than max length");
    return;
  }

  const fd = new FormData();
  if (url) fd.append("url", url);
  if (fileInput.files.length) fd.append("file", fileInput.files[0]);
  fd.append("vertical", vertical ? "true" : "false");
  fd.append("max_clips", String(maxClips));
  fd.append("min_length_s", String(minLength));
  fd.append("max_length_s", String(maxLength));

  const submitBtn = form.querySelector("button[type=submit]");
  submitBtn.disabled = true;
  try {
    const res = await fetch("/api/jobs", { method: "POST", body: fd });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      throw new Error(detail.detail || "Failed to create job");
    }
    const job = await res.json();

    currentJobId = job.id;
    renderJob(job);
    startPolling();

    form.reset();
    document.getElementById("vertical").checked = true;
    await loadDefaults();
  } catch (err) {
    alert(err.message);
  } finally {
    submitBtn.disabled = false;
  }
});

loadDefaults();
loadMostRecentJob();
