"""Engine health check and connection testing.

Provides structured validation of OpenAI connection and configuration.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional

from .env_file import get_env_resolution, mask_secret, EnvResolution
from .env_validator import EnvironmentValidator, EnvKeyStatus

logger = logging.getLogger("ai_orchestrator.engine_health")


class ConnectionStage(Enum):
    """Stages of the connection test."""
    NOT_STARTED = "not_started"
    KEY_RESOLUTION = "key_resolution"
    CLIENT_INIT = "client_init"
    CONNECTION_TEST = "connection_test"
    COMPLETED = "completed"


class ConnectionStatus(Enum):
    """Status of the connection test."""
    NOT_TESTED = "not_tested"
    TESTING = "testing"
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass
class ConnectionTestResult:
    """Result of OpenAI connection test."""
    success: bool
    stage: ConnectionStage
    status: ConnectionStatus
    env_name: str = "OPENAI_API_KEY"
    source: str = "none"  # "system", "dotenv", "none"
    key_preview: str = ""
    client_initialized: bool = False
    network_test_executed: bool = False
    message: str = ""
    details: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "stage": self.stage.value,
            "status": self.status.value,
            "env_name": self.env_name,
            "source": self.source,
            "key_preview": self.key_preview,
            "client_initialized": self.client_initialized,
            "network_test_executed": self.network_test_executed,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms,
        }


def _sanitize_error(error: Exception) -> str:
    """Sanitize error message to remove potential secrets."""
    msg = str(error)

    # Remove potential API key patterns
    import re
    msg = re.sub(r'sk-[a-zA-Z0-9]{20,}', 'sk-***', msg)
    msg = re.sub(r'api[_-]?key[=:]\s*["\']?[a-zA-Z0-9-]+["\']?', 'api_key=***', msg, flags=re.IGNORECASE)

    return msg


def check_key_resolution(
    project_root: Optional[Path] = None
) -> ConnectionTestResult:
    """
    Test Stage A: Resolve and validate the API key.

    Args:
        project_root: Optional project root for .env lookup

    Returns:
        ConnectionTestResult with key resolution status
    """
    start_time = time.time()
    details: List[str] = []

    try:
        # Get resolution details
        resolution = get_env_resolution("OPENAI_API_KEY", project_root / ".env" if project_root else None)

        if resolution.source == "none":
            # Key not found
            details.append("Variavel OPENAI_API_KEY nao encontrada")
            details.append("Verificar: variavel de ambiente ou arquivo .env")

            return ConnectionTestResult(
                success=False,
                stage=ConnectionStage.KEY_RESOLUTION,
                status=ConnectionStatus.FAILURE,
                source="none",
                message="Chave API nao encontrada.",
                details=details,
                duration_ms=int((time.time() - start_time) * 1000),
            )

        # Key found but might be empty
        if not resolution.value or not resolution.value.strip():
            details.append(f"Fonte: {resolution.source}")
            details.append("Valor: vazio ou apenas espacos")

            return ConnectionTestResult(
                success=False,
                stage=ConnectionStage.KEY_RESOLUTION,
                status=ConnectionStatus.FAILURE,
                source=resolution.source,
                message="Chave API esta vazia.",
                details=details,
                duration_ms=int((time.time() - start_time) * 1000),
            )

        # Key found and has value
        key_preview = mask_secret(resolution.value)
        details.append(f"Fonte: {resolution.source}")
        details.append(f"Preview: {key_preview}")

        if resolution.source == "system":
            details.append("Prioridade: variavel de sistema (sobrescreve .env)")
        elif resolution.source == "dotenv" and resolution.dotenv_path:
            details.append(f"Arquivo: {resolution.dotenv_path}")

        return ConnectionTestResult(
            success=True,
            stage=ConnectionStage.KEY_RESOLUTION,
            status=ConnectionStatus.SUCCESS,
            source=resolution.source,
            key_preview=key_preview,
            message="Chave API resolvida com sucesso.",
            details=details,
            duration_ms=int((time.time() - start_time) * 1000),
        )

    except Exception as e:
        logger.error(f"Key resolution error: {_sanitize_error(e)}")
        details.append(f"Erro: {_sanitize_error(e)}")

        return ConnectionTestResult(
            success=False,
            stage=ConnectionStage.KEY_RESOLUTION,
            status=ConnectionStatus.FAILURE,
            message="Erro ao resolver chave API.",
            details=details,
            duration_ms=int((time.time() - start_time) * 1000),
        )


def check_client_initialization(
    api_key: str
) -> ConnectionTestResult:
    """
    Test Stage B: Initialize the OpenAI client.

    Args:
        api_key: The API key to use

    Returns:
        ConnectionTestResult with client initialization status
    """
    start_time = time.time()
    details: List[str] = []
    key_preview = mask_secret(api_key)

    try:
        from openai import OpenAI

        details.append("Inicializando cliente OpenAI...")

        # Create client (this doesn't make network calls)
        client = OpenAI(api_key=api_key)

        details.append("Cliente OpenAI criado com sucesso")
        details.append(f"Chave: {key_preview}")

        return ConnectionTestResult(
            success=True,
            stage=ConnectionStage.CLIENT_INIT,
            status=ConnectionStatus.SUCCESS,
            key_preview=key_preview,
            client_initialized=True,
            message="Cliente OpenAI inicializado.",
            details=details,
            duration_ms=int((time.time() - start_time) * 1000),
        )

    except ImportError as e:
        details.append("Biblioteca openai nao instalada")
        details.append("Executar: pip install openai")

        return ConnectionTestResult(
            success=False,
            stage=ConnectionStage.CLIENT_INIT,
            status=ConnectionStatus.FAILURE,
            key_preview=key_preview,
            client_initialized=False,
            message="Biblioteca OpenAI nao encontrada.",
            details=details,
            duration_ms=int((time.time() - start_time) * 1000),
        )

    except Exception as e:
        details.append(f"Erro: {_sanitize_error(e)}")

        return ConnectionTestResult(
            success=False,
            stage=ConnectionStage.CLIENT_INIT,
            status=ConnectionStatus.FAILURE,
            key_preview=key_preview,
            client_initialized=False,
            message="Falha ao inicializar cliente OpenAI.",
            details=details,
            duration_ms=int((time.time() - start_time) * 1000),
        )


def check_network_connection(
    api_key: str,
    timeout_seconds: int = 10
) -> ConnectionTestResult:
    """
    Test Stage C: Perform a lightweight network test.

    Uses the models.list() endpoint which is fast and low-cost.

    Args:
        api_key: The API key to use
        timeout_seconds: Request timeout

    Returns:
        ConnectionTestResult with network test status
    """
    start_time = time.time()
    details: List[str] = []
    key_preview = mask_secret(api_key)

    try:
        from openai import OpenAI, AuthenticationError, APIConnectionError, RateLimitError
        import httpx

        details.append("Testando conexao com API OpenAI...")

        # Create client with timeout
        client = OpenAI(
            api_key=api_key,
            timeout=httpx.Timeout(timeout_seconds)
        )

        # Use models.list() - lightweight endpoint
        # This validates: authentication, network, and basic API access
        models = client.models.list()

        # Count models to confirm response
        model_count = len(list(models))
        details.append(f"Conexao estabelecida com sucesso")
        details.append(f"Modelos disponiveis: {model_count}")
        details.append(f"Chave: {key_preview}")

        return ConnectionTestResult(
            success=True,
            stage=ConnectionStage.CONNECTION_TEST,
            status=ConnectionStatus.SUCCESS,
            key_preview=key_preview,
            client_initialized=True,
            network_test_executed=True,
            message="Conexao com OpenAI validada com sucesso.",
            details=details,
            duration_ms=int((time.time() - start_time) * 1000),
        )

    except AuthenticationError as e:
        details.append("Falha de autenticacao")
        details.append("A chave API e invalida ou foi revogada")
        details.append(f"Chave usada: {key_preview}")

        return ConnectionTestResult(
            success=False,
            stage=ConnectionStage.CONNECTION_TEST,
            status=ConnectionStatus.FAILURE,
            key_preview=key_preview,
            client_initialized=True,
            network_test_executed=True,
            message="Falha de autenticacao: chave invalida.",
            details=details,
            duration_ms=int((time.time() - start_time) * 1000),
        )

    except RateLimitError as e:
        details.append("Limite de requisicoes atingido")
        details.append("A chave e valida, mas esta temporariamente limitada")
        details.append("Aguarde alguns minutos e tente novamente")

        return ConnectionTestResult(
            success=False,
            stage=ConnectionStage.CONNECTION_TEST,
            status=ConnectionStatus.FAILURE,
            key_preview=key_preview,
            client_initialized=True,
            network_test_executed=True,
            message="Limite de requisicoes atingido.",
            details=details,
            duration_ms=int((time.time() - start_time) * 1000),
        )

    except APIConnectionError as e:
        details.append("Falha de conexao de rede")
        details.append("Verificar: conexao com internet")
        details.append("Verificar: firewall ou proxy")

        return ConnectionTestResult(
            success=False,
            stage=ConnectionStage.CONNECTION_TEST,
            status=ConnectionStatus.FAILURE,
            key_preview=key_preview,
            client_initialized=True,
            network_test_executed=True,
            message="Falha de conexao de rede.",
            details=details,
            duration_ms=int((time.time() - start_time) * 1000),
        )

    except TimeoutError:
        details.append(f"Timeout apos {timeout_seconds} segundos")
        details.append("A API nao respondeu a tempo")
        details.append("Verificar: conexao com internet")

        return ConnectionTestResult(
            success=False,
            stage=ConnectionStage.CONNECTION_TEST,
            status=ConnectionStatus.FAILURE,
            key_preview=key_preview,
            client_initialized=True,
            network_test_executed=True,
            message="Timeout: API nao respondeu.",
            details=details,
            duration_ms=int((time.time() - start_time) * 1000),
        )

    except Exception as e:
        details.append(f"Erro: {_sanitize_error(e)}")

        return ConnectionTestResult(
            success=False,
            stage=ConnectionStage.CONNECTION_TEST,
            status=ConnectionStatus.FAILURE,
            key_preview=key_preview,
            client_initialized=True,
            network_test_executed=True,
            message="Erro ao testar conexao.",
            details=details,
            duration_ms=int((time.time() - start_time) * 1000),
        )


def check_openai_connection(
    project_root: Optional[Path] = None,
    skip_network_test: bool = False,
    timeout_seconds: int = 10
) -> ConnectionTestResult:
    """
    Run complete OpenAI connection test.

    Executes all test stages in order:
    1. Key resolution
    2. Client initialization
    3. Network connection test (optional)

    Args:
        project_root: Optional project root for .env lookup
        skip_network_test: If True, skip the network test
        timeout_seconds: Timeout for network test

    Returns:
        ConnectionTestResult with final status
    """
    total_start = time.time()
    all_details: List[str] = []

    logger.info("Starting OpenAI connection test")

    # Stage A: Key resolution
    logger.info("Stage A: Testing key resolution")
    key_result = check_key_resolution(project_root)
    all_details.extend(key_result.details)
    all_details.append("---")

    if not key_result.success:
        logger.warning(f"Key resolution failed: {key_result.message}")
        key_result.details = all_details
        key_result.duration_ms = int((time.time() - total_start) * 1000)
        return key_result

    # Get the actual key value for next stages
    resolution = get_env_resolution("OPENAI_API_KEY", project_root / ".env" if project_root else None)
    api_key = resolution.value

    # Stage B: Client initialization
    logger.info("Stage B: Testing client initialization")
    client_result = check_client_initialization(api_key)
    all_details.extend(client_result.details)
    all_details.append("---")

    if not client_result.success:
        logger.warning(f"Client init failed: {client_result.message}")
        client_result.source = key_result.source
        client_result.details = all_details
        client_result.duration_ms = int((time.time() - total_start) * 1000)
        return client_result

    # Stage C: Network test (optional)
    if skip_network_test:
        logger.info("Stage C: Network test skipped")
        all_details.append("Teste de rede: ignorado")

        return ConnectionTestResult(
            success=True,
            stage=ConnectionStage.COMPLETED,
            status=ConnectionStatus.SUCCESS,
            source=key_result.source,
            key_preview=client_result.key_preview,
            client_initialized=True,
            network_test_executed=False,
            message="Cliente inicializado; teste de rede nao executado.",
            details=all_details,
            duration_ms=int((time.time() - total_start) * 1000),
        )

    logger.info("Stage C: Testing network connection")
    network_result = check_network_connection(api_key, timeout_seconds)
    all_details.extend(network_result.details)

    # Final result
    network_result.source = key_result.source
    network_result.details = all_details
    network_result.stage = ConnectionStage.COMPLETED if network_result.success else network_result.stage
    network_result.duration_ms = int((time.time() - total_start) * 1000)

    if network_result.success:
        logger.info(f"Connection test passed in {network_result.duration_ms}ms")
    else:
        logger.warning(f"Connection test failed: {network_result.message}")

    return network_result
