"use client";

import { useMemo, useState } from "react";
import {
  enqueueRefreshJob,
  fetchFinancials,
  fetchPrices,
  fetchValuations,
  refreshFinancials,
  refreshPrices,
  refreshValuations,
} from "@/lib/api";
import { Financial, PriceHistory, Valuation } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { EmptyState, Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";

const DATA_TYPES = ["prices", "valuations", "financials"] as const;
type DataType = (typeof DATA_TYPES)[number];

type Row = PriceHistory | Valuation | Financial;

export default function DataConsolePage() {
  const [tsCode, setTsCode] = useState("demo");
  const [dataType, setDataType] = useState<DataType>("prices");
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<string | null>(null);

  const columns = useMemo(() => {
    if (dataType === "prices") {
      return ["trade_date", "close", "open", "high", "low", "volume"] as const;
    }
    if (dataType === "valuations") {
      return ["date", "pe", "pb", "ps", "ev_ebitda"] as const;
    }
    return ["period", "revenue", "profit", "roe", "roa", "debt_ratio"] as const;
  }, [dataType]);

  const handleFetch = async () => {
    if (!tsCode.trim()) return;
    try {
      setLoading(true);
      setError(null);
      let data: Row[] = [];
      if (dataType === "prices") {
        data = await fetchPrices(tsCode.trim());
      } else if (dataType === "valuations") {
        data = await fetchValuations(tsCode.trim());
      } else {
        data = await fetchFinancials(tsCode.trim());
      }
      setRows(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch data");
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    if (!tsCode.trim()) return;
    try {
      setLoading(true);
      setError(null);
      if (dataType === "prices") {
        await refreshPrices(tsCode.trim());
      } else if (dataType === "valuations") {
        await refreshValuations(tsCode.trim());
      } else {
        await refreshFinancials(tsCode.trim());
      }
      await handleFetch();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Refresh failed");
    } finally {
      setLoading(false);
    }
  };

  const handleJob = async () => {
    if (!tsCode.trim()) return;
    try {
      setError(null);
      const res = await enqueueRefreshJob([tsCode.trim()]);
      setJobStatus(`${res.status} ${res.symbols?.join(", ") || ""}`.trim());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Job enqueue failed");
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div>
            <CardTitle>Data Console</CardTitle>
            <CardDescription>Fetch or refresh cached data per ts_code.</CardDescription>
          </div>
        </CardHeader>
        <div className="grid gap-3 sm:grid-cols-[1fr_200px_200px]">
          <Input
            placeholder="ts_code (e.g. 000001.SZ)"
            value={tsCode}
            onChange={(e) => setTsCode(e.target.value)}
          />
          <select
            className="h-9 rounded-md border border-slate-200 bg-white px-3 text-sm shadow-sm"
            value={dataType}
            onChange={(e) => setDataType(e.target.value as DataType)}
          >
            {DATA_TYPES.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
          <div className="flex gap-2">
            <Button onClick={handleFetch} disabled={loading} variant="secondary">
              Fetch
            </Button>
            <Button onClick={handleRefresh} disabled={loading}>
              Refresh
            </Button>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2 text-sm text-slate-700">
          <Button variant="ghost" className="px-2" onClick={handleJob} disabled={loading}>
            Enqueue Background Refresh
          </Button>
          {jobStatus && <Badge variant="info">{jobStatus}</Badge>}
          {error && <span className="text-red-600">{error}</span>}
          {loading && <span>Loading...</span>}
        </div>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Results</CardTitle>
          <CardDescription>Latest response data.</CardDescription>
        </CardHeader>
        {rows.length === 0 && !loading ? (
          <EmptyState>No data yet. Fetch to view results.</EmptyState>
        ) : (
          <Table>
            <THead>
              <TR>
                {columns.map((col) => (
                  <TH key={col}>{col}</TH>
                ))}
              </TR>
            </THead>
            <TBody>
              {rows.map((row, idx) => (
                <TR key={idx}>
                  {columns.map((col) => (
                    <TD key={col}>{formatValue((row as Record<string, unknown>)[col])}</TD>
                  ))}
                </TR>
              ))}
            </TBody>
          </Table>
        )}
      </Card>
    </div>
  );
}

function formatValue(value: unknown) {
  if (value === null || value === undefined) return "-";
  if (typeof value === "number") return value.toFixed(4).replace(/\.0+$/, "").replace(/\.0$/, "");
  if (typeof value === "string") return value;
  return String(value);
}
