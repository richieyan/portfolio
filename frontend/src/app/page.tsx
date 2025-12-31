"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { createPortfolio, listPortfolios } from "@/lib/api";
import { Portfolio } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { EmptyState, Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";

export default function Home() {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newName, setNewName] = useState("");

  const loadPortfolios = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await listPortfolios();
      setPortfolios(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load portfolios");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPortfolios();
  }, []);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    try {
      setError(null);
      await createPortfolio(newName.trim());
      setNewName("");
      await loadPortfolios();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create portfolio");
    }
  };

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_380px]">
      <div className="space-y-4">
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Portfolios</CardTitle>
              <CardDescription>List and navigate to holdings dashboard.</CardDescription>
            </div>
            <Button onClick={loadPortfolios} disabled={loading} variant="secondary">
              Refresh
            </Button>
          </CardHeader>
          {error && <p className="text-sm text-red-600">{error}</p>}
          {portfolios.length === 0 && !loading ? (
            <EmptyState>No portfolios yet. Create one to get started.</EmptyState>
          ) : (
            <Table>
              <THead>
                <TR>
                  <TH>Name</TH>
                  <TH>Created</TH>
                  <TH>Action</TH>
                </TR>
              </THead>
              <TBody>
                {portfolios.map((p) => (
                  <TR key={p.id}>
                    <TD className="font-medium text-slate-900">{p.name}</TD>
                    <TD>{new Date(p.created_at).toLocaleString()}</TD>
                    <TD>
                      <Link href={`/portfolios/${p.id}`} className="text-sm font-semibold text-slate-900 underline">
                        Open
                      </Link>
                    </TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          )}
          {loading && <p className="pt-3 text-sm text-slate-600">Loading...</p>}
        </Card>
      </div>

      <div className="space-y-4">
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Create Portfolio</CardTitle>
              <CardDescription>Name only, holdings can be added later.</CardDescription>
            </div>
          </CardHeader>
          <div className="space-y-3">
            <Input
              placeholder="e.g. Alpha Fund"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
            />
            <Button onClick={handleCreate} disabled={loading || !newName.trim()}>
              Create
            </Button>
          </div>
        </Card>

        <Card>
          <CardHeader>
            <div>
              <CardTitle>Quick Links</CardTitle>
              <CardDescription>Jump to core consoles.</CardDescription>
            </div>
          </CardHeader>
          <div className="flex flex-col gap-2 text-sm font-medium text-slate-800">
            <Link className="underline" href="/console">
              Data Console (refresh/fetch)
            </Link>
            <Link className="underline" href="/stocks/demo">
              Stock Analysis (demo ts_code)
            </Link>
            <Link className="underline" href="/portfolios/1">
              Portfolio Dashboard (id=1)
            </Link>
          </div>
        </Card>
      </div>
    </div>
  );
}
