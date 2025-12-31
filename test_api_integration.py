#!/usr/bin/env python3
"""测试通过项目 API 获取 Tushare 数据"""

import asyncio
import os
import sys

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.app.config import get_settings
from backend.app.services.tushare_client import TushareService


async def test_api_integration():
    """测试通过项目的 TushareService 获取数据"""
    print("=" * 60)
    print("项目 API 集成测试")
    print("=" * 60)
    
    # 检查环境变量
    token = os.getenv("TUSHARE_TOKEN")
    if not token:
        print("❌ 错误: 未设置 TUSHARE_TOKEN 环境变量")
        return False
    
    # 初始化数据库连接
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    test_code = "000001.SZ"  # 平安银行
    
    try:
        async with async_session() as session:
            service = TushareService(session)
            
            # 测试 1: 获取价格数据
            print(f"\n测试 1: 通过 TushareService 获取 {test_code} 的价格数据...")
            try:
                prices = await service.fetch_daily_prices(ts_code=test_code)
                if prices:
                    print(f"✅ 成功获取 {len(prices)} 条价格记录")
                    latest = prices[0] if prices else None
                    if latest:
                        print(f"   最新记录: {latest.trade_date} - 收盘价: {latest.close}")
                else:
                    print("⚠️  未获取到价格数据")
            except Exception as e:
                print(f"❌ 获取价格数据失败: {e}")
                import traceback
                traceback.print_exc()
                return False
            
            # 测试 2: 获取财务数据
            print(f"\n测试 2: 通过 TushareService 获取 {test_code} 的财务数据...")
            try:
                financials = await service.fetch_financials(ts_code=test_code)
                if financials:
                    print(f"✅ 成功获取 {len(financials)} 条财务记录")
                    latest = financials[0] if financials else None
                    if latest:
                        print(f"   最新记录: {latest.period} - ROE: {latest.roe}, ROA: {latest.roa}")
                else:
                    print("⚠️  未获取到财务数据")
            except Exception as e:
                print(f"❌ 获取财务数据失败: {e}")
                import traceback
                traceback.print_exc()
                return False
            
            # 测试 3: 获取估值数据
            print(f"\n测试 3: 通过 TushareService 获取 {test_code} 的估值数据...")
            try:
                valuations = await service.fetch_valuations(ts_code=test_code)
                if valuations:
                    print(f"✅ 成功获取 {len(valuations)} 条估值记录")
                    latest = valuations[0] if valuations else None
                    if latest:
                        print(f"   最新记录: {latest.date} - PE: {latest.pe}, PB: {latest.pb}, PS: {latest.ps}")
                else:
                    print("⚠️  未获取到估值数据")
            except Exception as e:
                print(f"❌ 获取估值数据失败: {e}")
                import traceback
                traceback.print_exc()
                return False
            
            # 测试 4: 测试缓存机制（再次获取应该从缓存读取）
            print(f"\n测试 4: 测试缓存机制（再次获取应使用缓存）...")
            try:
                prices_cached = await service.list_prices(ts_code=test_code, limit=10)
                if prices_cached:
                    print(f"✅ 从缓存读取到 {len(prices_cached)} 条价格记录")
                else:
                    print("⚠️  缓存中无数据")
            except Exception as e:
                print(f"❌ 读取缓存失败: {e}")
                return False
    
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()
    
    print("\n" + "=" * 60)
    print("✅ 所有 API 集成测试通过！")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_api_integration())
    sys.exit(0 if success else 1)

