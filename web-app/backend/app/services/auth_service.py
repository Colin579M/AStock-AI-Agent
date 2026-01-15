"""
认证服务

管理 Access Code 验证和用户登录记录。
"""
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional


class AuthService:
    """认证服务"""

    def __init__(self, config_path: Optional[Path] = None):
        """
        初始化认证服务

        Args:
            config_path: access_codes.json 路径
        """
        if config_path is None:
            # Docker 容器内: /app/app/services/auth_service.py → /app/config/
            config_path = Path(__file__).parent.parent.parent / "config" / "access_codes.json"

        self.config_path = config_path
        self._load_config()
        self._login_records = {}  # user_id -> first_login_time

    def _load_config(self):
        """加载配置文件"""
        if not self.config_path.exists():
            # 创建默认配置
            self._create_default_config()

        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

    def _create_default_config(self):
        """创建默认配置文件"""
        import secrets

        # 生成安全的随机密码
        admin_code = secrets.token_urlsafe(16)

        default_config = {
            "version": "1.0",
            "codes": [
                {
                    "code_hash": self._hash_code(admin_code),
                    "user_id": "admin",
                    "name": "管理员",
                    "expires_at": None,
                    "is_active": True
                }
            ],
            "_setup_required": True,
            "_generated_admin_code": admin_code  # 首次运行后应删除此字段
        }

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)

        self.config = default_config

        # 打印首次设置信息
        print("\n" + "=" * 60)
        print("🔐 首次运行 - 已生成管理员访问码")
        print("=" * 60)
        print(f"管理员访问码: {admin_code}")
        print("请妥善保管此访问码，并在登录后添加其他用户。")
        print("=" * 60 + "\n")

    def _hash_code(self, code: str) -> str:
        """对 Access Code 进行 SHA256 哈希"""
        return hashlib.sha256(code.encode()).hexdigest()

    def verify_access_code(self, code: str) -> dict:
        """
        验证 Access Code

        Args:
            code: 用户输入的 Access Code

        Returns:
            dict: {"success": bool, "user": {...}, "message": str}
        """
        code_hash = self._hash_code(code)

        for user in self.config.get("codes", []):
            if user["code_hash"] == code_hash:
                # 检查是否激活
                if not user.get("is_active", True):
                    return {
                        "success": False,
                        "message": "该访问码已被禁用"
                    }

                # 检查是否过期
                expires_at = user.get("expires_at")
                if expires_at:
                    expire_time = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                    if datetime.now(expire_time.tzinfo) > expire_time:
                        return {
                            "success": False,
                            "message": "该访问码已过期"
                        }

                return {
                    "success": True,
                    "user": {
                        "user_id": user["user_id"],
                        "name": user["name"],
                        "expires_at": expires_at
                    }
                }

        return {
            "success": False,
            "message": "无效的访问码"
        }

    def record_login(self, user_id: str) -> bool:
        """
        记录用户登录

        Args:
            user_id: 用户 ID

        Returns:
            bool: 是否是首次登录
        """
        is_first = user_id not in self._login_records
        if is_first:
            self._login_records[user_id] = datetime.now()
        return is_first

    def add_user(self, code: str, user_id: str, name: str, expires_at: Optional[str] = None) -> bool:
        """
        添加新用户

        Args:
            code: Access Code (明文)
            user_id: 用户 ID
            name: 用户名
            expires_at: 过期时间 (ISO 格式)

        Returns:
            bool: 是否成功
        """
        # 检查 user_id 是否已存在
        for user in self.config.get("codes", []):
            if user["user_id"] == user_id:
                return False

        new_user = {
            "code_hash": self._hash_code(code),
            "user_id": user_id,
            "name": name,
            "expires_at": expires_at,
            "is_active": True
        }

        self.config["codes"].append(new_user)

        # 保存到文件
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

        return True
