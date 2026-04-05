const state = {
    jobId: null,
    nextFrom: 0,
    pollTimer: null,
};

const els = {
    form: document.getElementById("portForm"),
    noticeBar: document.getElementById("noticeBar"),
    baseRom: document.getElementById("baseRom"),
    portRom: document.getElementById("portRom"),
    portRom2: document.getElementById("portRom2"),
    portParts: document.getElementById("portParts"),
    workspace: document.getElementById("workspace"),
    scriptPath: document.getElementById("scriptPath"),
    runnerMode: document.getElementById("runnerMode"),
    bashPath: document.getElementById("bashPath"),
    startBtn: document.getElementById("startBtn"),
    dryRunBtn: document.getElementById("dryRunBtn"),
    stopBtn: document.getElementById("stopBtn"),
    clearLogsBtn: document.getElementById("clearLogsBtn"),
    statusBadge: document.getElementById("statusBadge"),
    jobIdValue: document.getElementById("jobIdValue"),
    returnCodeValue: document.getElementById("returnCodeValue"),
    startedAtValue: document.getElementById("startedAtValue"),
    finishedAtValue: document.getElementById("finishedAtValue"),
    commandPreview: document.getElementById("commandPreview"),
    logOutput: document.getElementById("logOutput"),
};

function setNotice(message, level = "info") {
    els.noticeBar.textContent = message;
    els.noticeBar.className = `notice ${level}`;
}

function quoteArg(raw) {
    if (!raw) {
        return "\"\"";
    }
    if (/\s/.test(raw) || raw.includes('"')) {
        return `"${raw.replaceAll('"', '\\"')}"`;
    }
    return raw;
}

function getPayload() {
    return {
        baseRom: els.baseRom.value.trim(),
        portRom: els.portRom.value.trim(),
        portRom2: els.portRom2.value.trim(),
        portParts: els.portParts.value.trim(),
        workspace: els.workspace.value.trim(),
        scriptPath: els.scriptPath.value.trim(),
        runnerMode: (els.runnerMode.value || "bash").trim(),
        bashPath: els.bashPath.value.trim(),
    };
}

function updateCommandPreview() {
    const p = getPayload();
    const runnerMode = (p.runnerMode || "bash").toLowerCase();
    const scriptArg = p.scriptPath || "port.sh";
    const baseArg = p.baseRom || "<base-rom>";
    const portArg = p.portRom || "<port-rom>";

    const args = [scriptArg, baseArg, portArg];

    if (p.portRom2) {
        args.push(p.portRom2);
    } else if (p.portParts) {
        args.push("");
    }

    if (p.portParts) {
        args.push(p.portParts);
    }

    let cmd;
    if (runnerMode === "wsl") {
        const runnerCmd = p.bashPath || "wsl";
        const workspaceArg = p.workspace || ".";
        const shell = `cd ${quoteArg(workspaceArg)} && bash ${args.map(quoteArg).join(" ")}`;
        cmd = [runnerCmd, "bash", "-lc", shell];
    } else {
        const runnerCmd = p.bashPath || "bash";
        cmd = [runnerCmd, ...args];
    }

    els.commandPreview.value = cmd.map(quoteArg).join(" ");
}

function updateStatus(status) {
    const normalized = (status || "idle").toLowerCase();
    els.statusBadge.textContent = normalized;
    els.statusBadge.className = `status ${normalized}`;

    const running = ["queued", "running", "stopping"].includes(normalized);
    els.startBtn.disabled = running;
    els.dryRunBtn.disabled = running;
    els.stopBtn.disabled = !running;
}

function appendLogs(lines) {
    if (!Array.isArray(lines) || lines.length === 0) {
        return;
    }

    const nearBottom =
        els.logOutput.scrollHeight - els.logOutput.scrollTop - els.logOutput.clientHeight < 40;

    if (els.logOutput.textContent.trim() === "[log] Waiting for a job...") {
        els.logOutput.textContent = "";
    }

    els.logOutput.textContent += `${lines.join("\n")}\n`;

    if (nearBottom) {
        els.logOutput.scrollTop = els.logOutput.scrollHeight;
    }
}

