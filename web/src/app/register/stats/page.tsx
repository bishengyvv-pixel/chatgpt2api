"use client";

import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, BarChart3, RefreshCw } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { getStoredAuthKey } from "@/store/auth";

/* ------------------------------------------------------------------ */
/*  类型                                                               */
/* ------------------------------------------------------------------ */

interface StepStat {
  success: number;
  fail: number;
  total: number;
  avg_duration: number;
}

interface TaskRecord {
  index: number;
  status: "success" | "fail";
  proxy: string;
  domain: string;
  email: string;
  duration: number;
  error: string;
  failed_step: string;
  time: string;
}

interface StatsData {
  step_stats: Record<string, StepStat>;
  proxy_stats: Record<string, { success: number; fail: number; total: number; cooldown?: boolean }>;
  domain_stats: Record<string, { success: number; fail: number; total: number; blocked?: boolean }>;
  recent_tasks: TaskRecord[];
  totals: { success: number; fail: number; total: number };
  job_running: boolean;
}

/* ------------------------------------------------------------------ */
/*  步骤名 → 中文映射                                                    */
/* ------------------------------------------------------------------ */

const STEP_LABELS: Record<string, string> = {
  _platform_authorize: "OAuth 授权",
  _register_user: "提交注册",
  _send_otp: "发送验证码",
  _create_account: "创建资料",
  _exchange_registered_tokens: "换取 Token",
};

const STEP_ORDER = [
  "_platform_authorize",
  "_register_user",
  "_send_otp",
  "_create_account",
  "_exchange_registered_tokens",
];

/* ------------------------------------------------------------------ */
/*  进度条组件                                                          */
/* ------------------------------------------------------------------ */

