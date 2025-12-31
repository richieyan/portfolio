"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { createHolding, deleteHolding, listHoldings } from "@/lib/api";
import { Holding } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { EmptyState, Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";

export default function PortfolioPage() {
  const params = useParams<{ id: string }>();
  const portfolioId = Number(params.id);
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({ ts_code: "", qty: "100", buy_price: "10", buy_date: "" });

  const load = async () => {
    if (!portfolioId) return;
    try {
      setLoading(true);
      setError(null);
      const data = await listHoldings(portfolioId);
      setHoldings(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load holdings");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [portfolioId]);

  const handleAdd = async () => {
    if (!form.ts_code.trim()) return;
    try {
      setLoading(true);
      setError(null);
      await createHolding({
        portfolio_id: portfolioId,
        ts_code: form.ts_code.trim(),
        qty: Number(form.qty),
        buy_price: Number(form.buy_price),
        buy_date: form.buy_date || undefined,
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Add failed");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      setLoading(true);
      setError(null);
      await deleteHolding(id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div>
            <CardTitle>Portfolio #{portfolioId}</CardTitle>
            <CardDescription>View and manage holdings.</CardDescription>
          </div>
          <Button onClick={load} disabled={loading} variant="secondary">
            Refresh
          </Button>
        </CardHeader>
        <div className="grid gap-3 sm:grid-cols-4">
          <Input
            placeholder="ts_code"
            value={form.ts_code}
            onChange={(e) => setForm({ ...form, ts_code: e.target.value })}
          />
          <Input
            type="number"
            placeholder="qty"
            value={form.qty}
            onChange={(e) => setForm({ ...form, qty: e.target.value })}
          />
          <Input
            type="number"
            placeholder="buy price"
            value={form.buy_price}
            onChange={(e) => setForm({ ...form, buy_price: e.target.value })}
          />
          <Input
            type="date"
            value={form.buy_date}
            onChange={(e) => setForm({ ...form, buy_date: e.target.value })}
          />
        </div>
        <div className="mt-3 flex items-center gap-3 text-sm text-slate-700">
          <Button onClick={handleAdd} disabled={loading}>
            Add holding
          </Button>
          {loading && <span>Working...</span>}
          {error && <span className="text-red-600">{error}</span>}
        </div>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Holdings</CardTitle>
          <CardDescription>Current holdings for this portfolio.</CardDescription>
        </CardHeader>
        {holdings.length === 0 ? (
          <EmptyState>No holdings yet.</EmptyState>
        ) : (
          <Table>
            <THead>
              <TR>
                <TH>ts_code</TH>
                <TH>Qty</TH>
                <TH>Buy Price</TH>
                <TH>Buy Date</TH>
                <TH>Tags</TH>
                <TH></TH>
              </TR>
            </THead>
            <TBody>
              {holdings.map((h) => (
                <TR key={h.id}>
                  <TD className="font-semibold text-slate-900">{h.ts_code}</TD>
                  <TD>{h.qty}</TD>
                  <TD>{h.buy_price}</TD>
                  <TD>{h.buy_date || "-"}</TD>
                  <TD>{h.tags || "-"}</TD>
                  <TD>
                    <Button variant="ghost" className="px-2 text-red-600" onClick={() => handleDelete(h.id)}>
                      Delete
                    </Button>
                  </TD>
                </TR>
              ))}
            </TBody>
          </Table>
        )}
      </Card>
    </div>
  );
}