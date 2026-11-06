"""
LanguageServer gRPC-Web / HTTP Connect protocol client.
"""

from __future__ import annotations

import concurrent.futures
from typing import Any, Optional

import requests
import urllib3

from antigravity_export.config import AntigravityConfig

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class LanguageServerClient:
    """Client for executing calls against the Antigravity Language Server."""

    def __init__(
        self,
        port: Optional[int] = None,
        csrf_token: Optional[str] = None,
        config: Optional[AntigravityConfig] = None,
    ):
        self.port = port
        self.csrf_token = csrf_token
        self.config = config or AntigravityConfig()

    def call_api(
        self,
        method: str,
        params: Optional[dict[str, Any]] = None,
        port: Optional[int] = None,
        csrf_token: Optional[str] = None,
        timeout: float = 20.0,
    ) -> Optional[dict[str, Any]]:
        """Call a LanguageServer gRPC-Web Connect API method."""
        p = port or self.port
        token = csrf_token or self.csrf_token

        if not p or not token:
            return None

        url = f"https://localhost:{p}/{self.config.BASE_SERVICE_PATH}/{method}"
        headers = {
            "Content-Type": "application/json",
            "Connect-Protocol-Version": self.config.CONNECT_PROTOCOL_VERSION,
            self.config.CSRF_HEADER_NAME: token,
        }

        try:
            resp = requests.post(
                url,
                headers=headers,
                json=params or {},
                verify=False,
                timeout=timeout,
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return None

    def get_all_trajectories(
        self,
        port: Optional[int] = None,
        csrf_token: Optional[str] = None,
    ) -> dict[str, Any]:
        """Fetch all conversation summaries indexed by a single LS instance."""
        res = self.call_api("GetAllCascadeTrajectories", {}, port=port, csrf_token=csrf_token, timeout=5.0)
        if not res:
            return {}
        return res.get("trajectorySummaries", {})

    def get_all_trajectories_merged(
        self,
        endpoints: list[dict[str, Any]],
    ) -> tuple[dict[str, Any], dict[str, dict[str, Any]], list[tuple[int, str]]]:
        """Query multiple LS endpoints concurrently and merge trajectories.

        Returns:
            (merged_summaries, cascade_to_endpoint, failed_endpoints)
        """
        merged: dict[str, Any] = {}
        cascade_ep: dict[str, dict[str, Any]] = {}
        failed_eps: list[tuple[int, str]] = []

        if not endpoints:
            return merged, cascade_ep, failed_eps

        def fetch(ep: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
            return ep, self.get_all_trajectories(port=ep["port"], csrf_token=ep["csrf_token"])

        max_workers = min(10, max(1, len(endpoints)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ep = {executor.submit(fetch, ep): ep for ep in endpoints}
            for future in concurrent.futures.as_completed(future_to_ep):
                ep = future_to_ep[future]
                try:
                    _, summaries = future.result()
                    if not summaries:
                        failed_eps.append((ep["port"], "Empty trajectory response or timeout"))
                    else:
                        for cid, info in summaries.items():
                            if cid not in merged:
                                merged[cid] = info
                                cascade_ep[cid] = ep
                except Exception as e:
                    failed_eps.append((ep["port"], str(e)))

        return merged, cascade_ep, failed_eps

    def get_trajectory_steps(
        self,
        cascade_id: str,
        step_count: int = 1000,
        port: Optional[int] = None,
        csrf_token: Optional[str] = None,
        timeout: float = 30.0,
    ) -> list[dict[str, Any]]:
        """Fetch all trajectory steps for a conversation ID (supports on-demand activation)."""
        res = self.call_api(
            "GetCascadeTrajectorySteps",
            {"cascadeId": cascade_id, "startIndex": 0, "endIndex": step_count + 20},
            port=port,
            csrf_token=csrf_token,
            timeout=timeout,
        )
        if not res:
            return []
        return res.get("steps", res.get("messages", []))
