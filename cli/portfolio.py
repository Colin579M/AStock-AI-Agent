"""
Portfolio管理模块

管理自选股组合：创建、编辑、删除、重命名portfolio，添加/移除股票
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from rich.console import Console
from rich.table import Table

console = Console()


class PortfolioManager:
    """Portfolio自选股管理器"""

    def __init__(self, data_dir: Path):
        """
        初始化Portfolio管理器

        Args:
            data_dir: 数据存储目录
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.data_file = self.data_dir / "portfolios.json"
        self._ensure_data_file()

    def _ensure_data_file(self):
        """确保数据文件存在"""
        if not self.data_file.exists():
            self._save_data({
                "portfolios": {},
                "default": None
            })

    def _load_data(self) -> Dict:
        """加载portfolio数据"""
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"portfolios": {}, "default": None}

    def _save_data(self, data: Dict):
        """保存portfolio数据"""
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def list_portfolios(self) -> List[Dict]:
        """
        列出所有portfolio

        Returns:
            portfolio列表，每个包含name, stock_count, created_at, is_default
        """
        data = self._load_data()
        result = []
        for name, info in data["portfolios"].items():
            result.append({
                "name": name,
                "stock_count": len(info.get("stocks", [])),
                "created_at": info.get("created_at", "未知"),
                "updated_at": info.get("updated_at", "未知"),
                "is_default": name == data.get("default")
            })
        return result

    def create(self, name: str, set_default: bool = False) -> bool:
        """
        创建新portfolio

        Args:
            name: portfolio名称
            set_default: 是否设为默认

        Returns:
            是否创建成功
        """
        data = self._load_data()

        if name in data["portfolios"]:
            console.print(f"[red]Portfolio '{name}' 已存在[/red]")
            return False

        now = datetime.now().isoformat()
        data["portfolios"][name] = {
            "created_at": now,
            "updated_at": now,
            "stocks": []
        }

        if set_default or data["default"] is None:
            data["default"] = name

        self._save_data(data)
        console.print(f"[green]Portfolio '{name}' 创建成功[/green]")
        return True

    def delete(self, name: str) -> bool:
        """
        删除portfolio

        Args:
            name: portfolio名称

        Returns:
            是否删除成功
        """
        data = self._load_data()

        if name not in data["portfolios"]:
            console.print(f"[red]Portfolio '{name}' 不存在[/red]")
            return False

        del data["portfolios"][name]

        # 如果删除的是默认portfolio，清除默认设置
        if data["default"] == name:
            data["default"] = list(data["portfolios"].keys())[0] if data["portfolios"] else None

        self._save_data(data)
        console.print(f"[green]Portfolio '{name}' 已删除[/green]")
        return True

    def rename(self, old_name: str, new_name: str) -> bool:
        """
        重命名portfolio

        Args:
            old_name: 原名称
            new_name: 新名称

        Returns:
            是否重命名成功
        """
        data = self._load_data()

        if old_name not in data["portfolios"]:
            console.print(f"[red]Portfolio '{old_name}' 不存在[/red]")
            return False

        if new_name in data["portfolios"]:
            console.print(f"[red]Portfolio '{new_name}' 已存在[/red]")
            return False

        # 移动数据
        data["portfolios"][new_name] = data["portfolios"].pop(old_name)
        data["portfolios"][new_name]["updated_at"] = datetime.now().isoformat()

        # 更新默认设置
        if data["default"] == old_name:
            data["default"] = new_name

        self._save_data(data)
        console.print(f"[green]Portfolio '{old_name}' 已重命名为 '{new_name}'[/green]")
        return True

    def add_stocks(self, name: str, tickers: List[str]) -> bool:
        """
        添加股票到portfolio

        Args:
            name: portfolio名称
            tickers: 股票代码列表

        Returns:
            是否添加成功
        """
        data = self._load_data()

        if name not in data["portfolios"]:
            console.print(f"[red]Portfolio '{name}' 不存在[/red]")
            return False

        existing = set(data["portfolios"][name]["stocks"])
        added = []
        skipped = []

        for ticker in tickers:
            # 标准化股票代码（去除.SH/.SZ后缀，只保留数字）
            clean_ticker = ticker.split(".")[0].strip()
            if clean_ticker in existing:
                skipped.append(clean_ticker)
            else:
                existing.add(clean_ticker)
                added.append(clean_ticker)

        data["portfolios"][name]["stocks"] = list(existing)
        data["portfolios"][name]["updated_at"] = datetime.now().isoformat()
        self._save_data(data)

        if added:
            console.print(f"[green]已添加: {', '.join(added)}[/green]")
        if skipped:
            console.print(f"[yellow]已跳过(重复): {', '.join(skipped)}[/yellow]")

        return True

    def remove_stocks(self, name: str, tickers: List[str]) -> bool:
        """
        从portfolio移除股票

        Args:
            name: portfolio名称
            tickers: 股票代码列表

        Returns:
            是否移除成功
        """
        data = self._load_data()

        if name not in data["portfolios"]:
            console.print(f"[red]Portfolio '{name}' 不存在[/red]")
            return False

        existing = set(data["portfolios"][name]["stocks"])
        removed = []
        not_found = []

        for ticker in tickers:
            clean_ticker = ticker.split(".")[0].strip()
            if clean_ticker in existing:
                existing.remove(clean_ticker)
                removed.append(clean_ticker)
            else:
                not_found.append(clean_ticker)

        data["portfolios"][name]["stocks"] = list(existing)
        data["portfolios"][name]["updated_at"] = datetime.now().isoformat()
        self._save_data(data)

        if removed:
            console.print(f"[green]已移除: {', '.join(removed)}[/green]")
        if not_found:
            console.print(f"[yellow]未找到: {', '.join(not_found)}[/yellow]")

        return True

    def get_stocks(self, name: str) -> Optional[List[str]]:
        """
        获取portfolio中的股票列表

        Args:
            name: portfolio名称

        Returns:
            股票代码列表，不存在返回None
        """
        data = self._load_data()

        if name not in data["portfolios"]:
            return None

        return data["portfolios"][name]["stocks"]

    def get_portfolio_info(self, name: str) -> Optional[Dict]:
        """
        获取portfolio详细信息

        Args:
            name: portfolio名称

        Returns:
            portfolio信息字典
        """
        data = self._load_data()

        if name not in data["portfolios"]:
            return None

        info = data["portfolios"][name].copy()
        info["name"] = name
        info["is_default"] = name == data.get("default")
        return info

    def set_default(self, name: str) -> bool:
        """
        设置默认portfolio

        Args:
            name: portfolio名称

        Returns:
            是否设置成功
        """
        data = self._load_data()

        if name not in data["portfolios"]:
            console.print(f"[red]Portfolio '{name}' 不存在[/red]")
            return False

        data["default"] = name
        self._save_data(data)
        console.print(f"[green]默认Portfolio已设置为 '{name}'[/green]")
        return True

    def get_default(self) -> Optional[str]:
        """获取默认portfolio名称"""
        data = self._load_data()
        return data.get("default")

    def display_list(self):
        """显示portfolio列表表格"""
        portfolios = self.list_portfolios()

        if not portfolios:
            console.print("[yellow]暂无Portfolio，使用 'portfolio create <名称>' 创建[/yellow]")
            return

        table = Table(title="Portfolio 列表")
        table.add_column("名称", style="cyan")
        table.add_column("股票数量", justify="center")
        table.add_column("创建时间")
        table.add_column("更新时间")
        table.add_column("默认", justify="center")

        for p in portfolios:
            table.add_row(
                p["name"],
                str(p["stock_count"]),
                p["created_at"][:10] if p["created_at"] != "未知" else "未知",
                p["updated_at"][:10] if p["updated_at"] != "未知" else "未知",
                "✓" if p["is_default"] else ""
            )

        console.print(table)

    def display_portfolio(self, name: str):
        """显示单个portfolio详情"""
        info = self.get_portfolio_info(name)

        if info is None:
            console.print(f"[red]Portfolio '{name}' 不存在[/red]")
            return

        table = Table(title=f"Portfolio: {name}")
        table.add_column("序号", justify="center", style="dim")
        table.add_column("股票代码", style="cyan")

        for i, ticker in enumerate(info["stocks"], 1):
            table.add_row(str(i), ticker)

        console.print(table)
        console.print(f"\n[dim]共 {len(info['stocks'])} 只股票 | 更新时间: {info['updated_at'][:19]}[/dim]")
