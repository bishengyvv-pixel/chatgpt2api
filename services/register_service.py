from __future__ import annotations

import functools
import json
import threading
import time
import uuid
from collections import defaultdict
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from pathlib import Path

from services.account_service import account_service
from services.config import DATA_DIR
from services.register import openai_register


REGISTER_FILE = DATA_DIR / "register.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_config() -> dict:
    return {**openai_register.config, "mode": "total", "target_quota": 100, "target_available": 10, "check_interval": 5, "enabled": False, "stats": {"success": 0, "fail": 0, "done": 0, "running": 0, "threads": openai_register.config["threads"], "elapsed_seconds": 0, "avg_seconds": 0, "success_rate": 0, "current_quota": 0, "current_available": 0}}


def _normalize(raw: dict) -> dict:
    cfg = _default_config()
    cfg.update({k: v for k, v in raw.items() if k not in {"stats", "logs"}})
    cfg["total"] = max(1, int(cfg.get("total") or 1))
    cfg["threads"] = max(1, int(cfg.get("threads") or 1))
    cfg["mode"] = str(cfg.get("mode") or "total").strip() if str(cfg.get("mode") or "total").strip() in {"total", "quota", "available"} else "total"
    cfg["target_quota"] = max(1, int(cfg.get("target_quota") or 1))
    cfg["target_available"] = max(1, int(cfg.get("target_available") or 1))
    cfg["check_interval"] = max(1, int(cfg.get("check_interval") or 5))
    cfg["proxy"] = str(cfg.get("proxy") or "").strip()
    cfg["enabled"] = bool(cfg.get("enabled"))
    stats = {**_default_config()["stats"], **(raw.get("stats") if isinstance(raw.get("stats"), dict) else {}),
             "threads": cfg["threads"]}
    cfg["stats"] = stats
    return cfg


