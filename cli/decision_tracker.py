"""
决策追踪器 - 记录分析决策并生成反思报告

功能：
1. 保存每次分析的决策结果
2. 读取上次决策并获取期间行情
3. 计算模拟收益
4. 生成反思报告供当前分析参考
"""
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any


class DecisionTracker:
    """决策追踪器 - 实现分析决策的持久化和反思闭环"""

    def __init__(self, results_base_dir: Path):
        """
        初始化决策追踪器

        Args:
            results_base_dir: 结果目录根路径 (如 results/)
        """
        self.results_base_dir = Path(results_base_dir)

    def _get_decisions_file(self, ticker: str) -> Path:
        """获取股票决策文件路径"""
        ticker_dir = self.results_base_dir / ticker
        ticker_dir.mkdir(parents=True, exist_ok=True)
        return ticker_dir / "decisions.json"

    def _load_decisions(self, ticker: str) -> Dict:
        """加载股票的决策历史"""
        decisions_file = self._get_decisions_file(ticker)
        if decisions_file.exists():
            with open(decisions_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"latest": None, "history": []}

    def _save_decisions(self, ticker: str, data: Dict):
        """保存股票的决策历史"""
        decisions_file = self._get_decisions_file(ticker)
        with open(decisions_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def save_decision(
        self,
        ticker: str,
        analysis_date: str,
        decision: str,
        price: float,
        confidence: float = 0.5,
        key_reasons: List[str] = None,
        full_report: str = None
    ):
        """
        保存本次分析决策

        Args:
            ticker: 股票代码
            analysis_date: 分析日期 (YYYY-MM-DD)
            decision: 决策类型 (BUY/SELL/HOLD)
            price: 当时价格
            confidence: 置信度 (0-1)
            key_reasons: 关键理由列表
            full_report: 完整报告内容（用于后续反思）
        """
        data = self._load_decisions(ticker)

        # 将当前 latest 移入 history
        if data["latest"]:
            data["history"].append(data["latest"])
            # 只保留最近10条历史
            data["history"] = data["history"][-10:]

        # 更新 latest
        data["latest"] = {
            "date": analysis_date,
            "decision": decision.upper(),
            "price": price,
            "confidence": confidence,
            "key_reasons": key_reasons or [],
            "created_at": datetime.now().isoformat(),
            "full_report_summary": self._extract_report_summary(full_report) if full_report else None
        }

        self._save_decisions(ticker, data)

    def _extract_report_summary(self, report: str, max_length: int = 500) -> str:
        """从完整报告中提取摘要"""
        if not report:
            return ""
        # 提取执行摘要部分
        summary_match = re.search(r'## 1\. 执行摘要.*?(?=## 2\.|\Z)', report, re.DOTALL)
        if summary_match:
            summary = summary_match.group(0)
            if len(summary) > max_length:
                summary = summary[:max_length] + "..."
            return summary
        # 如果没找到，返回前500字符
        return report[:max_length] + "..." if len(report) > max_length else report

    def get_previous_decision(self, ticker: str) -> Optional[Dict]:
        """获取上次决策"""
        data = self._load_decisions(ticker)
        return data.get("latest")

    def get_decision_history(self, ticker: str, limit: int = 5) -> List[Dict]:
        """获取决策历史"""
        data = self._load_decisions(ticker)
        history = data.get("history", [])
        if data.get("latest"):
            history = [data["latest"]] + history
        return history[:limit]

    def generate_reflection_report(
        self,
        ticker: str,
        current_date: str,
        current_price: float,
        price_history: List[Dict] = None
    ) -> Optional[str]:
        """
        生成反思报告

        Args:
            ticker: 股票代码
            current_date: 当前分析日期
            current_price: 当前价格
            price_history: 期间价格历史 [{date, open, high, low, close}, ...]

        Returns:
            反思报告 Markdown 字符串，如果没有上次决策则返回 None
        """
        prev = self.get_previous_decision(ticker)
        if not prev:
            return None

        prev_date = prev["date"]
        prev_decision = prev["decision"]
        prev_price = prev["price"]
        prev_confidence = prev.get("confidence", 0.5)
        prev_reasons = prev.get("key_reasons", [])

        # 计算收益
        price_change = current_price - prev_price
        price_change_pct = (price_change / prev_price) * 100 if prev_price else 0

        # 计算期间最高/最低价
        period_high = current_price
        period_low = current_price
        if price_history:
            period_high = max(p.get("high", p.get("close", current_price)) for p in price_history)
            period_low = min(p.get("low", p.get("close", current_price)) for p in price_history)

        # 评估决策正确性
        decision_evaluation = self._evaluate_decision(
            prev_decision, price_change_pct, period_high, period_low, prev_price
        )

        # 计算日期间隔
        try:
            d1 = datetime.strptime(prev_date, "%Y-%m-%d")
            d2 = datetime.strptime(current_date, "%Y-%m-%d")
            days_diff = (d2 - d1).days
        except:
            days_diff = "未知"

        # 生成报告
        report = f"""# 上次决策回顾与反思

## 决策信息
- **分析日期**: {prev_date}
- **决策**: {prev_decision} ({self._decision_cn(prev_decision)})
- **当时价格**: {prev_price:.2f} 元
- **置信度**: {prev_confidence * 100:.0f}%
- **主要理由**: {', '.join(prev_reasons) if prev_reasons else '未记录'}

## 实际表现 ({prev_date} → {current_date}, {days_diff}天)
- **当前价格**: {current_price:.2f} 元
- **期间涨跌**: {price_change:+.2f} 元 ({price_change_pct:+.2f}%)
- **期间最高**: {period_high:.2f} 元 ({((period_high - prev_price) / prev_price * 100):+.2f}%)
- **期间最低**: {period_low:.2f} 元 ({((period_low - prev_price) / prev_price * 100):+.2f}%)

## 决策评估
- **结果**: {decision_evaluation['emoji']} {decision_evaluation['verdict']}
- **评分**: {decision_evaluation['score']}/10
- **模拟收益**: {decision_evaluation['simulated_return']}

## 经验教训
{decision_evaluation['lessons']}

## 本次分析建议关注
{decision_evaluation['focus_points']}

---
"""
        return report

    def _decision_cn(self, decision: str) -> str:
        """决策类型中文"""
        mapping = {"BUY": "买入", "SELL": "卖出", "HOLD": "持有"}
        return mapping.get(decision.upper(), decision)

    def _evaluate_decision(
        self,
        decision: str,
        price_change_pct: float,
        period_high: float,
        period_low: float,
        prev_price: float
    ) -> Dict:
        """评估决策正确性"""
        decision = decision.upper()

        # 计算期间波动
        max_gain = ((period_high - prev_price) / prev_price * 100) if prev_price else 0
        max_loss = ((period_low - prev_price) / prev_price * 100) if prev_price else 0

        result = {
            "emoji": "⚠️",
            "verdict": "评估中",
            "score": 5,
            "simulated_return": "N/A",
            "lessons": "",
            "focus_points": ""
        }

        if decision == "BUY":
            # 买入决策评估
            if price_change_pct > 5:
                result.update({
                    "emoji": "✅",
                    "verdict": "决策正确，买入获利",
                    "score": 9 if price_change_pct > 10 else 8,
                    "simulated_return": f"如果买入: +{price_change_pct:.2f}%",
                    "lessons": f"- 买入决策正确，实现收益 +{price_change_pct:.2f}%\n- 分析逻辑得到验证，可以沿用类似方法",
                    "focus_points": "- 当前是否仍有上涨空间\n- 是否需要调整止盈位置"
                })
            elif price_change_pct > 0:
                result.update({
                    "emoji": "✅",
                    "verdict": "决策正确，小幅获利",
                    "score": 7,
                    "simulated_return": f"如果买入: +{price_change_pct:.2f}%",
                    "lessons": f"- 买入方向正确，但涨幅有限 (+{price_change_pct:.2f}%)\n- 可能需要更好的择时",
                    "focus_points": "- 上涨动能是否持续\n- 是否错过了更好的买点"
                })
            elif price_change_pct > -5:
                result.update({
                    "emoji": "⚠️",
                    "verdict": "决策中性，小幅亏损",
                    "score": 5,
                    "simulated_return": f"如果买入: {price_change_pct:.2f}%",
                    "lessons": f"- 买入决策小幅亏损 ({price_change_pct:.2f}%)\n- 可能是时机问题，不一定是方向错误",
                    "focus_points": "- 基本面是否有变化\n- 技术面是否形成新的支撑"
                })
            else:
                result.update({
                    "emoji": "❌",
                    "verdict": "决策失误，明显亏损",
                    "score": 3 if price_change_pct > -10 else 2,
                    "simulated_return": f"如果买入: {price_change_pct:.2f}%",
                    "lessons": f"- 买入决策造成亏损 ({price_change_pct:.2f}%)\n- 需要反思：是基本面判断错误还是忽略了风险信号？",
                    "focus_points": "- 之前忽略了什么风险信号？\n- 当前是否企稳，还是继续下跌趋势"
                })

        elif decision == "SELL":
            # 卖出决策评估
            if price_change_pct < -5:
                result.update({
                    "emoji": "✅",
                    "verdict": "决策正确，成功规避下跌",
                    "score": 9 if price_change_pct < -10 else 8,
                    "simulated_return": f"规避了 {abs(price_change_pct):.2f}% 的下跌",
                    "lessons": f"- 卖出决策正确，成功规避 {abs(price_change_pct):.2f}% 下跌\n- 风险识别能力得到验证",
                    "focus_points": "- 是否已到底部可以考虑抄底\n- 下跌原因是否已消化"
                })
            elif price_change_pct < 0:
                result.update({
                    "emoji": "✅",
                    "verdict": "决策正确，规避小幅下跌",
                    "score": 7,
                    "simulated_return": f"规避了 {abs(price_change_pct):.2f}% 的下跌",
                    "lessons": f"- 卖出方向正确，规避 {abs(price_change_pct):.2f}% 下跌\n- 风险敏感度适当",
                    "focus_points": "- 是否出现企稳信号\n- 何时可以考虑重新入场"
                })
            elif price_change_pct < 5:
                result.update({
                    "emoji": "⚠️",
                    "verdict": "决策偏保守，错失小幅上涨",
                    "score": 5,
                    "simulated_return": f"错失 +{price_change_pct:.2f}% 上涨",
                    "lessons": f"- 卖出后股价小幅上涨 (+{price_change_pct:.2f}%)\n- 风险评估可能过于保守",
                    "focus_points": "- 上次卖出的担忧是否过虑\n- 当前是否应该追涨"
                })
            else:
                result.update({
                    "emoji": "❌",
                    "verdict": "决策失误，错失上涨",
                    "score": 3 if price_change_pct < 10 else 2,
                    "simulated_return": f"错失 +{price_change_pct:.2f}% 上涨",
                    "lessons": f"- 卖出后股价大涨 (+{price_change_pct:.2f}%)，决策失误\n- 需要反思：是低估了上涨动能还是过度担忧风险？",
                    "focus_points": "- 上次忽略了什么积极信号？\n- 当前是否还有上涨空间"
                })

        else:  # HOLD
            # 持有决策评估
            if abs(price_change_pct) < 3:
                result.update({
                    "emoji": "✅",
                    "verdict": "决策正确，震荡行情持有",
                    "score": 7,
                    "simulated_return": f"持有期间变化 {price_change_pct:+.2f}%",
                    "lessons": "- 持有决策适合震荡行情\n- 判断准确，没有追涨杀跌",
                    "focus_points": "- 是否即将突破方向\n- 需要重新评估多空力量"
                })
            elif price_change_pct > 5:
                result.update({
                    "emoji": "⚠️",
                    "verdict": "持有正确但错失加仓机会",
                    "score": 6,
                    "simulated_return": f"持有收益 +{price_change_pct:.2f}%",
                    "lessons": f"- 持有期间上涨 +{price_change_pct:.2f}%\n- 应该考虑增持而非仅持有",
                    "focus_points": "- 当前是否应该加仓\n- 还是已经涨太多需要减仓"
                })
            else:
                result.update({
                    "emoji": "⚠️",
                    "verdict": "持有决策待商榷",
                    "score": 4,
                    "simulated_return": f"持有亏损 {price_change_pct:.2f}%",
                    "lessons": f"- 持有期间下跌 {price_change_pct:.2f}%\n- 应该考虑减仓而非持有",
                    "focus_points": "- 当前是否应该止损\n- 还是已经跌到支撑位可以加仓"
                })

        return result


def parse_decision_from_report(report: str) -> Dict:
    """
    从最终决策报告中解析决策信息

    Args:
        report: final_trade_decision.md 的内容

    Returns:
        {decision: BUY/SELL/HOLD, confidence: float, reasons: list}
    """
    result = {
        "decision": "HOLD",
        "confidence": 0.5,
        "reasons": []
    }

    # 解析决策类型
    # 匹配 "FINAL TRANSACTION PROPOSAL: **BUY**" 或 "最终交易建议: 【买入】"
    decision_patterns = [
        r'FINAL TRANSACTION PROPOSAL:\s*\*?\*?(\w+)\*?\*?',
        r'最终交易建议[：:]\s*[【\[]?(\w+)[】\]]?',
        r'投资评级[：:]\s*[【\[]?([^\]】\n]+)[】\]]?',
    ]

    for pattern in decision_patterns:
        match = re.search(pattern, report, re.IGNORECASE)
        if match:
            decision_text = match.group(1).strip().upper()
            if 'BUY' in decision_text or '买' in decision_text:
                result["decision"] = "BUY"
            elif 'SELL' in decision_text or '卖' in decision_text:
                result["decision"] = "SELL"
            else:
                result["decision"] = "HOLD"
            break

    # 解析置信度
    confidence_patterns = [
        r'置信度[：:]\s*(\d+(?:\.\d+)?)\s*%?',
        r'Confidence[：:]\s*(\d+(?:\.\d+)?)\s*%?',
        r'确定性[：:]\s*(\d+(?:\.\d+)?)\s*%?',
    ]

    for pattern in confidence_patterns:
        match = re.search(pattern, report, re.IGNORECASE)
        if match:
            conf = float(match.group(1))
            result["confidence"] = conf / 100 if conf > 1 else conf
            break

    # 解析关键理由
    reasons_section = re.search(r'核心投资逻辑.*?(?=##|\Z)', report, re.DOTALL)
    if reasons_section:
        # 提取编号列表项
        reasons = re.findall(r'\d+\)\s*([^\n]+)', reasons_section.group(0))
        result["reasons"] = [r.strip()[:100] for r in reasons[:5]]  # 最多5条，每条最多100字

    return result


def get_price_from_report(report: str) -> Optional[float]:
    """从报告中提取当前价格"""
    patterns = [
        r'当前价格[：:]\s*([\d.]+)',
        r'收盘价[：:]\s*([\d.]+)',
        r'最新价[：:]\s*([\d.]+)',
        r'close[：:]\s*([\d.]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, report, re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None
