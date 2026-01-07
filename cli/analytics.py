"""
CLI Analytics Tracker - 追踪分析执行指标

提供以下功能：
- Agent 执行时间追踪
- Token 使用量统计
- API 成本估算
- 错误追踪
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class AgentMetrics:
    """单个Agent的运行指标"""
    name: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    tool_calls: int = 0
    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    errors: List[str] = field(default_factory=list)

    @property
    def duration(self) -> float:
        """获取执行时长（秒）"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        elif self.start_time:
            return time.time() - self.start_time
        return 0.0

    @property
    def duration_str(self) -> str:
        """格式化执行时长"""
        d = self.duration
        if d < 60:
            return f"{d:.1f}s"
        elif d < 3600:
            return f"{int(d//60)}m {int(d%60)}s"
        return f"{int(d//3600)}h {int((d%3600)//60)}m"


@dataclass
class AnalyticsTracker:
    """CLI分析追踪器 - 追踪整个分析过程的指标"""
    start_time: float = field(default_factory=time.time)
    agents: Dict[str, AgentMetrics] = field(default_factory=dict)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tool_calls: int = 0
    total_llm_calls: int = 0
    errors: List[str] = field(default_factory=list)
    model: str = "gpt-5"

    # 定价配置 (per 1K tokens, USD)
    # 格式: model_name -> (input_price, output_price)
    PRICING: Dict[str, tuple] = field(default_factory=lambda: {
        # OpenAI GPT-5 系列
        "gpt-5": (0.00125, 0.010),
        "gpt-5.1": (0.00125, 0.010),
        "gpt-5.2": (0.00175, 0.014),
        "gpt-5-mini": (0.00025, 0.002),
        "gpt-5-nano": (0.00005, 0.0004),
        # DashScope Qwen 系列
        "qwen-plus": (0.0008, 0.002),
        "qwen-turbo": (0.0003, 0.0006),
        "qwen-max": (0.004, 0.012),
        "qwen-max-longcontext": (0.004, 0.012),
        # Anthropic Claude 系列
        "claude-sonnet-4-0": (0.003, 0.015),
        "claude-opus-4-0": (0.015, 0.075),
        "claude-3-5-sonnet-latest": (0.003, 0.015),
        "claude-3-5-haiku-latest": (0.001, 0.005),
        "claude-3-7-sonnet-latest": (0.003, 0.015),
        # Google Gemini 系列
        "gemini-2.0-flash": (0.0001, 0.0004),
        "gemini-2.0-flash-lite": (0.00005, 0.0002),
        "gemini-2.5-flash-preview-05-20": (0.00015, 0.0006),
        "gemini-2.5-pro-preview-06-05": (0.00125, 0.005),
        # Ollama 本地模型 (免费)
        "llama3.1": (0.0, 0.0),
        "llama3.2": (0.0, 0.0),
        "qwen3": (0.0, 0.0),
    })

    def start_agent(self, agent_name: str):
        """开始追踪一个Agent"""
        self.agents[agent_name] = AgentMetrics(name=agent_name, start_time=time.time())

    def end_agent(self, agent_name: str):
        """结束追踪一个Agent"""
        if agent_name in self.agents:
            self.agents[agent_name].end_time = time.time()

    def add_tokens(self, agent_name: str, input_tokens: int, output_tokens: int):
        """添加Token使用量"""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        if agent_name in self.agents:
            self.agents[agent_name].input_tokens += input_tokens
            self.agents[agent_name].output_tokens += output_tokens

    def add_tool_call(self, agent_name: str = None):
        """记录一次工具调用"""
        self.total_tool_calls += 1
        if agent_name and agent_name in self.agents:
            self.agents[agent_name].tool_calls += 1

    def add_llm_call(self, agent_name: str = None):
        """记录一次LLM调用"""
        self.total_llm_calls += 1
        if agent_name and agent_name in self.agents:
            self.agents[agent_name].llm_calls += 1

    def add_error(self, error: str, agent_name: str = None):
        """记录错误"""
        if agent_name:
            self.errors.append(f"[{agent_name}] {error}")
            if agent_name in self.agents:
                self.agents[agent_name].errors.append(error)
        else:
            self.errors.append(error)

    def set_model(self, model: str):
        """设置使用的模型"""
        self.model = model

    @property
    def elapsed_time(self) -> float:
        """获取总执行时间（秒）"""
        return time.time() - self.start_time

    @property
    def elapsed_str(self) -> str:
        """格式化总执行时间"""
        e = self.elapsed_time
        if e < 60:
            return f"{e:.1f}s"
        elif e < 3600:
            return f"{int(e//60)}m {int(e%60)}s"
        return f"{int(e//3600)}h {int((e%3600)//60)}m"

    @property
    def total_tokens(self) -> int:
        """获取总Token数"""
        return self.total_input_tokens + self.total_output_tokens

    @property
    def estimated_cost(self) -> float:
        """估算API成本 (USD)"""
        if self.model in self.PRICING:
            input_price, output_price = self.PRICING[self.model]
            cost = (self.total_input_tokens / 1000 * input_price +
                   self.total_output_tokens / 1000 * output_price)
            return cost
        return 0.0

    @property
    def cost_str(self) -> str:
        """格式化成本显示"""
        cost = self.estimated_cost
        if cost == 0:
            return "Free"
        elif cost < 0.01:
            return f"${cost:.4f}"
        elif cost < 1:
            return f"${cost:.3f}"
        return f"${cost:.2f}"

    def get_summary(self) -> dict:
        """获取分析摘要"""
        return {
            "elapsed_time": self.elapsed_str,
            "total_tool_calls": self.total_tool_calls,
            "total_llm_calls": self.total_llm_calls,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost": self.cost_str,
            "model": self.model,
            "errors": len(self.errors),
            "agents": {
                name: {
                    "duration": metrics.duration_str,
                    "tool_calls": metrics.tool_calls,
                    "llm_calls": metrics.llm_calls,
                    "tokens": metrics.input_tokens + metrics.output_tokens,
                    "errors": len(metrics.errors),
                }
                for name, metrics in self.agents.items()
                if metrics.end_time  # 只返回已完成的Agent
            }
        }

    def reset(self):
        """重置追踪器"""
        self.start_time = time.time()
        self.agents.clear()
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_tool_calls = 0
        self.total_llm_calls = 0
        self.errors.clear()
