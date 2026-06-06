"use client";

import { useEffect, useRef } from "react";
import { BarChart3, LoaderCircle } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import webConfig from "@/constants/common-env";
import { useAuthGuard } from "@/lib/use-auth-guard";
import type { RegisterConfig } from "@/lib/api";
import { getStoredAuthKey } from "@/store/auth";

import { useSettingsStore } from "../settings/store";
import { RegisterCard } from "./components/register-card";

function RegisterDataController() {
  const didLoadRef = useRef(false);
  const loadRegister = useSettingsStore((state) => state.loadRegister);
  const setRegisterConfig = useSettingsStore((state) => state.setRegisterConfig);

  useEffect(() => {
    if (didLoadRef.current) return;
    didLoadRef.current = true;
    void loadRegister();
  }, [loadRegister]);

  useEffect(() => {
    let source: EventSource | null = null;
    let closed = false;
    void getStoredAuthKey().then((token) => {
      if (closed || !token) return;
      const baseUrl = webConfig.apiUrl.replace(/\/$/, "");
      source = new EventSource(`${baseUrl}/api/register/events?token=${encodeURIComponent(token)}`);
      source.onmessage = (event) => {
        setRegisterConfig(JSON.parse(event.data) as RegisterConfig);
      };
    });
    return () => {
      closed = true;
      source?.close();
    };
  }, [setRegisterConfig]);

  return null;
}

function RegisterPageContent() {
  return (
    <>
      <RegisterDataController />
      <div className="mb-4 flex items-center justify-end">
        <Link href="/register/stats">
          <Button variant="outline" size="sm" className="gap-1.5 rounded-xl border-stone-200 bg-white">
            <BarChart3 className="size-4" />
            统计看板
          </Button>
        </Link>
      </div>
      <section className="mb-2 flex flex-col gap-1 lg:flex-row lg:items-start lg:justify-between">
        <div className="space-y-1">
          <div className="text-xs font-semibold tracking-[0.18em] text-stone-500 uppercase">Register</div>
          <h1 className="text-2xl font-semibold tracking-tight">ChatGPT注册机</h1>
        </div>
      </section>
      <section>
        <RegisterCard />
      </section>
    </>
  );
}

export default function RegisterPage() {
  const { isCheckingAuth, session } = useAuthGuard(["admin"]);

  if (isCheckingAuth || !session || session.role !== "admin") {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <LoaderCircle className="size-5 animate-spin text-stone-400" />
      </div>
    );
  }

  return <RegisterPageContent />;
}