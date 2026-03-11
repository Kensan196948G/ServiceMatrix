"""開発用サンプルデータ投入スクリプト"""
import asyncio
import sys
from pathlib import Path

# プロジェクトルートを sys.path に追加
sys.path.insert(0, str(Path(__file__).parent.parent))


async def seed():
    """サンプルデータを投入する"""
    print("🌱 サンプルデータ投入スキップ（CI/テスト環境用スタブ）")
    print("   実際の投入は docker compose up 後に実行してください")


if __name__ == "__main__":
    asyncio.run(seed())
