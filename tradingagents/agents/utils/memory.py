import chromadb
from openai import OpenAI
import os
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
import json
import logging

# Import DashScope if available
try:
    import dashscope
    from dashscope import TextEmbedding
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False
    dashscope = None
    TextEmbedding = None

logger = logging.getLogger(__name__)


def get_historical_price(ticker: str, date: str) -> Optional[float]:
    """
    获取指定日期的股票收盘价

    Args:
        ticker: 股票代码 (如 "600036")
        date: 日期 (YYYY-MM-DD 格式)

    Returns:
        float: 收盘价，获取失败返回 None
    """
    try:
        from tradingagents.dataflows.tushare_utils import get_pro_api, convert_stock_code

        # 转换日期格式 YYYY-MM-DD -> YYYYMMDD
        date_formatted = date.replace("-", "")

        # 转换股票代码为tushare格式 (如 600036 -> 600036.SH)
        ts_code = convert_stock_code(ticker)

        # 获取 tushare pro api
        pro = get_pro_api()

        # 获取日线数据
        df = pro.daily(ts_code=ts_code, trade_date=date_formatted)

        if df is not None and not df.empty:
            return float(df.iloc[0]['close'])

        return None
    except Exception as e:
        logger.warning(f"获取 {ticker} 在 {date} 的历史价格失败: {e}")
        return None


def _is_valid_api_key(key: Optional[str]) -> bool:
    """Check if an API key is valid (not empty and not a placeholder)"""
    if not key:
        return False
    # Common placeholder patterns
    placeholders = [
        "your_", "your-", "xxx", "placeholder", "api_key_here",
        "sk-xxx", "sk-your", "replace_", "insert_", "enter_"
    ]
    key_lower = key.lower()
    for p in placeholders:
        if p in key_lower:
            return False
    # Check minimum length (real API keys are typically 20+ chars)
    if len(key) < 20:
        return False
    return True


