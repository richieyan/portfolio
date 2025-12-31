"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listStocks } from "@/lib/api";
import { Stock } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { EmptyState, Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";

const PAGE_SIZE = 20;

export default function StocksListPage() {
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [currentPage, setCurrentPage] = useState(0);
  const [searchInput, setSearchInput] = useState("");

  const loadStocks = async (page: number, searchTerm?: string) => {
    try {
      setLoading(true);
      setError(null);
      const offset = page * PAGE_SIZE;
      const response = await listStocks(searchTerm, PAGE_SIZE, offset);
      setStocks(response.stocks);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load stocks");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStocks(currentPage, search || undefined);
  }, [currentPage, search]);

  const handleSearch = () => {
    setSearch(searchInput);
    setCurrentPage(0);
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div>
            <CardTitle>股票列表</CardTitle>
            <CardDescription>查看数据库中所有已存在的股票</CardDescription>
          </div>
        </CardHeader>
        <div className="space-y-3">
          <div className="flex gap-2">
            <Input
              placeholder="搜索股票代码、名称或行业..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyPress={handleKeyPress}
            />
            <Button onClick={handleSearch} disabled={loading}>
              搜索
            </Button>
            {search && (
              <Button variant="ghost" onClick={() => {
                setSearchInput("");
                setSearch("");
                setCurrentPage(0);
              }}>
                清除
              </Button>
            )}
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
        </div>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>股票列表</CardTitle>
              <CardDescription>
                共 {total} 只股票，第 {currentPage + 1} / {totalPages || 1} 页
              </CardDescription>
            </div>
            <Button onClick={() => loadStocks(currentPage, search || undefined)} disabled={loading} variant="secondary">
              刷新
            </Button>
          </div>
        </CardHeader>
        {loading && <p className="p-4 text-sm text-slate-600">加载中...</p>}
        {!loading && stocks.length === 0 ? (
          <EmptyState>暂无股票数据</EmptyState>
        ) : (
          <>
            <Table>
              <THead>
                <TR>
                  <TH>股票代码</TH>
                  <TH>名称</TH>
                  <TH>行业</TH>
                  <TH>状态</TH>
                  <TH>操作</TH>
                </TR>
              </THead>
              <TBody>
                {stocks.map((stock) => (
                  <TR key={stock.id}>
                    <TD className="font-medium text-slate-900">{stock.ts_code}</TD>
                    <TD>{stock.name || "-"}</TD>
                    <TD>{stock.sector || "-"}</TD>
                    <TD>{stock.active ? "活跃" : "停牌"}</TD>
                    <TD>
                      <Link
                        href={`/stocks/${stock.ts_code}`}
                        className="text-sm font-semibold text-slate-900 underline"
                      >
                        查看详情
                      </Link>
                    </TD>
                  </TR>
                ))}
              </TBody>
            </Table>
            {totalPages > 1 && (
              <div className="mt-4 flex items-center justify-center gap-2">
                <Button
                  variant="outline"
                  onClick={() => setCurrentPage(Math.max(0, currentPage - 1))}
                  disabled={currentPage === 0 || loading}
                >
                  上一页
                </Button>
                <span className="text-sm text-slate-600">
                  第 {currentPage + 1} / {totalPages} 页
                </span>
                <Button
                  variant="outline"
                  onClick={() => setCurrentPage(Math.min(totalPages - 1, currentPage + 1))}
                  disabled={currentPage >= totalPages - 1 || loading}
                >
                  下一页
                </Button>
              </div>
            )}
          </>
        )}
      </Card>
    </div>
  );
}

