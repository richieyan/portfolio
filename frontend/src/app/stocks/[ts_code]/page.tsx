"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import {
  createAnalysis,
  fetchPrices,
  fetchValuations,
  getStockDetail,
  refreshPrices,
  refreshValuations,
} from "@/lib/api";
import { Analysis, PriceHistory, StockDetailResponse, Valuation } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { EmptyState, Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
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
  const [detail, setDetail] = useState<StockDetailResponse | null>(null);
  const [prices, setPrices] = useState<PriceHistory[]>([]);
  const [valuations, setValuations] = useState<Valuation[]>([]);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [targetReturn, setTargetReturn] = useState(0.1);
  const [horizonYears, setHorizonYears] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"income" | "balance" | "cashflow">("income");
  const [daysRange, setDaysRange] = useState(90);

  const chartData = useMemo(() => {
    const sorted = prices
      .slice()
      .sort((a, b) => a.trade_date.localeCompare(b.trade_date))
      .slice(-daysRange);
    return sorted.map((p) => ({
      date: p.trade_date,
      close: p.close,
      open: p.open ?? p.close,
      high: p.high ?? p.close,
      low: p.low ?? p.close,
      volume: p.volume ?? 0,
    }));
  }, [prices, daysRange]);

  const klineData = useMemo(() => {
    return chartData.map((d) => ({
      ...d,
      dateShort: d.date.slice(5),
    }));
  }, [chartData]);

  useEffect(() => {
    if (!tsCode) return;
    const load = async () => {
      try {
        setLoading(true);
        setError(null);
        const [detailData, p, v] = await Promise.all([
          getStockDetail(tsCode),
          fetchPrices(tsCode, 1000),
          fetchValuations(tsCode),
        ]);
        setDetail(detailData);
        setPrices(p);
        setValuations(v);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load data");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [tsCode]);

  const handleRefresh = async () => {
    try {
      setLoading(true);
      setError(null);
      await Promise.all([refreshPrices(tsCode), refreshValuations(tsCode)]);
      const [detailData, p, v] = await Promise.all([
        getStockDetail(tsCode),
        fetchPrices(tsCode, 1000),
        fetchValuations(tsCode),
      ]);
      setDetail(detailData);
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
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>{detail?.stock.name || tsCode}</CardTitle>
              <CardDescription>
                {tsCode} {detail?.stock.sector ? `· ${detail.stock.sector}` : ""}
              </CardDescription>
            </div>
            <div className="flex gap-2">
              <Button onClick={handleRefresh} disabled={loading}>
                刷新数据
              </Button>
            </div>
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

      {detail && (
        <Card>
          <CardHeader>
            <CardTitle>基础数据</CardTitle>
            <CardDescription>最新价格、估值和财务指标</CardDescription>
          </CardHeader>
          <div className="grid gap-4 sm:grid-cols-3">
            {detail.latest_price && (
              <div>
                <p className="text-sm text-slate-600">最新价格</p>
                <p className="text-2xl font-bold">{detail.latest_price.close.toFixed(2)}</p>
                <p className="text-xs text-slate-500">{detail.latest_price.trade_date}</p>
                {detail.latest_price.volume && (
                  <p className="text-xs text-slate-500">成交量: {(detail.latest_price.volume / 10000).toFixed(2)}万</p>
                )}
              </div>
            )}
            {detail.latest_valuation && (
              <div>
                <p className="text-sm text-slate-600">估值指标</p>
                <div className="space-y-1 text-sm">
                  <p>PE: {fmt(detail.latest_valuation.pe)}</p>
                  <p>PB: {fmt(detail.latest_valuation.pb)}</p>
                  <p>PS: {fmt(detail.latest_valuation.ps)}</p>
                </div>
              </div>
            )}
            {detail.latest_financial && (
              <div>
                <p className="text-sm text-slate-600">财务指标</p>
                <div className="space-y-1 text-sm">
                  <p>ROE: {fmt(detail.latest_financial.roe)}%</p>
                  <p>ROA: {fmt(detail.latest_financial.roa)}%</p>
                  <p>负债率: {fmt(detail.latest_financial.debt_ratio)}%</p>
                </div>
              </div>
            )}
          </div>
        </Card>
      )}

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>K 线图</CardTitle>
              <CardDescription>价格走势和成交量</CardDescription>
            </div>
            <div className="flex gap-2">
              <Button
                variant={daysRange === 30 ? "default" : "outline"}
                size="sm"
                onClick={() => setDaysRange(30)}
              >
                30天
              </Button>
              <Button
                variant={daysRange === 60 ? "default" : "outline"}
                size="sm"
                onClick={() => setDaysRange(60)}
              >
                60天
              </Button>
              <Button
                variant={daysRange === 90 ? "default" : "outline"}
                size="sm"
                onClick={() => setDaysRange(90)}
              >
                90天
              </Button>
            </div>
          </div>
        </CardHeader>
        {klineData.length === 0 ? (
          <EmptyState>暂无价格数据</EmptyState>
        ) : (
          <div className="space-y-4">
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={klineData} margin={{ left: 8, right: 8, top: 8, bottom: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="dateShort" tick={{ fontSize: 10 }} />
                  <YAxis yAxisId="price" tick={{ fontSize: 10 }} domain={["auto", "auto"]} />
                  <YAxis yAxisId="volume" orientation="right" tick={{ fontSize: 10 }} />
                  <Tooltip
                    formatter={(value: number, name: string) => {
                      if (name === "volume") return `${(value / 10000).toFixed(2)}万`;
                      return value.toFixed(2);
                    }}
                    labelFormatter={(label) => `日期: ${label}`}
                  />
                  <Line
                    yAxisId="price"
                    type="monotone"
                    dataKey="close"
                    stroke="#0f172a"
                    dot={false}
                    strokeWidth={2}
                    name="收盘价"
                  />
                  <Bar yAxisId="volume" dataKey="volume" fill="#94a3b8" opacity={0.3} name="成交量" />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
            <div className="grid grid-cols-4 gap-2 text-xs text-slate-600">
              <div>
                <p>开盘: {klineData[klineData.length - 1]?.open.toFixed(2)}</p>
              </div>
              <div>
                <p>最高: {klineData[klineData.length - 1]?.high.toFixed(2)}</p>
              </div>
              <div>
                <p>最低: {klineData[klineData.length - 1]?.low.toFixed(2)}</p>
              </div>
              <div>
                <p>收盘: {klineData[klineData.length - 1]?.close.toFixed(2)}</p>
              </div>
            </div>
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

      {detail && (
        <Card>
          <CardHeader>
            <CardTitle>财务报表</CardTitle>
            <CardDescription>利润表、资产负债表、现金流量表</CardDescription>
          </CardHeader>
          <div className="mb-4 flex gap-2 border-b">
            <Button
              variant={activeTab === "income" ? "default" : "ghost"}
              onClick={() => setActiveTab("income")}
            >
              利润表 ({detail.income_statements.length})
            </Button>
            <Button
              variant={activeTab === "balance" ? "default" : "ghost"}
              onClick={() => setActiveTab("balance")}
            >
              资产负债表 ({detail.balance_sheets.length})
            </Button>
            <Button
              variant={activeTab === "cashflow" ? "default" : "ghost"}
              onClick={() => setActiveTab("cashflow")}
            >
              现金流量表 ({detail.cash_flow_statements.length})
            </Button>
          </div>
          {activeTab === "income" && (
            <div className="overflow-x-auto">
              {detail.income_statements.length === 0 ? (
                <EmptyState>暂无利润表数据</EmptyState>
              ) : (
                <Table>
                  <THead>
                    <TR>
                      <TH>期间</TH>
                      <TH>营业收入</TH>
                      <TH>营业利润</TH>
                      <TH>利润总额</TH>
                      <TH>净利润</TH>
                      <TH>基本每股收益</TH>
                      <TH>稀释每股收益</TH>
                    </TR>
                  </THead>
                  <TBody>
                    {detail.income_statements.map((s) => (
                      <TR key={s.id}>
                        <TD>{s.period}</TD>
                        <TD>{fmt(s.revenue)}</TD>
                        <TD>{fmt(s.operating_profit)}</TD>
                        <TD>{fmt(s.total_profit)}</TD>
                        <TD>{fmt(s.net_profit)}</TD>
                        <TD>{fmt(s.basic_eps)}</TD>
                        <TD>{fmt(s.diluted_eps)}</TD>
                      </TR>
                    ))}
                  </TBody>
                </Table>
              )}
            </div>
          )}
          {activeTab === "balance" && (
            <div className="overflow-x-auto">
              {detail.balance_sheets.length === 0 ? (
                <EmptyState>暂无资产负债表数据</EmptyState>
              ) : (
                <Table>
                  <THead>
                    <TR>
                      <TH>期间</TH>
                      <TH>总资产</TH>
                      <TH>总负债</TH>
                      <TH>股东权益</TH>
                      <TH>固定资产</TH>
                      <TH>流动资产</TH>
                      <TH>流动负债</TH>
                    </TR>
                  </THead>
                  <TBody>
                    {detail.balance_sheets.map((s) => (
                      <TR key={s.id}>
                        <TD>{s.period}</TD>
                        <TD>{fmt(s.total_assets)}</TD>
                        <TD>{fmt(s.total_liab)}</TD>
                        <TD>{fmt(s.total_equity)}</TD>
                        <TD>{fmt(s.fixed_assets)}</TD>
                        <TD>{fmt(s.current_assets)}</TD>
                        <TD>{fmt(s.current_liab)}</TD>
                      </TR>
                    ))}
                  </TBody>
                </Table>
              )}
            </div>
          )}
          {activeTab === "cashflow" && (
            <div className="overflow-x-auto">
              {detail.cash_flow_statements.length === 0 ? (
                <EmptyState>暂无现金流量表数据</EmptyState>
              ) : (
                <Table>
                  <THead>
                    <TR>
                      <TH>期间</TH>
                      <TH>净利润</TH>
                      <TH>经营活动现金流</TH>
                      <TH>投资活动现金流</TH>
                      <TH>筹资活动现金流</TH>
                      <TH>自由现金流</TH>
                    </TR>
                  </THead>
                  <TBody>
                    {detail.cash_flow_statements.map((s) => (
                      <TR key={s.id}>
                        <TD>{s.period}</TD>
                        <TD>{fmt(s.net_profit)}</TD>
                        <TD>{fmt(s.oper_cash_flow)}</TD>
                        <TD>{fmt(s.inv_cash_flow)}</TD>
                        <TD>{fmt(s.fin_cash_flow)}</TD>
                        <TD>{fmt(s.free_cash_flow)}</TD>
                      </TR>
                    ))}
                  </TBody>
                </Table>
              )}
            </div>
          )}
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>分析结果</CardTitle>
          <CardDescription>概率、参数与 DeepSeek 报告</CardDescription>
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
          <EmptyState>运行分析后查看结果</EmptyState>
        )}
      </Card>
    </div>
  );
}

function fmt(value?: number | null) {
  if (value === null || value === undefined) return "-";
  return value.toFixed(4).replace(/\.0+$/, "").replace(/\.0$/, "");
}