class RegisterService:
    def __init__(self, store_file: Path):
        self._store_file = store_file
        self._lock = threading.RLock()
        self._runner: threading.Thread | None = None
        self._logs: list[dict] = []
        openai_register.register_log_sink = self._append_log
        self._config = self._load()
        if self._config["enabled"]:
            self.start()

    def _load(self) -> dict:
        try:
            return _normalize(json.loads(self._store_file.read_text(encoding="utf-8")))
        except Exception:
            return _normalize({})

    def _save(self) -> None:
        self._store_file.parent.mkdir(parents=True, exist_ok=True)
        self._store_file.write_text(json.dumps(self._config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def get(self) -> dict:
        with self._lock:
            return json.loads(json.dumps({**self._config, "logs": self._logs[-300:]}, ensure_ascii=False))

    def _inject_proxy_to_mail(self) -> None:
        proxy = str(self._config.get("proxy") or "").strip()
        if proxy and isinstance(self._config.get("mail"), dict):
            self._config["mail"]["proxy"] = proxy

    def update(self, updates: dict) -> dict:
        with self._lock:
            self._config = _normalize({**self._config, **updates})
            self._inject_proxy_to_mail()
            openai_register.config.update({k: self._config[k] for k in ("mail", "proxy", "total", "threads")})
            self._save()
            return self.get()

    def start(self) -> dict:
        with self._lock:
            if self._runner and self._runner.is_alive():
                self._config["enabled"] = True
                self._save()
                return self.get()
            self._config["enabled"] = True
            self._inject_proxy_to_mail()
            self._logs = []
            metrics = self._pool_metrics()
            self._config["stats"] = {"job_id": uuid.uuid4().hex, "success": 0, "fail": 0, "done": 0, "running": 0, "threads": self._config["threads"], **metrics, "started_at": _now(), "updated_at": _now()}
            openai_register.config.update({k: self._config[k] for k in ("mail", "proxy", "total", "threads")})
            with openai_register.stats_lock:
                openai_register.stats.update({"done": 0, "success": 0, "fail": 0, "start_time": time.time()})
            self._save()
            # 激活统计看板的猴子补丁（不修改 openai_register.py）
            _reset_task_stats()
            _patch_registrar()
            _patch_worker()
            self._runner = threading.Thread(target=self._run, daemon=True, name="openai-register")
            self._runner.start()
            self._append_log(f"注册任务启动，模式={self._config['mode']}，线程数={self._config['threads']}", "yellow")
            return self.get()

    def stop(self) -> dict:
        with self._lock:
            self._config["enabled"] = False
            self._config["stats"]["updated_at"] = _now()
            self._save()
            self._append_log("已请求停止注册任务，正在等待当前运行任务结束", "yellow")
            return self.get()

    def reset(self) -> dict:
        with self._lock:
            self._logs = []
            self._config["stats"] = {"success": 0, "fail": 0, "done": 0, "running": 0, "threads": self._config["threads"], "elapsed_seconds": 0, "avg_seconds": 0, "success_rate": 0, **self._pool_metrics(), "updated_at": _now()}
            with openai_register.stats_lock:
                openai_register.stats.update({"done": 0, "success": 0, "fail": 0, "start_time": 0.0})
            self._save()
            return self.get()

    def _append_log(self, text: str, color: str = "") -> None:
        with self._lock:
            self._logs.append({"time": _now(), "text": str(text), "level": str(color or "info")})
            self._logs = self._logs[-300:]

    def _pool_metrics(self) -> dict:
        items = account_service.list_accounts()
        normal = [item for item in items if item.get("status") == "正常"]
        return {
            "current_quota": sum(int(item.get("quota") or 0) for item in normal if not item.get("image_quota_unknown")),
            "current_available": len(normal),
        }

    def _target_reached(self, cfg: dict, submitted: int) -> bool:
        mode = str(cfg.get("mode") or "total")
        metrics = self._pool_metrics()
        self._bump(**metrics)
        if mode == "quota":
            reached = metrics["current_quota"] >= int(cfg.get("target_quota") or 1)
            self._append_log(f"检查号池：当前正常账号={metrics['current_available']}，当前剩余额度={metrics['current_quota']}，目标额度={cfg.get('target_quota')}，{'跳过注册' if reached else '继续注册'}", "yellow")
            return reached
        if mode == "available":
            reached = metrics["current_available"] >= int(cfg.get("target_available") or 1)
            self._append_log(f"检查号池：当前正常账号={metrics['current_available']}，目标账号={cfg.get('target_available')}，当前剩余额度={metrics['current_quota']}，{'跳过注册' if reached else '继续注册'}", "yellow")
            return reached
        return submitted >= int(cfg.get("total") or 1)

    def _bump(self, **updates) -> None:
        with self._lock:
            self._config["stats"].update(updates)
            stats = self._config["stats"]
            started_at = str(stats.get("started_at") or "")
            if started_at:
                try:
                    elapsed = max(0.0, (datetime.now(timezone.utc) - datetime.fromisoformat(started_at)).total_seconds())
                except Exception:
                    elapsed = 0.0
                done = int(stats.get("done") or 0)
                success = int(stats.get("success") or 0)
                fail = int(stats.get("fail") or 0)
                stats["elapsed_seconds"] = round(elapsed, 1)
                stats["avg_seconds"] = round(elapsed / success, 1) if success else 0
                stats["success_rate"] = round(success * 100 / max(1, success + fail), 1)
            self._config["stats"]["updated_at"] = _now()
            self._save()

    def _run(self) -> None:
        threads = int(self.get()["threads"])
        submitted, done, success, fail = 0, 0, 0, 0
        executor = ThreadPoolExecutor(max_workers=threads)
        try:
            futures = set()
            while True:
                cfg = self.get()
                while self.get()["enabled"] and not self._target_reached(cfg, submitted) and len(futures) < threads:
                    submitted += 1
                    futures.add(executor.submit(openai_register.worker, submitted))
                self._bump(running=len(futures), done=done, success=success, fail=fail)
                enabled = self.get()["enabled"]
                if not enabled:
                    break
                if not futures and str(cfg.get("mode") or "total") == "total":
                    break
                if not futures and enabled:
                    time.sleep(max(1, int(cfg.get("check_interval") or 5)))
                    continue
                finished, futures = wait(futures, timeout=5, return_when=FIRST_COMPLETED)
                for future in finished:
                    done += 1
                    try:
                        result = future.result()
                        success += 1 if result.get("ok") else 0
                        fail += 0 if result.get("ok") else 1
                    except Exception:
                        fail += 1
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
        self._bump(running=0, done=done, success=success, fail=fail, finished_at=_now())
        with self._lock:
            self._config["enabled"] = False
            self._save()
        self._append_log(f"注册任务结束，成功{success}，失败{fail}", "yellow")


# ── 统计看板（非侵入式，猴子补丁旁挂）────────────────────

_task_stats_lock = threading.Lock()
_step_records: list[dict] = []
_task_records: list[dict] = []
_proxy_stats: dict = defaultdict(lambda: {"success": 0, "fail": 0, "total": 0})
_domain_stats: dict = defaultdict(lambda: {"success": 0, "fail": 0, "total": 0})


def _record_step(step_name: str, ok: bool, duration: float, error: str = "") -> None:
    with _task_stats_lock:
        _step_records.append({"step": step_name, "ok": ok, "duration": round(duration, 2), "error": str(error)[:200]})


def _record_task(
    index: int, proxy: str, domain: str, email: str,
    ok: bool, duration: float, error: str = "", failed_step: str = "",
) -> None:
    with _task_stats_lock:
        task = {
            "index": index, "status": "success" if ok else "fail",
            "proxy": proxy, "domain": domain, "email": email,
            "duration": round(duration, 2), "error": str(error)[:200],
            "failed_step": failed_step, "time": _now(),
        }
        _task_records.append(task)
        if len(_task_records) > 50:
            _task_records.pop(0)
        if proxy:
            ps = _proxy_stats[proxy]
            ps["total"] += 1
            ps["success" if ok else "fail"] += 1
        if domain:
            ds = _domain_stats[domain]
            ds["total"] += 1
            ds["success" if ok else "fail"] += 1


def get_task_stats() -> dict:
    """返回聚合统计快照。"""
    with _task_stats_lock:
        step_agg: dict = defaultdict(lambda: {"success": 0, "fail": 0, "total": 0, "durations": []})
        for r in _step_records:
            s = step_agg[r["step"]]
            s["success" if r["ok"] else "fail"] += 1
            s["total"] += 1
            s["durations"].append(r["duration"])
        step_stats: dict = {}
        for name, agg in step_agg.items():
            step_stats[name] = {
                "success": agg["success"], "fail": agg["fail"], "total": agg["total"],
                "avg_duration": round(sum(agg["durations"]) / len(agg["durations"]), 2) if agg["durations"] else 0,
            }
        ps: dict = {}
        try:
            from services.register.openai_register import proxy_pool
            _cooldowns = dict(proxy_pool._cooldown) if hasattr(proxy_pool, "_cooldown") else {}
        except Exception:
            _cooldowns = {}
        for p, d in _proxy_stats.items():
            ps[p] = dict(d)
            ps[p]["cooldown"] = p in _cooldowns
        ds: dict = {}
        for d, v in _domain_stats.items():
            ds[d] = dict(v)
            ds[d]["blocked"] = v["fail"] >= 5 and v["success"] == 0
        return {
            "step_stats": step_stats,
            "proxy_stats": ps,
            "domain_stats": ds,
            "recent_tasks": list(_task_records),
            "totals": {
                "success": sum(1 for r in _task_records if r["status"] == "success"),
                "fail": sum(1 for r in _task_records if r["status"] == "fail"),
                "total": len(_task_records),
            },
            "job_running": register_service._config.get("enabled", False),
        }


def _reset_task_stats() -> None:
    with _task_stats_lock:
        _step_records.clear()
        _task_records.clear()
        _proxy_stats.clear()
        _domain_stats.clear()


def _step_decorator(step_name: str):
    """步骤级装饰器工厂"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            start = time.time()
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                _record_step(step_name, False, time.time() - start, str(e))
                raise
            _record_step(step_name, True, time.time() - start)
        return wrapper
    return decorator


def _patch_registrar() -> None:
    """运行时给 PlatformRegistrar 方法挂步骤统计装饰器（不修改源文件）。"""
    from services.register.openai_register import PlatformRegistrar
    for method_name in [
        "_platform_authorize", "_register_user", "_send_otp",
        "_create_account", "_exchange_registered_tokens",
    ]:
        if not hasattr(PlatformRegistrar, method_name):
            continue
        # 防止重复 patch
        original = getattr(PlatformRegistrar, method_name)
        if getattr(original, "_stats_patched", False):
            continue
        setattr(PlatformRegistrar, method_name, _step_decorator(method_name)(original))
        getattr(PlatformRegistrar, method_name)._stats_patched = True


def _patch_worker() -> None:
    """运行时给 worker() 挂任务级统计包装（不修改源文件）。"""
    import services.register.openai_register as reg
    original_worker = reg.worker
    if getattr(original_worker, "_stats_patched", False):
        return

    @functools.wraps(original_worker)
    def _tracked_worker(index: int) -> dict:
        task_start = time.time()
        result = original_worker(index)
        ok = bool(result.get("ok"))
        email = ""
        domain = ""
        proxy = ""
        error = str(result.get("error") or "")
        failed_step = ""

        if ok and isinstance(result.get("result"), dict):
            email = str(result["result"].get("email") or "")
            domain = email.split("@")[-1] if "@" in email else ""
        elif not ok:
            if "Cloudflare" in error:
                failed_step = "_platform_authorize"
            elif "user_register" in error or "409" in error or "403" in error:
                failed_step = "_register_user"
            elif "send_otp" in error:
                failed_step = "_send_otp"
            elif "create_account" in error:
                failed_step = "_create_account"
            elif "token" in error.lower():
                failed_step = "_exchange_registered_tokens"

        _record_task(index, proxy, domain, email, ok, time.time() - task_start, error, failed_step)
        return result

    _tracked_worker._stats_patched = True
    reg.worker = _tracked_worker


# ── 统计看板结束 ──────────────────────────────────────────


register_service = RegisterService(REGISTER_FILE)