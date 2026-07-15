# core/local_api_manager.py
import asyncio
import subprocess
import os
import time
from pathlib import Path
from typing import Tuple, Optional

class LocalApiManager:
    def __init__(self, config: dict, env_vars: dict):
        self.config = config
        self.env_vars = env_vars
        self.base_dir = Path(config.get("data_dir", "/tmp/local_bot"))
        self.compose_file = self.base_dir / "docker-compose.yml"
        self.container_name = "local_telegram_api"
        
        # Параметры из конфига (используются для проверки доступности)
        self.host = config.get("host", "192.168.50.1")
        self.port = config.get("port", 8002)
        self.image = config.get("image", "aiogram/telegram-bot-api:latest")

    def _get_env(self) -> dict:
        """
        Формирует окружение для docker compose команды.
        Теперь передаем только API ID и Hash, так как порты жестко заданы в YAML.
        """
        env = os.environ.copy()
        env.update(self.env_vars)
        # LOCAL_API_PORT и HOST больше не нужны для маппинга, но можно оставить для безопасности
        return env

    async def _run_compose_command(self, command: list[str]) -> Tuple[bool, str]:
        """Запускает docker compose команду."""
        if not self.compose_file.exists():
            return False, f"Файл docker-compose.yml не найден: {self.compose_file}"

        cmd = ["docker", "compose", "-f", str(self.compose_file)] + command
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._get_env()
            )
            stdout, stderr = await proc.communicate()
            
            out_text = stdout.decode('utf-8', errors='ignore').strip()
            err_text = stderr.decode('utf-8', errors='ignore').strip()

            if proc.returncode != 0:
                return False, err_text or f"Код выхода: {proc.returncode}"
            return True, out_text or "Выполнено успешно."
        except Exception as e:
            return False, f"Ошибка выполнения: {str(e)}"

    async def is_running(self) -> bool:
        """Проверяет, запущен ли контейнер."""
        cmd = ["docker", "inspect", "-f", "{{.State.Running}}", self.container_name]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            if proc.returncode == 0:
                return stdout.decode().strip().lower() == "true"
        except Exception:
            pass
        return False

    async def start(self) -> Tuple[bool, str]:
        """Запускает контейнер через docker compose start (или up -d если не создан)."""
        success, msg = await self._run_compose_command(["start"])
        
        if not success:
            # Если start не удался (контейнер не создан), пробуем up -d
            check_cmd = ["docker", "ps", "-a", "-q", "-f", f"name={self.container_name}"]
            try:
                proc = await asyncio.create_subprocess_exec(*check_cmd, stdout=asyncio.subprocess.PIPE)
                out, _ = await proc.communicate()
                if not out.strip():
                    print(f"⚠️ Контейнер {self.container_name} не найден. Запуск через 'up -d'...")
                    return await self._run_compose_command(["up", "-d"])
            except Exception:
                pass
            
            return False, f"Не удалось запустить: {msg}. Попробуйте 'docker compose up -d' вручную."
        
        return True, "Контейнер запущен."

    async def stop(self) -> Tuple[bool, str]:
        """Останавливает контейнер через docker compose stop."""
        return await self._run_compose_command(["stop"])

    async def wait_ready(self, timeout: int = 30) -> bool:
        """Ждет, пока порт станет доступен на хосте."""
        url = f"http://{self.host}:{self.port}"
        start_time = time.time()
        
        print(f"⏳ Ожидание готовности Local API на {url}...")
        
        while time.time() - start_time < timeout:
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port),
                    timeout=2.0
                )
                writer.close()
                await writer.wait_closed()
                print(f"✅ Local API готов!")
                return True
            except (ConnectionRefusedError, OSError, asyncio.TimeoutError):
                await asyncio.sleep(1)
            except Exception:
                await asyncio.sleep(1)
        
        print(f"❌ Таймаут ожидания Local API ({timeout} сек).")
        return False