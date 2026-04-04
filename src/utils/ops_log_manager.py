"""
Operations Log Manager

Manages persistent storage of One-Shot operation logs on disk.
Enforces a configurable capacity limit (default 1GB) and auto-purges
the oldest 25% of log files when the limit is exceeded.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)


class OpsLogManager:
    """Manages persistent operation log files with capacity limits."""

    DEFAULT_MAX_BYTES = 1_073_741_824  # 1 GB
    DEFAULT_PURGE_FRACTION = 0.25

    def __init__(
        self,
        log_dir: Optional[Path] = None,
        max_bytes: int = DEFAULT_MAX_BYTES,
        purge_fraction: float = DEFAULT_PURGE_FRACTION,
    ):
        if log_dir is None:
            from utils import get_data_dir

            log_dir = get_data_dir() / "logs" / "operations"
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._max_bytes = max_bytes
        self._purge_fraction = purge_fraction

    def save_session_log(
        self,
        entries: List[Dict[str, Any]],
        session_id: str,
        cluster_ip: str,
    ) -> Path:
        """Write operation log as a JSON Lines file.

        Returns the path to the saved log file.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_ip = cluster_ip.replace(".", "_") if cluster_ip else "unknown"
        filename = f"oneshot_{safe_ip}_{timestamp}_{session_id}.jsonl"
        filepath = self._log_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry, default=str) + "\n")

        logger.info("Saved operation log: %s (%d entries)", filename, len(entries))
        return filepath

    def check_capacity(self) -> Dict[str, Any]:
        """Return capacity stats: total_bytes, file_count, over_limit."""
        total_bytes = 0
        file_count = 0
        for f in self._log_dir.iterdir():
            if f.is_file() and f.suffix == ".jsonl":
                total_bytes += f.stat().st_size
                file_count += 1
        return {
            "total_bytes": total_bytes,
            "file_count": file_count,
            "max_bytes": self._max_bytes,
            "over_limit": total_bytes > self._max_bytes,
            "usage_percent": round((total_bytes / self._max_bytes) * 100, 1) if self._max_bytes > 0 else 0,
        }

    def purge_oldest(self) -> Dict[str, Any]:
        """Delete the oldest fraction of log files. Returns purge stats."""
        files = sorted(
            [f for f in self._log_dir.iterdir() if f.is_file() and f.suffix == ".jsonl"],
            key=lambda f: f.stat().st_mtime,
        )
        if not files:
            return {"purged": 0, "freed_bytes": 0}

        purge_count = max(1, int(len(files) * self._purge_fraction))
        to_purge = files[:purge_count]
        freed_bytes = 0

        for f in to_purge:
            try:
                freed_bytes += f.stat().st_size
                f.unlink()
                logger.info("Purged old operation log: %s", f.name)
            except Exception as exc:
                logger.warning("Failed to purge %s: %s", f.name, exc)

        return {"purged": len(to_purge), "freed_bytes": freed_bytes}

    def list_logs(self) -> List[Dict[str, Any]]:
        """List all saved operation logs with metadata."""
        logs = []
        for f in sorted(
            self._log_dir.glob("*.jsonl"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        ):
            st = f.stat()
            logs.append(
                {
                    "filename": f.name,
                    "path": str(f),
                    "size": st.st_size,
                    "modified": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"),
                    "entry_count": sum(1 for _ in open(f, encoding="utf-8")),
                }
            )
        return logs

    def ensure_capacity(self, emit_fn=None) -> bool:
        """Check capacity and purge if over limit. Returns True if purge occurred."""
        cap = self.check_capacity()
        if cap["over_limit"]:
            if emit_fn:
                emit_fn(
                    "warn",
                    f"Operation log storage at {cap['usage_percent']}% capacity "
                    f"({cap['total_bytes'] / 1024 / 1024:.0f} MB / {self._max_bytes / 1024 / 1024:.0f} MB). "
                    f"Purging oldest {int(self._purge_fraction * 100)}% of logs...",
                )
            result = self.purge_oldest()
            if emit_fn:
                emit_fn(
                    "info",
                    f"Purged {result['purged']} log files, freed {result['freed_bytes'] / 1024 / 1024:.1f} MB",
                )
            return True
        return False