class FinancialSituationMemory:
    def __init__(self, name, config):
        self.config = config
        self.llm_provider = config.get("llm_provider", "openai").lower()
        self._disabled = False  # Memory 功能是否被禁用

        # Configure embedding model and client based on LLM provider
        if (self.llm_provider == "dashscope" or
            "dashscope" in self.llm_provider or
            "alibaba" in self.llm_provider):

            # Check if DashScope is available and configured
            dashscope_key = os.getenv('DASHSCOPE_API_KEY')
            openai_key = os.getenv('OPENAI_API_KEY')

            if DASHSCOPE_AVAILABLE and _is_valid_api_key(dashscope_key):
                # Use DashScope embeddings
                self.embedding = "text-embedding-v3"
                self.client = None  # DashScope doesn't need OpenAI client
                dashscope.api_key = dashscope_key
                print("✅ Using DashScope embeddings")
            elif _is_valid_api_key(openai_key):
                # Fallback to OpenAI embeddings - use OpenAI native URL, not DashScope URL
                logger.info("DashScope not available or not configured, falling back to OpenAI embeddings")
                self.embedding = "text-embedding-3-small"
                self.client = OpenAI(base_url="https://api.openai.com/v1")
            else:
                # No valid API keys available
                raise ValueError(
                    "No valid API keys found. For DashScope provider, please set either:\n"
                    "1. DASHSCOPE_API_KEY (preferred for DashScope embeddings)\n"
                    "2. OPENAI_API_KEY (fallback for OpenAI embeddings)\n"
                    f"Current DASHSCOPE_API_KEY: {'[placeholder]' if dashscope_key else '[not set]'}\n"
                    f"Current OPENAI_API_KEY: {'[placeholder]' if openai_key else '[not set]'}\n"
                    "Install dashscope package: pip install dashscope"
                )
        elif self.llm_provider == "google":
            # Google AI uses DashScope embedding if available, otherwise OpenAI
            dashscope_key = os.getenv('DASHSCOPE_API_KEY')
            openai_key = os.getenv('OPENAI_API_KEY')

            if _is_valid_api_key(dashscope_key) and DASHSCOPE_AVAILABLE:
                self.embedding = "text-embedding-v3"
                self.client = None
                dashscope.api_key = dashscope_key
                logger.info("Google AI using DashScope embedding service")
            elif _is_valid_api_key(openai_key):
                # Fallback to OpenAI embeddings - use OpenAI native URL
                self.embedding = "text-embedding-3-small"
                self.client = OpenAI(base_url="https://api.openai.com/v1")
                logger.info("Google AI falling back to OpenAI embedding service")
            else:
                raise ValueError(
                    "No valid API keys found for Google AI embeddings. Please set either:\n"
                    "1. DASHSCOPE_API_KEY (preferred)\n"
                    "2. OPENAI_API_KEY (fallback)\n"
                    f"Current DASHSCOPE_API_KEY: {'[placeholder]' if dashscope_key else '[not set]'}\n"
                    f"Current OPENAI_API_KEY: {'[placeholder]' if openai_key else '[not set]'}"
                )
        elif config.get("backend_url") and "deepseek" in config.get("backend_url", "").lower():
            # DeepSeek 不支持 Embeddings API，需要使用其他服务
            dashscope_key = os.getenv('DASHSCOPE_API_KEY')
            openai_embedding_key = os.getenv('OPENAI_EMBEDDING_API_KEY')  # 独立的 OpenAI Embedding Key

            if DASHSCOPE_AVAILABLE and _is_valid_api_key(dashscope_key):
                # 使用 DashScope Embeddings（国内可访问）
                self.embedding = "text-embedding-v3"
                self.client = None
                dashscope.api_key = dashscope_key
                logger.info("DeepSeek 模式: 使用 DashScope embedding 服务")
            elif _is_valid_api_key(openai_embedding_key):
                # 使用独立的 OpenAI Embedding Key
                self.embedding = "text-embedding-3-small"
                self.client = OpenAI(api_key=openai_embedding_key)
                logger.info("DeepSeek 模式: 使用独立 OpenAI embedding 服务")
            else:
                # 禁用 Memory 功能，使用空操作
                logger.warning(
                    "DeepSeek 不支持 Embeddings API，Memory 功能已禁用。\n"
                    "建议配置以下任一环境变量以启用 Memory 功能：\n"
                    "1. DASHSCOPE_API_KEY（推荐，国内可访问）\n"
                    "2. OPENAI_EMBEDDING_API_KEY（需要能访问 OpenAI）"
                )
                self.embedding = None
                self.client = None
                self._disabled = True
        elif config.get("backend_url") == "http://localhost:11434/v1":
            self.embedding = "nomic-embed-text"
            self.client = OpenAI(base_url=config["backend_url"])
        else:
            self.embedding = "text-embedding-3-small"
            self.client = OpenAI(base_url=config["backend_url"])

        # 如果 Memory 功能被禁用，跳过 ChromaDB 初始化
        if self._disabled:
            self.chroma_client = None
            self.situation_collection = None
            logger.info("Memory 功能已禁用，跳过 ChromaDB 初始化")
            return

        # 配置持久化存储路径
        chroma_path = config.get(
            "chroma_db_path",
            os.path.join(os.path.expanduser("~"), "Documents", "TradingAgents", "chroma_db")
        )

        # 初始化 ChromaDB
        try:
            # 确保目录存在
            os.makedirs(chroma_path, exist_ok=True)

            # 使用持久化客户端（数据会保存到磁盘，程序重启后不丢失）
            self.chroma_client = chromadb.PersistentClient(path=chroma_path)

            # 获取或创建集合
            self.situation_collection = self.chroma_client.get_or_create_collection(name=name)
        except PermissionError as e:
            logger.error(f"ChromaDB 初始化失败：无权限访问目录 {chroma_path}: {e}")
            raise ValueError(f"无法初始化 Memory 系统：权限不足。请检查目录权限: {chroma_path}")
        except Exception as e:
            logger.error(f"ChromaDB 初始化失败: {e}")
            raise ValueError(f"Memory 系统初始化失败: {e}")

    def _safe_json_dumps(self, obj: Any) -> str:
        """安全的 JSON 序列化，处理不可序列化的对象"""
        if obj is None:
            return "{}"
        try:
            return json.dumps(obj, default=str, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            logger.warning(f"JSON 序列化失败: {e}，使用空字典")
            return "{}"

    def get_embedding(self, text):
        """Get embedding for a text using the configured provider

        对于超长文本，使用分块嵌入后取平均的方式处理
        """
        # 如果 Memory 功能被禁用，返回空列表
        if self._disabled:
            return []

        # text-embedding-3-small 限制 8191 tokens
        # 保守估计：中文 1字符 ≈ 2 tokens
        # 设置每块最大字符数为 2500（约 5000 tokens，留安全余量）
        MAX_CHARS_PER_CHUNK = 2500

        if len(text) > MAX_CHARS_PER_CHUNK:
            # 分块处理
            chunks = []
            for i in range(0, len(text), MAX_CHARS_PER_CHUNK):
                chunk = text[i:i + MAX_CHARS_PER_CHUNK]
                chunks.append(chunk)

            # 获取每个块的嵌入
            embeddings = []
            for chunk in chunks:
                emb = self._get_single_embedding(chunk)
                embeddings.append(emb)

            # 计算平均嵌入
            import numpy as np
            avg_embedding = np.mean(embeddings, axis=0).tolist()
            return avg_embedding
        else:
            return self._get_single_embedding(text)

    def _get_single_embedding(self, text):
        """获取单个文本块的嵌入"""
        if ((self.llm_provider == "dashscope" or
             "dashscope" in self.llm_provider or
             "alibaba" in self.llm_provider or
             (self.llm_provider == "google" and self.client is None)) and
            DASHSCOPE_AVAILABLE and self.client is None):
            # Use DashScope embedding model
            try:
                response = TextEmbedding.call(
                    model=self.embedding,
                    input=text
                )
                if response.status_code == 200:
                    return response.output['embeddings'][0]['embedding']
                else:
                    raise Exception(f"DashScope embedding error: {response.code} - {response.message}")
            except Exception as e:
                raise Exception(f"Error getting DashScope embedding: {str(e)}")
        else:
            # Use OpenAI-compatible embedding model
            response = self.client.embeddings.create(
                model=self.embedding, input=text
            )
            return response.data[0].embedding

    def add_situations(self, situations_and_advice):
        """Add financial situations and their corresponding advice. Parameter is a list of tuples (situation, rec)"""
        # 如果 Memory 功能被禁用，直接返回
        if self._disabled:
            logger.debug("Memory 功能已禁用，跳过 add_situations")
            return

        situations = []
        advice = []
        ids = []
        embeddings = []

        offset = self.situation_collection.count()

        for i, (situation, recommendation) in enumerate(situations_and_advice):
            situations.append(situation)
            advice.append(recommendation)
            ids.append(str(offset + i))
            embeddings.append(self.get_embedding(situation))

        self.situation_collection.add(
            documents=situations,
            metadatas=[{"recommendation": rec} for rec in advice],
            embeddings=embeddings,
            ids=ids,
        )

    def add_decision_with_context(
        self,
        situation: str,
        recommendation: str,
        ticker: str,
        decision_date: str,
        decision_type: str = "BUY",
        confidence: float = 0.5,
        extra_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        添加带有完整上下文的决策记录

        如果同一天同一股票已有记录，则更新而不是创建新记录（避免冗余）

        Args:
            situation: 市场情况描述
            recommendation: 推荐的行动
            ticker: 股票代码
            decision_date: 决策日期 (YYYY-MM-DD)
            decision_type: 决策类型 (BUY/SELL/HOLD)
            confidence: 置信度 (0.0-1.0)
            extra_context: 额外上下文信息

        Returns:
            str: 记录ID，用于后续更新outcome
        """
        # 如果 Memory 功能被禁用，返回占位 ID
        if self._disabled:
            logger.debug("Memory 功能已禁用，跳过 add_decision_with_context")
            return f"{ticker}_{decision_date}_disabled"

        # 检查当天是否已有该股票的记录
        existing_id = self._find_existing_record(ticker, decision_date)

        if existing_id:
            # 更新现有记录
            record_id = existing_id
            logger.info(f"发现当日已有记录 {record_id}，将更新而非创建新记录")
        else:
            # 创建新记录ID
            offset = self.situation_collection.count()
            record_id = f"{ticker}_{decision_date}_{offset}"

        # Build metadata - ChromaDB doesn't accept None values
        metadata = {
            "recommendation": recommendation,
            "ticker": ticker,
            "decision_date": decision_date,
            "decision_type": decision_type,
            "confidence": confidence,
            "created_at": datetime.now().isoformat(),
            # Outcome fields - use empty string/0 as placeholder (to be updated later)
            "outcome_updated": False,
            "actual_return": 0.0,  # Will be updated with actual return
            "outcome_category": "",  # "profit", "loss", "breakeven"
            "days_held": 0,  # Will be updated with actual days held
            "extra_context": self._safe_json_dumps(extra_context)
        }

        embedding = self.get_embedding(situation)

        if existing_id:
            # 更新现有记录
            self.situation_collection.update(
                ids=[record_id],
                documents=[situation],
                metadatas=[metadata],
                embeddings=[embedding],
            )
            logger.info(f"Updated decision record: {record_id}")
        else:
            # 添加新记录
            self.situation_collection.add(
                documents=[situation],
                metadatas=[metadata],
                embeddings=[embedding],
                ids=[record_id],
            )
            logger.info(f"Added decision record: {record_id}")

        return record_id

    def _find_existing_record(self, ticker: str, decision_date: str) -> Optional[str]:
        """
        查找当天是否已有该股票的决策记录

        Args:
            ticker: 股票代码
            decision_date: 决策日期

        Returns:
            str or None: 如果存在返回记录ID，否则返回None
        """
        if self._disabled:
            return None

        try:
            # 获取所有记录的metadata
            all_records = self.situation_collection.get(include=["metadatas"])

            if not all_records["ids"]:
                return None

            # 查找匹配的记录
            for i, metadata in enumerate(all_records["metadatas"]):
                if (metadata.get("ticker") == ticker and
                    metadata.get("decision_date") == decision_date):
                    return all_records["ids"][i]

            return None
        except Exception as e:
            logger.warning(f"查找现有记录时出错: {e}")
            return None

    def update_outcome(
        self,
        record_id: str,
        actual_return: float,
        days_held: int,
        exit_date: Optional[str] = None,
        exit_reason: Optional[str] = None
    ) -> bool:
        """
        更新决策的实际结果

        Args:
            record_id: 记录ID
            actual_return: 实际收益率 (-100% 到 +∞)
            days_held: 持仓天数
            exit_date: 退出日期 (可选)
            exit_reason: 退出原因 (可选)

        Returns:
            bool: 是否更新成功
        """
        if self._disabled:
            logger.debug("Memory 功能已禁用，跳过 update_outcome")
            return False

        try:
            # Get existing record
            result = self.situation_collection.get(
                ids=[record_id],
                include=["metadatas", "documents", "embeddings"]
            )

            if not result["ids"]:
                logger.warning(f"Record not found: {record_id}")
                return False

            # Determine outcome category
            if actual_return > 0.5:  # > 0.5%
                outcome_category = "profit"
            elif actual_return < -0.5:  # < -0.5%
                outcome_category = "loss"
            else:
                outcome_category = "breakeven"

            # Update metadata
            metadata = result["metadatas"][0]
            metadata["outcome_updated"] = True
            metadata["actual_return"] = actual_return
            metadata["outcome_category"] = outcome_category
            metadata["days_held"] = days_held
            metadata["outcome_updated_at"] = datetime.now().isoformat()
            if exit_date:
                metadata["exit_date"] = exit_date
            if exit_reason:
                metadata["exit_reason"] = exit_reason

            # Update the record
            self.situation_collection.update(
                ids=[record_id],
                metadatas=[metadata]
            )

            logger.info(
                f"Updated outcome for {record_id}: "
                f"return={actual_return:.2f}%, category={outcome_category}"
            )
            return True

        except Exception as e:
            logger.error(f"Error updating outcome for {record_id}: {e}")
            return False

    def get_memories_by_outcome(
        self,
        current_situation: str,
        outcome_filter: Optional[str] = None,
        n_matches: int = 3
    ) -> List[Dict[str, Any]]:
        """
        根据outcome过滤获取相似情况的记忆

        Args:
            current_situation: 当前市场情况
            outcome_filter: 结果过滤器 ("profit", "loss", "breakeven", None=all)
            n_matches: 返回匹配数量

        Returns:
            List[Dict]: 匹配的记忆列表
        """
        # 如果 Memory 功能被禁用，返回空列表
        if self._disabled:
            return []

        query_embedding = self.get_embedding(current_situation)

        # Build where clause for filtering
        where_clause = None
        if outcome_filter:
            where_clause = {"outcome_category": outcome_filter}

        try:
            results = self.situation_collection.query(
                query_embeddings=[query_embedding],
                n_results=n_matches * 3,  # Get more, then filter
                include=["metadatas", "documents", "distances"],
                where=where_clause
            )
        except Exception:
            # Fallback without filter if ChromaDB doesn't support this where clause
            results = self.situation_collection.query(
                query_embeddings=[query_embedding],
                n_results=n_matches * 3,
                include=["metadatas", "documents", "distances"]
            )

        matched_results = []
        for i in range(len(results["documents"][0])):
            metadata = results["metadatas"][0][i]

            # Apply filter manually if needed
            if outcome_filter and metadata.get("outcome_category") != outcome_filter:
                continue

            matched_results.append({
                "matched_situation": results["documents"][0][i],
                "recommendation": metadata.get("recommendation"),
                "similarity_score": 1 - results["distances"][0][i],
                "ticker": metadata.get("ticker"),
                "decision_date": metadata.get("decision_date"),
                "decision_type": metadata.get("decision_type"),
                "confidence": metadata.get("confidence"),
                "outcome_updated": metadata.get("outcome_updated", False),
                "actual_return": metadata.get("actual_return"),
                "outcome_category": metadata.get("outcome_category"),
                "days_held": metadata.get("days_held"),
            })

            if len(matched_results) >= n_matches:
                break

        return matched_results

    def get_performance_stats(
        self,
        ticker: Optional[str] = None,
        decision_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取决策性能统计

        Args:
            ticker: 可选，按股票代码过滤
            decision_type: 可选，按决策类型过滤 (BUY/SELL/HOLD)

        Returns:
            Dict: 性能统计信息
        """
        if self._disabled:
            return {"total_decisions": 0, "message": "Memory 功能已禁用"}

        try:
            # Get all records with outcomes
            all_records = self.situation_collection.get(
                include=["metadatas"]
            )

            if not all_records["ids"]:
                return {"total_decisions": 0, "message": "No records found"}

            # Filter and analyze
            stats = {
                "total_decisions": 0,
                "decisions_with_outcome": 0,
                "profit_count": 0,
                "loss_count": 0,
                "breakeven_count": 0,
                "total_return": 0.0,
                "avg_return": 0.0,
                "win_rate": 0.0,
                "avg_days_held": 0.0,
                "best_return": None,
                "worst_return": None,
            }

            returns = []
            days_held_list = []

            for metadata in all_records["metadatas"]:
                # Apply filters
                if ticker and metadata.get("ticker") != ticker:
                    continue
                if decision_type and metadata.get("decision_type") != decision_type:
                    continue

                stats["total_decisions"] += 1

                if metadata.get("outcome_updated"):
                    stats["decisions_with_outcome"] += 1
                    actual_return = metadata.get("actual_return", 0)
                    returns.append(actual_return)

                    if metadata.get("days_held"):
                        days_held_list.append(metadata["days_held"])

                    category = metadata.get("outcome_category")
                    if category == "profit":
                        stats["profit_count"] += 1
                    elif category == "loss":
                        stats["loss_count"] += 1
                    else:
                        stats["breakeven_count"] += 1

            # Calculate aggregates
            if returns:
                stats["total_return"] = sum(returns)
                stats["avg_return"] = stats["total_return"] / len(returns)
                stats["best_return"] = max(returns)
                stats["worst_return"] = min(returns)
                stats["win_rate"] = (
                    stats["profit_count"] / stats["decisions_with_outcome"] * 100
                    if stats["decisions_with_outcome"] > 0 else 0
                )

            if days_held_list:
                stats["avg_days_held"] = sum(days_held_list) / len(days_held_list)

            return stats

        except Exception as e:
            logger.error(f"Error getting performance stats: {e}")
            return {"error": str(e)}

    def get_lessons_learned(
        self,
        current_situation: str,
        n_successes: int = 2,
        n_failures: int = 2
    ) -> Dict[str, List[Dict]]:
        """
        获取从成功和失败中学到的经验教训

        这个方法会同时返回相似情况下的成功案例和失败案例，
        帮助Agent做出更明智的决策。

        Args:
            current_situation: 当前市场情况
            n_successes: 返回的成功案例数量
            n_failures: 返回的失败案例数量

        Returns:
            Dict: 包含 "successes" 和 "failures" 两个列表
        """
        return {
            "successes": self.get_memories_by_outcome(
                current_situation,
                outcome_filter="profit",
                n_matches=n_successes
            ),
            "failures": self.get_memories_by_outcome(
                current_situation,
                outcome_filter="loss",
                n_matches=n_failures
            )
        }

    def health_check(self) -> Dict[str, Any]:
        """
        执行Memory系统健康检查

        检查项目：
        1. ChromaDB连接状态
        2. 集合是否存在且可访问
        3. Embedding服务是否可用
        4. 存储空间使用情况

        Returns:
            Dict: 健康检查结果
        """
        health = {
            "status": "healthy",
            "checks": {},
            "warnings": [],
            "errors": []
        }

        # 如果 Memory 功能被禁用，返回禁用状态
        if self._disabled:
            health["status"] = "disabled"
            health["checks"]["memory_disabled"] = {
                "status": "disabled",
                "reason": "DeepSeek 不支持 Embeddings API，Memory 功能已禁用"
            }
            health["warnings"].append(
                "Memory 功能已禁用。建议配置 DASHSCOPE_API_KEY 或 OPENAI_EMBEDDING_API_KEY"
            )
            return health

        # 1. 检查ChromaDB连接
        try:
            collections = self.chroma_client.list_collections()
            health["checks"]["chromadb_connection"] = {
                "status": "ok",
                "collections_count": len(collections)
            }
        except Exception as e:
            health["checks"]["chromadb_connection"] = {
                "status": "error",
                "error": str(e)
            }
            health["errors"].append(f"ChromaDB连接失败: {e}")
            health["status"] = "unhealthy"

        # 2. 检查集合状态
        try:
            count = self.situation_collection.count()
            health["checks"]["collection"] = {
                "status": "ok",
                "record_count": count
            }
            if count == 0:
                health["warnings"].append("集合为空，尚无历史记录")
            elif count > 10000:
                health["warnings"].append(f"集合记录数较多({count})，可能影响查询性能")
        except Exception as e:
            health["checks"]["collection"] = {
                "status": "error",
                "error": str(e)
            }
            health["errors"].append(f"集合访问失败: {e}")
            health["status"] = "unhealthy"

        # 3. 检查Embedding服务
        try:
            test_embedding = self.get_embedding("健康检查测试文本")
            if test_embedding and len(test_embedding) > 0:
                health["checks"]["embedding_service"] = {
                    "status": "ok",
                    "embedding_dim": len(test_embedding),
                    "provider": self.llm_provider
                }
            else:
                raise ValueError("Embedding返回为空")
        except Exception as e:
            health["checks"]["embedding_service"] = {
                "status": "error",
                "error": str(e)
            }
            health["errors"].append(f"Embedding服务不可用: {e}")
            health["status"] = "unhealthy"

        # 4. 检查存储路径
        chroma_path = self.config.get(
            "chroma_db_path",
            os.path.join(os.path.expanduser("~"), "Documents", "TradingAgents", "chroma_db")
        )
        try:
            if os.path.exists(chroma_path):
                # 计算目录大小
                total_size = 0
                for dirpath, dirnames, filenames in os.walk(chroma_path):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        total_size += os.path.getsize(fp)

                size_mb = total_size / (1024 * 1024)
                health["checks"]["storage"] = {
                    "status": "ok",
                    "path": chroma_path,
                    "size_mb": round(size_mb, 2)
                }
                if size_mb > 500:
                    health["warnings"].append(f"存储空间使用较大({size_mb:.0f}MB)，考虑清理旧数据")
            else:
                health["checks"]["storage"] = {
                    "status": "warning",
                    "message": "存储路径不存在，将在首次写入时创建"
                }
        except Exception as e:
            health["checks"]["storage"] = {
                "status": "error",
                "error": str(e)
            }

        # 汇总状态
        if health["errors"]:
            health["status"] = "unhealthy"
        elif health["warnings"]:
            health["status"] = "degraded"

        return health

    def cleanup_old_records(
        self,
        max_age_days: int = 365,
        keep_min_records: int = 100
    ) -> Dict[str, int]:
        """
        清理过期的历史记录

        Args:
            max_age_days: 保留的最大天数
            keep_min_records: 至少保留的记录数

        Returns:
            Dict: 清理结果统计
        """
        if self._disabled:
            return {"total_before": 0, "deleted": 0, "total_after": 0, "message": "Memory 功能已禁用"}

        from datetime import timedelta

        result = {
            "total_before": 0,
            "deleted": 0,
            "total_after": 0
        }

        try:
            all_records = self.situation_collection.get(include=["metadatas"])
            result["total_before"] = len(all_records["ids"])

            if result["total_before"] <= keep_min_records:
                logger.info(f"记录数({result['total_before']})未超过最小保留数({keep_min_records})，跳过清理")
                result["total_after"] = result["total_before"]
                return result

            cutoff_date = datetime.now() - timedelta(days=max_age_days)
            ids_to_delete = []

            for i, metadata in enumerate(all_records["metadatas"]):
                created_at = metadata.get("created_at")
                if created_at:
                    try:
                        record_date = datetime.fromisoformat(created_at)
                        if record_date < cutoff_date:
                            ids_to_delete.append(all_records["ids"][i])
                    except (ValueError, TypeError):
                        pass

            # 确保不删除太多
            max_deletable = result["total_before"] - keep_min_records
            if len(ids_to_delete) > max_deletable:
                ids_to_delete = ids_to_delete[:max_deletable]

            if ids_to_delete:
                self.situation_collection.delete(ids=ids_to_delete)
                result["deleted"] = len(ids_to_delete)
                logger.info(f"清理了{len(ids_to_delete)}条过期记录")

            result["total_after"] = result["total_before"] - result["deleted"]

        except Exception as e:
            logger.error(f"清理记录时出错: {e}")
            result["error"] = str(e)

        return result

    def get_memories(self, current_situation, n_matches=1, exclude_date: Optional[str] = None):
        """Find matching recommendations using embeddings

        Args:
            current_situation: 当前市场情况描述
            n_matches: 返回的匹配数量
            exclude_date: 排除的日期（YYYY-MM-DD格式），用于排除当天的记录

        Returns:
            List[Dict]: 匹配结果列表，每个结果包含：
                - matched_situation: 匹配的市场情况
                - recommendation: 当时的建议
                - similarity_score: 相似度分数 (0-1)
                - decision_type: 决策类型 (BUY/SELL/HOLD等)
                - decision_date: 决策日期
                - ticker: 股票代码
                - confidence: 置信度
                - actual_return: 实际收益 (如果有)
                - outcome_category: 结果分类 (profit/loss/breakeven)
        """
        # 如果 Memory 功能被禁用，返回空列表
        if self._disabled:
            return []

        # 边界检查：如果集合为空，直接返回空列表
        if self.situation_collection.count() == 0:
            return []

        query_embedding = self.get_embedding(current_situation)

        # 如果需要排除某个日期，多获取一些结果以便过滤后仍有足够数量
        fetch_count = n_matches * 3 if exclude_date else n_matches

        results = self.situation_collection.query(
            query_embeddings=[query_embedding],
            n_results=fetch_count,
            include=["metadatas", "documents", "distances"],
        )

        # 边界检查：确保结果不为空
        if not results or not results.get("documents") or not results["documents"][0]:
            return []

        # 验证返回数据的一致性
        docs = results["documents"][0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        if len(docs) != len(metadatas) or len(docs) != len(distances):
            logger.warning(f"ChromaDB 返回数据长度不一致: docs={len(docs)}, metadatas={len(metadatas)}, distances={len(distances)}")
            # 使用最小长度，避免 IndexError
            min_len = min(len(docs), len(metadatas), len(distances))
        else:
            min_len = len(docs)

        matched_results = []
        for i in range(min_len):
            metadata = results["metadatas"][0][i]

            # 如果指定了排除日期，跳过该日期的记录
            if exclude_date and metadata.get("decision_date") == exclude_date:
                continue

            matched_results.append(
                {
                    "matched_situation": results["documents"][0][i],
                    "recommendation": metadata.get("recommendation", ""),
                    "similarity_score": 1 - results["distances"][0][i],
                    # 额外的决策上下文信息
                    "decision_type": metadata.get("decision_type", "未知"),
                    "decision_date": metadata.get("decision_date", "未知日期"),
                    "ticker": metadata.get("ticker", ""),
                    "confidence": metadata.get("confidence", 0.5),
                    "actual_return": metadata.get("actual_return"),
                    "outcome_category": metadata.get("outcome_category"),
                    "outcome_updated": metadata.get("outcome_updated", False),
                }
            )

            # 已获取足够数量，停止
            if len(matched_results) >= n_matches:
                break

        return matched_results


if __name__ == "__main__":
    # Example usage with outcome tracking
    from tradingagents.default_config import DEFAULT_CONFIG

    print("=== Memory System with Outcome Tracking Demo ===\n")

    # Initialize memory
    matcher = FinancialSituationMemory("demo_memory", DEFAULT_CONFIG)

    # Example 1: Add a decision with full context
    print("1. Adding a decision with context...")
    record_id = matcher.add_decision_with_context(
        situation="A股市场震荡，北向资金连续流入，主力资金净流入，融资余额上升",
        recommendation="建议买入，趋势向好",
        ticker="600036",
        decision_date="2024-01-15",
        decision_type="BUY",
        confidence=0.75,
        extra_context={"analyst": "bull_researcher", "market_regime": "震荡市"}
    )
    print(f"   Created record: {record_id}")

    # Example 2: Update outcome after the trade
    print("\n2. Updating outcome after trade...")
    success = matcher.update_outcome(
        record_id=record_id,
        actual_return=5.2,  # 5.2% profit
        days_held=10,
        exit_date="2024-01-25",
        exit_reason="达到目标价"
    )
    print(f"   Outcome updated: {success}")

    # Example 3: Query memories filtered by outcome
    print("\n3. Querying successful similar situations...")
    current_situation = "市场震荡偏强，北向资金持续流入，板块轮动活跃"

    lessons = matcher.get_lessons_learned(
        current_situation,
        n_successes=2,
        n_failures=2
    )

    print(f"   Found {len(lessons['successes'])} successful cases")
    print(f"   Found {len(lessons['failures'])} failed cases")

    for case in lessons['successes']:
        print(f"\n   Success case:")
        print(f"   - Ticker: {case.get('ticker')}")
        print(f"   - Return: {case.get('actual_return')}%")
        print(f"   - Recommendation: {case.get('recommendation')}")

    # Example 4: Get performance statistics
    print("\n4. Getting performance statistics...")
    stats = matcher.get_performance_stats()
    print(f"   Total decisions: {stats.get('total_decisions', 0)}")
    print(f"   Decisions with outcome: {stats.get('decisions_with_outcome', 0)}")
    print(f"   Win rate: {stats.get('win_rate', 0):.1f}%")
    print(f"   Average return: {stats.get('avg_return', 0):.2f}%")

    print("\n=== Demo Complete ===")
