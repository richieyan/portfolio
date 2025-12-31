"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import {
  createAnalysis,
  fetchPrices,
  fetchValuations,
  refreshPrices,
  refreshValuations,
} from "@/lib/api";
import { Analysis, PriceHistory, Valuation } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { EmptyState, Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export default function StockAnalysisPage() {
  const params = useParams<{ ts_code: string }>();
  const tsCode = params.ts_code;
  const [prices, setPrices] = useState<PriceHistory[]>([]);
  const [valuations, setValuations] = useState<Valuation[]>([]);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [targetReturn, setTargetReturn] = useState(0.1);
  const [horizonYears, setHorizonYears] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const chartData = useMemo(
    () =>
      prices
        .slice()
        .sort((a, b) => a.trade_date.localeCompare(b.trade_date))
        .map((p) => ({ date: p.trade_date, close: p.close })),
    [prices]
  );

  useEffect(() => {
    if (!tsCode) return;
    const load = async () => {
      try {
        setError(null);
        const [p, v] = await Promise.all([fetchPrices(tsCode), fetchValuations(tsCode)]);
        setPrices(p);
        setValuations(v);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load data");
      }
    };
    load();
  }, [tsCode]);

  const handleRefresh = async () => {
    try {
      setLoading(true);
      setError(null);
      await Promise.all([refreshPrices(tsCode), refreshValuations(tsCode)]);
      const [p, v] = await Promise.all([fetchPrices(tsCode), fetchValuations(tsCode)]);
      setPrices(p);
      setValuations(v);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Refresh failed");
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyze = async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await createAnalysis({
        ts_code: tsCode,
        target_return: targetReturn,
        horizon_years: horizonYears,
      });
      setAnalysis(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div>
            <CardTitle>个股分析</CardTitle>
            <CardDescription>{tsCode}</CardDescription>
          </div>
          <div className="flex gap-2">
            <Button onClick={handleRefresh} disabled={loading}>
              刷新数据
            </Button>
          </div>
        </CardHeader>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-800">目标收益（小数）</label>
            <Input
              type="number"
              step="0.01"
              value={targetReturn}
              onChange={(e) => setTargetReturn(parseFloat(e.target.value))}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-800">期限（年）</label>
            <Input
              type="number"
              step="0.25"
              value={horizonYears}
              onChange={(e) => setHorizonYears(parseFloat(e.target.value))}
            />
          </div>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-slate-700">
          <Button onClick={handleAnalyze} disabled={loading}>
            运行 GBM 分析
          </Button>
          {loading && <span>计算中...</span>}
          {error && <span className="text-red-600">{error}</span>}
          {analysis?.probability !== undefined && analysis?.probability !== null && (
            <Badge variant="success">P={analysis.probability.toFixed(4)}</Badge>
          )}
        </div>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>价格走势</CardTitle>
          <CardDescription>收盘价曲线（按日期排序）。</CardDescription>
        </CardHeader>
        {chartData.length === 0 ? (
          <EmptyState>暂无价格数据。</EmptyState>
        ) : (
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ left: 8, right: 8, top: 8, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(v) => v.slice(5)} />
                <YAxis tick={{ fontSize: 11 }} domain={["auto", "auto"]} />
                <Tooltip formatter={(value: number) => value.toFixed(2)} labelFormatter={(label) => `Date: ${label}`} />
                <Line type="monotone" dataKey="close" stroke="#0f172a" dot={false} strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>估值</CardTitle>
          <CardDescription>最新估值快照。</CardDescription>
        </CardHeader>
        {valuations.length === 0 ? (
          <EmptyState>暂无估值数据。</EmptyState>
        ) : (
          <Table>
            <THead>
              <TR>
                <TH>Date</TH>
                <TH>PE</TH>
                <TH>PB</TH>
                <TH>PS</TH>
                <TH>EV/EBITDA</TH>
              </TR>
            </THead>
            <TBody>
              {valuations.map((v) => (
                <TR key={v.id}>
                  <TD>{v.date}</TD>
                  <TD>{fmt(v.pe)}</TD>
                  <TD>{fmt(v.pb)}</TD>
                  <TD>{fmt(v.ps)}</TD>
                  <TD>{fmt(v.ev_ebitda)}</TD>
                </TR>
              ))}
            </TBody>
          </Table>
        )}
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>分析结果</CardTitle>
          <CardDescription>概率、参数与 DeepSeek 报告。</CardDescription>
        </CardHeader>
        {analysis ? (
          <div className="space-y-3 text-sm text-slate-800">
            <div className="flex flex-wrap gap-3">
              <Badge variant="success">Probability: {analysis.probability?.toFixed(4) ?? "-"}</Badge>
              <Badge variant="info">mu: {analysis.params_json?.mu?.toFixed(4) ?? "-"}</Badge>
              <Badge variant="info">sigma: {analysis.params_json?.sigma?.toFixed(4) ?? "-"}</Badge>
              <Badge variant="default">n_returns: {analysis.params_json?.n_returns ?? 0}</Badge>
            </div>
            <div>
              <p className="mb-2 text-sm font-semibold text-slate-900">DeepSeek 报告</p>
              <Textarea readOnly value={analysis.params_json?.report || ""} placeholder="暂无报告" />
            </div>
          </div>
        ) : (
          <EmptyState>运行分析后查看结果。</EmptyState>
        )}
      </Card>
    </div>
  );
}

function fmt(value?: number | null) {
  if (value === null || value === undefined) return "-";
  return value.toFixed(4).replace(/\.0+$/, "").replace(/\.0$/, "");
}
