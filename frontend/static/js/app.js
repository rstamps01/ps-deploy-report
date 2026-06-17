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

    // -- Browser liveness heartbeat (auto-shutdown) -----------------------
    // Posts a lightweight ping so the local server can exit shortly after
    // the operator closes the browser.  A final beacon on unload speeds up
    // detection; the server still has a grace window and never exits mid-job.
    (function initHeartbeat() {
        let intervalMs = 5000;
        let timer = null;

        function ping() {
            fetch("/api/heartbeat", { method: "POST", keepalive: true })
                .then(function (r) { return r.ok ? r.json() : null; })
                .then(function (data) {
                    if (!data) return;
                    if (data.auto_shutdown === false) {
                        // Feature disabled server-side: stop pinging.
                        if (timer) { clearInterval(timer); timer = null; }
                        return;
                    }
                    if (data.interval) {
                        const next = Math.max(1, Number(data.interval)) * 1000;
                        if (next !== intervalMs && timer) {
                            intervalMs = next;
                            clearInterval(timer);
                            timer = setInterval(ping, intervalMs);
                        }
                    }
                })
                .catch(function () { /* server gone or offline: ignore */ });
        }

        ping();
        timer = setInterval(ping, intervalMs);
        // No unload beacon on purpose: a ping at teardown would refresh the
        // heartbeat and is not multi-tab safe.  When the last tab closes the
        // pings simply stop and the watchdog exits after the grace window.
    })();

    // -- App-update status pill + Download control (QP-3 item 2) ----------
    // Three-state pill next to the version number:
    //   UPDATE AVAILABLE (orange) > PRE-RELEASE (indigo) > LATEST VERSION (green).
    // When an update is available a Download control appears that auto-starts
    // the OS-matched installer, with a dropdown for version / notes / per-OS.
    (function initAppUpdate() {
        const pill = document.getElementById("appStatusPill");
        const update = document.getElementById("appUpdate");
        if (!pill || !update) return;
        const btn = document.getElementById("appUpdateBtn");
        const caret = document.getElementById("appUpdateCaret");
        const drop = document.getElementById("appUpdateDropdown");
        const verEl = document.getElementById("appUpdateVersion");
        const notesEl = document.getElementById("appUpdateNotes");
        const macEl = document.getElementById("appUpdateMac");
        const winEl = document.getElementById("appUpdateWin");

        function isWindows() {
            const p = (navigator.userAgentData && navigator.userAgentData.platform) ||
                navigator.platform || navigator.userAgent || "";
            return /win/i.test(p);
        }

        function setPill(cls, text) {
            pill.className = "app-status-pill " + cls;
            pill.textContent = text;
        }

        if (caret && drop) {
            caret.addEventListener("click", function (e) {
                e.stopPropagation();
                drop.classList.toggle("open");
            });
            document.addEventListener("click", function (e) {
                if (!drop.contains(e.target) && e.target !== caret && !caret.contains(e.target)) {
                    drop.classList.remove("open");
                }
            });
        }

        fetch("/api/update/status")
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (data) {
                if (!data) return;
                if (data.update_available && data.latest_version) {
                    setPill("update", "UPDATE AVAILABLE");
                    if (verEl) verEl.textContent = "Version " + data.latest_version +
                        " (you have " + data.current_version + ")";
                    if (notesEl) notesEl.href = data.release_notes_url || data.latest_url || "#";
                    const mac = data.download_url_mac;
                    const win = data.download_url_win;
                    if (macEl) { macEl.hidden = !mac; if (mac) macEl.href = mac; }
                    if (winEl) { winEl.hidden = !win; if (win) winEl.href = win; }
                    // Primary button auto-picks the OS-matched installer; falls
                    // back to the release page if no matching asset is published.
                    const preferred = isWindows() ? (win || mac) : (mac || win);
                    if (btn) btn.href = preferred || data.release_notes_url || data.latest_url || "#";
                    update.hidden = false;
                } else if (data.is_prerelease) {
                    setPill("prerelease", "PRE-RELEASE");
                } else if (data.enabled !== false && data.error == null) {
                    // Successfully checked, stable build, nothing newer.
                    setPill("latest", "LATEST VERSION");
                }
                // else (disabled/offline on a stable build): leave the initial
                // hidden pill as-is rather than falsely claiming LATEST VERSION.
            })
            .catch(function () { /* offline or check failed: keep initial pill */ });
    })();

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

    // -- Deployment tools nav indicator (available on every page) ---------

    (function initNavTools() {
        const wrap = document.getElementById("navTools");
        const btn = document.getElementById("navToolsBtn");
        const drop = document.getElementById("navToolsDropdown");
        const dot = document.getElementById("navToolsDot");
        const list = document.getElementById("navToolsList");
        const summary = document.getElementById("navToolsSummary");
        const updateBtn = document.getElementById("btnUpdateTools");
        if (!wrap || !btn || !drop) return;

        function stateFor(tool) {
            if (!tool.cached) return { cls: "missing", label: "Missing" };
            if (tool.stale) return { cls: "warn", label: (tool.age_days || 0) + "d old" };
            return { cls: "ok", label: "Ready" };
        }

        function render(status) {
            const tools = (status && status.tools) || [];
            const attention = !!(status && status.needs_attention);
            if (dot) dot.hidden = !attention;
            wrap.classList.toggle("attention", attention);
            if (summary) {
                summary.textContent = status
                    ? status.cached + "/" + status.total + " cached"
                    : "";
            }
            if (!list) return;
            if (!tools.length) {
                list.innerHTML = '<div class="nav-tools-empty">No tools defined.</div>';
                return;
            }
            list.innerHTML = "";
            tools.forEach(function (t) {
                const st = stateFor(t);
                const row = document.createElement("div");
                row.className = "nav-tools-row";
                const name = document.createElement("span");
                name.className = "tn";
                name.textContent = t.name;
                const tag = document.createElement("span");
                tag.className = "nav-tools-state " + st.cls;
                tag.textContent = st.label;
                row.appendChild(name);
                row.appendChild(tag);
                list.appendChild(row);
            });
        }

        function refresh() {
            fetch("/api/tools/status?_t=" + Date.now())
                .then(function (r) { return r.json(); })
                .then(render)
                .catch(function () { /* leave last-known state */ });
        }

        btn.addEventListener("click", function (e) {
            e.stopPropagation();
            drop.classList.toggle("open");
            if (drop.classList.contains("open")) refresh();
        });
        document.addEventListener("click", function (e) {
            if (!drop.contains(e.target) && !btn.contains(e.target)) {
                drop.classList.remove("open");
            }
        });

        if (updateBtn) {
            updateBtn.addEventListener("click", function () {
                updateBtn.disabled = true;
                const original = updateBtn.textContent;
                updateBtn.textContent = "Updating…";
                fetch("/api/tools/update", { method: "POST" })
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        if (data && data.status) render(data.status);
                        else refresh();
                    })
                    .catch(function () {})
                    .finally(function () {
                        updateBtn.disabled = false;
                        updateBtn.textContent = original;
                    });
            });
        }

        refresh();
        setInterval(refresh, 60000);
    })();

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