function StepBar({ stat }: { stat: StepStat }) {
  const total = stat.total || 1;
  const pctSuccess = (stat.success / total) * 100;
  const pctFail = (stat.fail / total) * 100;
  const pct = Math.round((stat.success / total) * 100);

  return (
    <div className="flex items-center gap-3">
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-stone-100">
        <div className="flex h-full">
          <div
            className="h-full bg-emerald-500 transition-all"
            style={{ width: `${pctSuccess}%` }}
          />
          <div
            className="h-full bg-rose-400 transition-all"
            style={{ width: `${pctFail}%` }}
          />
        </div>
      </div>
      <span className="w-10 text-right text-xs tabular-nums text-stone-500">
        {pct}%
      </span>
      <span className="w-16 text-right text-xs tabular-nums text-stone-400">
        {stat.avg_duration.toFixed(1)}s
      </span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  主页面                                                              */
/* ------------------------------------------------------------------ */

export default function RegisterStatsPage() {
  const [stats, setStats] = useState<StatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchStats = useCallback(async () => {
    try {
      const token = await getStoredAuthKey();
      const resp = await fetch("/api/register/stats", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const json = await resp.json();
      setStats(json.stats as StatsData);
      setError("");
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchStats();
    const timer = setInterval(() => void fetchStats(), 3000);
    return () => clearInterval(timer);
  }, [fetchStats]);

  /* ---- 加载态 ---- */
  if (loading && !stats) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <RefreshCw className="size-5 animate-spin text-stone-400" />
      </div>
    );
  }

  /* ---- 错误态 ---- */
  if (error && !stats) {
    return (
      <div className="flex min-h-[50vh] flex-col items-center justify-center gap-3">
        <p className="text-sm text-stone-500">加载失败: {error}</p>
        <Button variant="outline" size="sm" onClick={fetchStats}>
          重试
        </Button>
      </div>
    );
  }

  if (!stats) return null;

  /* ------------------------------------------------------------------ */
  /*  渲染                                                               */
  /* ------------------------------------------------------------------ */

  return (
    <div className="space-y-6 p-4">
      {/* 顶部导航 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/register">
            <Button variant="outline" size="sm" className="gap-1.5 rounded-xl border-stone-200 bg-white">
              <ArrowLeft className="size-4" />
              返回注册机
            </Button>
          </Link>
          <h1 className="text-xl font-semibold tracking-tight">注册统计看板</h1>
          {stats.job_running && (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-xs text-emerald-700">
              <span className="size-1.5 rounded-full bg-emerald-500" />
              运行中
            </span>
          )}
        </div>
        <Button variant="outline" size="sm" onClick={fetchStats} className="gap-1.5 rounded-xl border-stone-200 bg-white">
          <RefreshCw className="size-4" />
          刷新
        </Button>
      </div>

      {/* 全局统计卡片 */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "总成功", value: stats.totals.success, color: "text-emerald-600" },
          { label: "总失败", value: stats.totals.fail, color: "text-rose-500" },
          { label: "总计", value: stats.totals.total, color: "text-stone-700" },
        ].map((item) => (
          <div
            key={item.label}
            className="rounded-xl border border-stone-200 bg-white/70 px-4 py-3 text-center"
          >
            <div className="text-xs text-stone-400">{item.label}</div>
            <div className={`mt-1 text-2xl font-bold tabular-nums ${item.color}`}>
              {item.value}
            </div>
          </div>
        ))}
      </div>

      {/* 步骤成功率 */}
      <div className="rounded-xl border border-stone-200 bg-white/70 p-4">
        <h2 className="mb-3 text-sm font-semibold text-stone-800">步骤成功率</h2>
        <div className="space-y-3">
          {STEP_ORDER.map((key) => {
            const stat = stats.step_stats[key];
            if (!stat) return null;
            return (
              <div key={key} className="space-y-1">
                <div className="flex justify-between text-xs text-stone-500">
                  <span>{STEP_LABELS[key] || key}</span>
                  <span>
                    {stat.success}/{stat.total}
                    {stat.fail > 0 && (
                      <span className="ml-1 text-rose-400">({stat.fail} 失败)</span>
                    )}
                  </span>
                </div>
                <StepBar stat={stat} />
              </div>
            );
          })}
        </div>
      </div>

      {/* 代理 + 域名 双栏 */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* 代理统计 */}
        {Object.keys(stats.proxy_stats).length > 0 && (
          <div className="rounded-xl border border-stone-200 bg-white/70 p-4">
            <h2 className="mb-3 text-sm font-semibold text-stone-800">代理成功率</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-stone-100 text-stone-400">
                    <th className="pb-2 text-left font-medium">代理 IP</th>
                    <th className="pb-2 text-right font-medium">成功</th>
                    <th className="pb-2 text-right font-medium">失败</th>
                    <th className="pb-2 text-right font-medium">总计</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(stats.proxy_stats).map(([proxy, ps]) => (
                    <tr key={proxy} className="border-b border-stone-50 last:border-0">
                      <td className="py-1.5 font-mono">
                        {proxy}
                        {ps.cooldown && (
                          <span className="ml-1 text-amber-500" title="冷却中">🔒</span>
                        )}
                      </td>
                      <td className="py-1.5 text-right text-emerald-600 tabular-nums">{ps.success}</td>
                      <td className="py-1.5 text-right text-rose-400 tabular-nums">{ps.fail}</td>
                      <td className="py-1.5 text-right tabular-nums text-stone-600">{ps.total}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* 域名统计 */}
        {Object.keys(stats.domain_stats).length > 0 && (
          <div className="rounded-xl border border-stone-200 bg-white/70 p-4">
            <h2 className="mb-3 text-sm font-semibold text-stone-800">域名成功率</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-stone-100 text-stone-400">
                    <th className="pb-2 text-left font-medium">域名</th>
                    <th className="pb-2 text-right font-medium">成功</th>
                    <th className="pb-2 text-right font-medium">失败</th>
                    <th className="pb-2 text-right font-medium">总计</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(stats.domain_stats).map(([domain, ds]) => (
                    <tr key={domain} className="border-b border-stone-50 last:border-0">
                      <td className="py-1.5 font-mono">
                        {domain}
                        {ds.blocked && (
                          <span className="ml-1 text-rose-500" title="被 OpenAI 封禁">⚠️</span>
                        )}
                      </td>
                      <td className="py-1.5 text-right text-emerald-600 tabular-nums">{ds.success}</td>
                      <td className="py-1.5 text-right text-rose-400 tabular-nums">{ds.fail}</td>
                      <td className="py-1.5 text-right tabular-nums text-stone-600">{ds.total}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* 最近任务 */}
      <div className="rounded-xl border border-stone-200 bg-white/70 p-4">
        <h2 className="mb-3 text-sm font-semibold text-stone-800">
          最近任务
          <span className="ml-2 font-normal text-stone-400">
            ({stats.recent_tasks.length})
          </span>
        </h2>
        {stats.recent_tasks.length === 0 ? (
          <p className="text-xs text-stone-400">暂无任务记录</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-stone-100 text-stone-400">
                  <th className="pb-2 text-left font-medium">#</th>
                  <th className="pb-2 text-left font-medium">状态</th>
                  <th className="pb-2 text-left font-medium">失败步骤</th>
                  <th className="pb-2 text-right font-medium">耗时</th>
                  <th className="pb-2 text-left font-medium">错误</th>
                </tr>
              </thead>
              <tbody>
                {[...stats.recent_tasks].reverse().map((task) => (
                  <tr key={task.index} className="border-b border-stone-50 last:border-0">
                    <td className="py-1.5 tabular-nums text-stone-500">{task.index}</td>
                    <td className="py-1.5">
                      {task.status === "success" ? (
                        <span className="text-emerald-600">✅</span>
                      ) : (
                        <span className="text-rose-400">❌</span>
                      )}
                    </td>
                    <td className="py-1.5 text-stone-600">
                      {task.failed_step ? (STEP_LABELS[task.failed_step] || task.failed_step) : "-"}
                    </td>
                    <td className="py-1.5 text-right tabular-nums text-stone-500">
                      {task.duration.toFixed(1)}s
                    </td>
                    <td className="max-w-[240px] truncate py-1.5 font-mono text-stone-400" title={task.error}>
                      {task.error || "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
