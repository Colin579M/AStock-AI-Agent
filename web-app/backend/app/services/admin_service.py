"""
管理员服务

提供用户管理、系统监控、内容管理等管理功能。
"""
import os
import json
import psutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class AdminLog:
    """管理员操作日志"""
    id: str
    timestamp: str
    admin_id: str
    action: str
    target_user_id: Optional[str] = None
    details: Dict = field(default_factory=dict)
    ip_address: str = ""


@dataclass
class SystemStatus:
    """系统状态"""
    backend_status: str  # healthy / degraded / unhealthy
    chatbot_status: str  # ready / loading / error
    memory_usage_mb: float
    memory_percent: float
    cpu_percent: float
    active_tasks: int
    uptime_seconds: float


@dataclass
class ApiStats:
    """API 统计"""
    date: str
    total_requests: int
    by_endpoint: Dict[str, int]
    by_user: Dict[str, int]
    errors: Dict[str, int]


class AdminService:
    """管理员服务"""

    def __init__(self):
        """初始化管理员服务"""
        self.config_dir = Path(__file__).parent.parent.parent / "config"
        self.results_dir = Path(__file__).parent.parent.parent.parent / "results"
        self.logs_file = self.config_dir / "admin_logs.json"
        self.stats_file = self.config_dir / "api_stats.json"

        # 确保配置目录存在
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # 初始化日志和统计文件
        self._init_logs_file()
        self._init_stats_file()

        # 启动时间
        self._start_time = datetime.now()

        # CPU 监控缓存（避免短间隔采样不准确）
        self._cpu_percent_cache = 0.0
        self._cpu_last_update = datetime.now()
        self._process = psutil.Process()
        # 初始化 CPU 采样（首次调用返回0，需要预热）
        try:
            self._process.cpu_percent()
        except Exception:
            pass

    def _init_logs_file(self):
        """初始化日志文件"""
        if not self.logs_file.exists():
            with open(self.logs_file, 'w', encoding='utf-8') as f:
                json.dump({"version": "1.0", "logs": []}, f, ensure_ascii=False, indent=2)

    def _init_stats_file(self):
        """初始化统计文件"""
        if not self.stats_file.exists():
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "version": "1.0",
                    "daily_stats": {},
                    "current_hour": {"requests": 0, "active_users": []}
                }, f, ensure_ascii=False, indent=2)

    # ==================== 系统监控 ====================

    def get_system_status(self, analysis_service=None, chat_service=None) -> SystemStatus:
        """
        获取系统状态

        Args:
            analysis_service: 分析服务实例（可选）
            chat_service: 聊天服务实例（可选）
        """
        # 内存使用
        memory_info = self._process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        memory_percent = self._process.memory_percent()

        # CPU 使用（进程级别，更新缓存以获得准确值）
        # psutil 的 cpu_percent() 需要两次调用之间的时间差来计算
        # 这里直接获取进程 CPU（非阻塞），依赖上次调用的时间差
        try:
            cpu_percent = self._process.cpu_percent()
            # 如果值为0且距离上次更新不到1秒，使用缓存值
            now = datetime.now()
            if cpu_percent > 0:
                self._cpu_percent_cache = cpu_percent
                self._cpu_last_update = now
            elif (now - self._cpu_last_update).total_seconds() < 5:
                cpu_percent = self._cpu_percent_cache
        except Exception:
            cpu_percent = self._cpu_percent_cache

        # 活跃任务数
        active_tasks = 0
        if analysis_service:
            active_tasks = len([t for t in analysis_service._tasks.values()
                              if t.status.value in ("pending", "running")])

        # Chatbot 状态
        chatbot_status = "ready"
        if chat_service:
            try:
                if chat_service._chatbot is None:
                    chatbot_status = "not_loaded"
                else:
                    chatbot_status = "ready"
            except Exception:
                chatbot_status = "error"

        # 运行时间
        uptime = (datetime.now() - self._start_time).total_seconds()

        return SystemStatus(
            backend_status="healthy",
            chatbot_status=chatbot_status,
            memory_usage_mb=round(memory_mb, 2),
            memory_percent=round(memory_percent, 2),
            cpu_percent=round(cpu_percent, 2),
            active_tasks=active_tasks,
            uptime_seconds=round(uptime, 2)
        )

    def get_api_stats(self, date: Optional[str] = None) -> ApiStats:
        """获取 API 统计"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        try:
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            daily = data.get("daily_stats", {}).get(date, {})
            return ApiStats(
                date=date,
                total_requests=daily.get("total_requests", 0),
                by_endpoint=daily.get("by_endpoint", {}),
                by_user=daily.get("by_user", {}),
                errors=daily.get("errors", {})
            )
        except Exception as e:
            logger.error(f"读取 API 统计失败: {e}")
            return ApiStats(date=date, total_requests=0, by_endpoint={}, by_user={}, errors={})

    def record_api_call(self, endpoint: str, user_id: str, status_code: int):
        """记录 API 调用"""
        try:
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            date = datetime.now().strftime("%Y-%m-%d")
            if date not in data["daily_stats"]:
                data["daily_stats"][date] = {
                    "total_requests": 0,
                    "by_endpoint": {},
                    "by_user": {},
                    "errors": {}
                }

            daily = data["daily_stats"][date]
            daily["total_requests"] += 1
            daily["by_endpoint"][endpoint] = daily["by_endpoint"].get(endpoint, 0) + 1
            daily["by_user"][user_id] = daily["by_user"].get(user_id, 0) + 1

            if status_code >= 400:
                error_key = str(status_code)
                daily["errors"][error_key] = daily["errors"].get(error_key, 0) + 1

            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"记录 API 调用失败: {e}")

    # ==================== 内容管理 ====================

    def list_all_reports(self, user_id: Optional[str] = None) -> List[Dict]:
        """
        列出所有分析报告

        Args:
            user_id: 按用户筛选（可选）
        """
        reports = []

        if not self.results_dir.exists():
            return reports

        # 遍历 results/{ticker}/{date}/
        for ticker_dir in self.results_dir.iterdir():
            if not ticker_dir.is_dir():
                continue

            ticker = ticker_dir.name

            for date_dir in ticker_dir.iterdir():
                if not date_dir.is_dir():
                    continue

                date = date_dir.name

                # 检查是否有报告文件
                reports_dir = date_dir / "reports"
                if reports_dir.exists():
                    report_files = list(reports_dir.glob("*.md"))

                    # 获取综合报告
                    final_report = reports_dir / "final_report.md"
                    summary = ""
                    if final_report.exists():
                        try:
                            content = final_report.read_text(encoding='utf-8')
                            # 提取前200字符作为摘要
                            summary = content[:200] + "..." if len(content) > 200 else content
                        except Exception:
                            pass

                    # 读取分析摘要（包含用户和时间信息）
                    ticker_name = ""
                    user_id = ""
                    created_at = ""
                    completed_at = ""
                    summary_file = date_dir / "analysis_summary.json"
                    if summary_file.exists():
                        try:
                            with open(summary_file, 'r', encoding='utf-8') as f:
                                summary_data = json.load(f)
                                ticker_name = summary_data.get("ticker_name", "")
                                user_id = summary_data.get("user_id", "")
                                created_at = summary_data.get("created_at", "")
                                completed_at = summary_data.get("completed_at", "")
                        except Exception:
                            pass

                    reports.append({
                        "ticker": ticker,
                        "ticker_name": ticker_name,
                        "date": date,
                        "report_count": len(report_files),
                        "summary": summary,
                        "path": str(date_dir),
                        "user_id": user_id,
                        "created_at": created_at,
                        "completed_at": completed_at
                    })

        # 按日期降序排序
        reports.sort(key=lambda x: x["date"], reverse=True)
        return reports

    def list_all_conversations(self, chat_service=None) -> List[Dict]:
        """
        列出所有对话记录

        Args:
            chat_service: 聊天服务实例
        """
        conversations = []

        if chat_service is None:
            return conversations

        # 遍历所有用户的对话
        for user_id, user_convs in chat_service._conversations.items():
            for conv_id, conv in user_convs.items():
                conversations.append({
                    "user_id": user_id,
                    "conversation_id": conv_id,
                    "title": conv.get("title", ""),
                    "message_count": len(conv.get("messages", [])),
                    "created_at": conv.get("created_at", ""),
                    "updated_at": conv.get("updated_at", "")
                })

        # 按更新时间降序排序
        conversations.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return conversations

    def delete_report(self, ticker: str, date: str) -> bool:
        """删除分析报告"""
        import shutil

        report_dir = self.results_dir / ticker / date
        if report_dir.exists():
            try:
                shutil.rmtree(report_dir)
                return True
            except Exception as e:
                logger.error(f"删除报告失败: {e}")
                return False
        return False

    def delete_conversation(self, user_id: str, conversation_id: str, chat_service=None) -> bool:
        """删除对话"""
        if chat_service is None:
            return False

        return chat_service.delete_conversation(user_id, conversation_id)

    # ==================== 操作日志 ====================

    def log_admin_action(
        self,
        admin_id: str,
        action: str,
        target_user_id: Optional[str] = None,
        details: Optional[Dict] = None,
        ip_address: str = ""
    ):
        """记录管理员操作"""
        import uuid

        log_entry = AdminLog(
            id=str(uuid.uuid4())[:8],
            timestamp=datetime.utcnow().isoformat() + "Z",
            admin_id=admin_id,
            action=action,
            target_user_id=target_user_id,
            details=details or {},
            ip_address=ip_address
        )

        try:
            with open(self.logs_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            data["logs"].insert(0, asdict(log_entry))

            # 只保留最近1000条日志
            data["logs"] = data["logs"][:1000]

            with open(self.logs_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"记录管理员操作失败: {e}")

    def get_admin_logs(self, limit: int = 100, action: Optional[str] = None) -> List[Dict]:
        """获取管理员操作日志"""
        try:
            with open(self.logs_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            logs = data.get("logs", [])

            if action:
                logs = [log for log in logs if log.get("action") == action]

            return logs[:limit]

        except Exception as e:
            logger.error(f"读取管理员日志失败: {e}")
            return []

    def get_error_logs(self, limit: int = 100) -> List[Dict]:
        """获取错误日志（从 Python logging 或文件）"""
        errors = []

        # 尝试读取应用日志文件
        log_file = self.config_dir.parent / "app.log"
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[-500:]  # 最近500行

                for line in lines:
                    if "ERROR" in line or "CRITICAL" in line:
                        errors.append({
                            "message": line.strip(),
                            "level": "ERROR" if "ERROR" in line else "CRITICAL"
                        })

            except Exception as e:
                logger.error(f"读取错误日志失败: {e}")

        return errors[-limit:]