function renderJob(job) {
    updateStatus(job.status || "idle");

    els.jobIdValue.textContent = job.id || "-";
    els.returnCodeValue.textContent = job.returnCode === null || job.returnCode === undefined ? "-" : String(job.returnCode);
    els.startedAtValue.textContent = job.startedAt || "-";
    els.finishedAtValue.textContent = job.finishedAt || "-";

    if (job.commandString) {
        els.commandPreview.value = job.commandString;
    }

    if (job.error) {
        setNotice(job.error, "danger");
    }

    if (Array.isArray(job.logs) && job.logs.length > 0) {
        appendLogs(job.logs);
    }

    if (typeof job.nextFrom === "number") {
        state.nextFrom = job.nextFrom;
    }

    const terminal = ["completed", "failed", "stopped"].includes((job.status || "").toLowerCase());
    if (terminal) {
        stopPolling();
        if ((job.status || "").toLowerCase() === "completed") {
            setNotice("Job completed successfully.", "ok");
        } else if ((job.status || "").toLowerCase() === "stopped") {
            setNotice("Job stopped by user.", "warn");
        } else {
            setNotice("Job failed. Check logs for details.", "danger");
        }
    }
}

async function submitJob(dryRun = false) {
    const payload = getPayload();
    if (!payload.baseRom || !payload.portRom) {
        setNotice("baseRom and portRom are required.", "warn");
        return;
    }

    try {
        setNotice(dryRun ? "Running dry run..." : "Starting port job...", "info");
        updateStatus("queued");

        const response = await fetch("/api/jobs", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...payload, dryRun }),
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Failed to start job.");
        }

        state.jobId = data.id;
        state.nextFrom = 0;
        els.logOutput.textContent = "";

        renderJob(data);

        if (!["completed", "failed", "stopped"].includes((data.status || "").toLowerCase())) {
            startPolling();
        }
    } catch (err) {
        updateStatus("idle");
        setNotice(String(err), "danger");
    }
}

async function pollJob() {
    if (!state.jobId) {
        return;
    }

    try {
        const response = await fetch(`/api/jobs/${encodeURIComponent(state.jobId)}?from=${state.nextFrom}`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Failed to poll job.");
        }

        renderJob(data);
    } catch (err) {
        setNotice(`Polling error: ${String(err)}`, "danger");
        stopPolling();
        updateStatus("idle");
    }
}

function startPolling() {
    stopPolling();
    state.pollTimer = window.setInterval(pollJob, 1300);
}

function stopPolling() {
    if (state.pollTimer !== null) {
        window.clearInterval(state.pollTimer);
        state.pollTimer = null;
    }
}

async function stopJob() {
    if (!state.jobId) {
        setNotice("No active job.", "warn");
        return;
    }

    try {
        const response = await fetch(`/api/jobs/${encodeURIComponent(state.jobId)}/stop`, {
            method: "POST",
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Failed to send stop signal.");
        }
        setNotice("Stop request sent.", "warn");
        await pollJob();
    } catch (err) {
        setNotice(String(err), "danger");
    }
}

els.form.addEventListener("submit", (event) => {
    event.preventDefault();
    submitJob(false);
});

els.dryRunBtn.addEventListener("click", () => submitJob(true));
els.stopBtn.addEventListener("click", stopJob);
els.clearLogsBtn.addEventListener("click", () => {
    els.logOutput.textContent = "[log] Cleared. Waiting for more output...\n";
});

for (const field of [
    els.baseRom,
    els.portRom,
    els.portRom2,
    els.portParts,
    els.workspace,
    els.scriptPath,
    els.runnerMode,
    els.bashPath,
]) {
    field.addEventListener("input", updateCommandPreview);
}

updateCommandPreview();
updateStatus("idle");
