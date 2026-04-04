/**
 * VAST As-Built Reporter - Web UI JavaScript
 *
 * Handles: form submission, SSE log streaming, and job status polling.
 */

(function () {
    "use strict";

    // -- Exit button (available on every page) ----------------------------

    const btnExit = document.getElementById("btnExit");
    if (btnExit) {
        btnExit.addEventListener("click", function () {
            if (!confirm("Exit the application?")) return;
            btnExit.disabled = true;
            btnExit.textContent = "Exiting…";
            fetch("/shutdown", { method: "POST" }).catch(function () {});
            setTimeout(function () {
                document.body.innerHTML =
                    '<div style="display:flex;align-items:center;justify-content:center;' +
                    'height:100vh;background:#0f1724;color:#94a3b8;font-family:sans-serif;' +
                    'font-size:1.1rem;">Application stopped. You may close this window.</div>';
            }, 500);
        });
    }

    // -- Hamburger menu toggle (available on every page) -------------------

    const hamBtn = document.getElementById("navHamburgerBtn");
    const hamDrop = document.getElementById("navHamburgerDropdown");
    if (hamBtn && hamDrop) {
        hamBtn.addEventListener("click", function (e) {
            e.stopPropagation();
            hamDrop.classList.toggle("open");
        });
        document.addEventListener("click", function (e) {
            if (!hamDrop.contains(e.target) && e.target !== hamBtn) {
                hamDrop.classList.remove("open");
            }
        });
    }

    // -- Generate form submission + SSE -----------------------------------

    const form = document.getElementById("generateForm");
    if (!form) return;

    const logOutput = document.getElementById("logOutput");
    const statusBanner = document.getElementById("statusBanner");
    const resultPanel = document.getElementById("resultPanel");
    const resultMessage = document.getElementById("resultMessage");
    const resultLinks = document.getElementById("resultLinks");
    const btnGenerate = document.getElementById("btnGenerate");

    const btnCancel = document.getElementById("btnCancel");
    let evtSource = null;
    let pollTimer = null;

    form.addEventListener("submit", async function (e) {
        e.preventDefault();

        const placementMode = document.getElementById("switch_placement");
        if (placementMode && placementMode.value === "manual") {
            const mp = document.getElementById("manual_placements");
            const placements = mp ? JSON.parse(mp.value || "[]") : [];
            if (placements.length === 0) {
                alert("Manual mode: please discover and place at least one switch before generating.");
                return;
            }
        }

        // Clear previous state
        if (logOutput) logOutput.innerHTML = "";
        if (resultPanel) resultPanel.classList.add("hidden");
        statusBanner.classList.remove("hidden");
        statusBanner.className = "status-banner running";
        statusBanner.textContent = "Generating report...";
        btnGenerate.disabled = true;
        btnGenerate.textContent = "Generating...";
        if (btnCancel) btnCancel.classList.remove("hidden");

        // Submit the form data
        const body = new URLSearchParams(new FormData(form));
        try {
            const resp = await fetch("/generate", {
                method: "POST",
                body: body,
            });
            const data = await resp.json();
            if (!resp.ok) {
                showError(data.error || "Failed to start generation");
                resetButton();
                return;
            }
        } catch (err) {
            showError("Network error: " + err.message);
            resetButton();
            return;
        }

        // Start SSE log stream
        startLogStream();

        // Poll for completion
        pollTimer = setInterval(checkStatus, 2000);
    });

    function startLogStream() {
        if (evtSource) evtSource.close();
        evtSource = new EventSource("/stream/logs");
        evtSource.onmessage = function (e) {
            if (e.data.startsWith(":")) return; // keepalive
            try {
                const entry = JSON.parse(e.data);
                appendLog(entry);
            } catch (_) {
                /* skip malformed */
            }
        };
        evtSource.onerror = function () {
            /* will reconnect automatically */
        };
    }

    function appendLog(entry) {
        if (!logOutput) return;
        const line = document.createElement("p");
        line.className = "log-line " + (entry.level || "");
        const ts = entry.timestamp ? entry.timestamp + " " : "";
        const lvl = entry.level ? "[" + entry.level + "] " : "";
        line.textContent = ts + lvl + (entry.message || "");
        logOutput.appendChild(line);
        logOutput.scrollTop = logOutput.scrollHeight;
    }

    async function checkStatus() {
        try {
            const resp = await fetch("/generate/status?_t=" + Date.now());
            const data = await resp.json();
            if (!data.running && data.result) {
                clearInterval(pollTimer);
                if (evtSource) evtSource.close();

                try {
                    if (data.result.success) {
                        showSuccess(data.result);
                    } else {
                        showError(data.result.error || "Unknown error");
                    }
                } catch (renderErr) {
                    console.error("Render error:", renderErr);
                    showError("Display error — check console");
                }
                resetButton();
            }
        } catch (_) {
            /* retry next tick */
        }
    }

    function showSuccess(result) {
        statusBanner.className = "status-banner success";
        statusBanner.textContent = "Report generated successfully for " + (result.cluster || "cluster");

        resultPanel.classList.remove("hidden");

        const pdfIcon = '<span class="file-icon file-icon-pdf"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6"/><text x="7" y="17" font-size="6" font-weight="700" fill="currentColor" stroke="none">PDF</text></svg></span>';
        const jsonIcon = '<span class="file-icon file-icon-json"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6"/><text x="5" y="17" font-size="5.5" font-weight="700" fill="currentColor" stroke="none">JSON</text></svg></span>';

        resultMessage.innerHTML =
            '<span class="result-file">' + pdfIcon + ' ' + result.pdf + '</span>' +
            '<span class="result-file">' + jsonIcon + ' ' + result.json + '</span>';

        resultLinks.innerHTML = "";

        const viewPdf = document.createElement("a");
        viewPdf.href = "/reports/view/" + encodeURIComponent(result.pdf);
        viewPdf.target = "_blank";
        viewPdf.className = "btn btn-accent btn-sm";
        viewPdf.textContent = "View PDF";
        resultLinks.appendChild(viewPdf);

        const dlPdf = document.createElement("a");
        dlPdf.href = "/reports/download/" + encodeURIComponent(result.pdf);
        dlPdf.className = "btn btn-accent btn-sm";
        dlPdf.textContent = "Download PDF";
        resultLinks.appendChild(dlPdf);

        const dlJson = document.createElement("a");
        dlJson.href = "/reports/download/" + encodeURIComponent(result.json);
        dlJson.className = "btn btn-accent btn-sm";
        dlJson.textContent = "Download JSON";
        resultLinks.appendChild(dlJson);
    }

    if (btnCancel) {
        btnCancel.addEventListener("click", async function () {
            btnCancel.disabled = true;
            btnCancel.textContent = "Cancelling...";
            try {
                await fetch("/generate/cancel", { method: "POST" });
            } catch (_) { /* best effort */ }
            clearInterval(pollTimer);
            if (evtSource) evtSource.close();
            statusBanner.className = "status-banner error";
            statusBanner.textContent = "Report generation cancelled";
            resetButton();
        });
    }

    function showError(msg) {
        statusBanner.className = "status-banner error";
        statusBanner.textContent = "Error: " + msg;
    }

    function resetButton() {
        btnGenerate.disabled = false;
        btnGenerate.textContent = "Generate";
        if (btnCancel) {
            btnCancel.classList.add("hidden");
            btnCancel.disabled = false;
            btnCancel.textContent = "Cancel";
        }
    }
})();
