#!/usr/bin/env python3
"""测试 Tushare 数据获取功能"""

import asyncio
import os
import sys
from datetime import datetime

import tushare as ts


def test_tushare_connection():
    """测试 Tushare 连接和基本功能"""
    print("=" * 60)
    print("Tushare 连接测试")
    print("=" * 60)
    
    # 1. 检查环境变量
    token = os.getenv("TUSHARE_TOKEN")
    if not token:
        print("❌ 错误: 未设置 TUSHARE_TOKEN 环境变量")
        print("   请运行: export TUSHARE_TOKEN='your_token'")
        return False
    print(f"✅ TUSHARE_TOKEN 已设置: {token[:10]}...")
    
    # 2. 设置 Token 并初始化 API
    try:
        ts.set_token(token)
        pro = ts.pro_api()
        print("✅ Tushare API 初始化成功")
    except Exception as e:
        print(f"❌ Tushare API 初始化失败: {e}")
        return False
    
    # 3. 测试基本 API 调用（获取股票基本信息）
    print("\n测试 1: 获取股票基本信息...")
    try:
        # 测试获取股票列表（限制 5 条）
        df = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,area,industry')
        if df is not None and not df.empty:
            print(f"✅ 成功获取 {len(df)} 条股票基本信息")
            print(f"   示例: {df.head(3).to_string()}")
        else:
            print("⚠️  返回数据为空")
    except Exception as e:
        print(f"❌ 获取股票基本信息失败: {e}")
        return False
    
    # 4. 测试价格数据获取
    print("\n测试 2: 获取价格数据...")
    test_code = "000001.SZ"  # 平安银行
    try:
        # 获取最近 5 个交易日的数据
        end_date = datetime.now().strftime("%Y%m%d")
        df = pro.daily(ts_code=test_code, start_date="20240101", end_date=end_date)
        if df is not None and not df.empty:
            print(f"✅ 成功获取 {test_code} 的价格数据: {len(df)} 条记录")
            print(f"   最新数据: {df.head(1).to_string()}")
        else:
            print(f"⚠️  {test_code} 返回数据为空")
    except Exception as e:
        print(f"❌ 获取价格数据失败: {e}")
        return False
    
    # 5. 测试财务数据获取
    print("\n测试 3: 获取财务数据...")
    try:
        df = pro.fina_indicator(ts_code=test_code)
        if df is not None and not df.empty:
            print(f"✅ 成功获取 {test_code} 的财务数据: {len(df)} 条记录")
            print(f"   最新数据: {df.head(1)[['ts_code', 'end_date', 'roe', 'roa', 'debt_to_assets']].to_string()}")
        else:
            print(f"⚠️  {test_code} 财务数据为空")
    except Exception as e:
        print(f"❌ 获取财务数据失败: {e}")
        return False
    
    # 6. 测试估值数据获取
    print("\n测试 4: 获取估值数据...")
    try:
        end_date = datetime.now().strftime("%Y%m%d")
        df = pro.daily_basic(ts_code=test_code, start_date="20240101", end_date=end_date)
        if df is not None and not df.empty:
            print(f"✅ 成功获取 {test_code} 的估值数据: {len(df)} 条记录")
            print(f"   最新数据: {df.head(1)[['ts_code', 'trade_date', 'pe_ttm', 'pb', 'ps_ttm']].to_string()}")
        else:
            print(f"⚠️  {test_code} 估值数据为空")
    except Exception as e:
        print(f"❌ 获取估值数据失败: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！Tushare 数据获取功能正常")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_tushare_connection()
    sys.exit(0 if success else 1)

