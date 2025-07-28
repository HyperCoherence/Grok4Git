"""
Configuration management for Grok4Git.

This module handles environment variables, API configuration,
and other settings for the application.
"""

import os
import logging
import shutil
from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Prompt
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("grok4git.log")],
)

logger = logging.getLogger(__name__)
console = Console()


class Config:
    """Configuration class for Grok4Git application."""

    def __init__(self):
        """Initialize configuration by loading environment variables."""
        load_dotenv()
        # Only run interactive setup if not in testing/CI environment
        if not self._is_testing_environment():
            self._ensure_env_setup()

    def _is_testing_environment(self) -> bool:
        """Check if we're running in a testing environment."""
        return (
            os.getenv("PYTEST_CURRENT_TEST") is not None or
            os.getenv("CI") is not None or
            os.getenv("GITHUB_ACTIONS") is not None or
            "pytest" in sys.modules
        )

    @property
    def xai_api_key(self) -> str:
        """Get xAI API key from environment."""
        return os.getenv("XAI_API_KEY", "")

    @property
    def github_token(self) -> str:
        """Get GitHub token from environment."""
        return os.getenv("GITHUB_TOKEN", "")

    @property
    def github_username(self) -> str:
        """Get GitHub username from environment."""
        return os.getenv("GITHUB_USERNAME", "")

    @property
    def model_name(self) -> str:
        """Get AI model name from environment or use default."""
        return os.getenv("MODEL_NAME", "grok-4-0709")

    @property
    def xai_base_url(self) -> str:
        """Get xAI base URL from environment or use default."""
        return os.getenv("XAI_BASE_URL", "https://api.x.ai/v1")

    @property
    def github_api_base_url(self) -> str:
        """Get GitHub API base URL from environment or use default."""
        return os.getenv("GITHUB_API_BASE_URL", "https://api.github.com")

    @property
    def log_level(self) -> str:
        """Get log level from environment or use default."""
        return os.getenv("LOG_LEVEL", "INFO").upper()

    @property
    def max_file_size_mb(self) -> int:
        """Get maximum file size in MB for processing."""
        return int(os.getenv("MAX_FILE_SIZE_MB", "1"))

    @property
    def api_timeout(self) -> int:
        """Get API timeout in seconds for GitHub API calls (not AI requests)."""
        return int(os.getenv("API_TIMEOUT", "30"))

    @property
    def github_api_version(self) -> str:
        """Get GitHub API version."""
        return os.getenv("GITHUB_API_VERSION", "2022-11-28")

    @property
    def pr_peer_review_enabled(self) -> bool:
        """Get whether peer review is enabled for pull requests."""
        return os.getenv("ENABLE_PR_PEER_REVIEW", "false").lower() == "true"

    @property
    def peer_review_model(self) -> str:
        """Get the AI model to use for peer review (defaults to main model)."""
        return os.getenv("PEER_REVIEW_MODEL", self.model_name)

    @property
    def max_review_iterations(self) -> int:
        """Get maximum number of review iterations allowed."""
        return int(os.getenv("MAX_REVIEW_ITERATIONS", "3"))

    @property
    def auto_recover_empty_responses(self) -> bool:
        """Get whether to automatically recover from empty responses."""
        return os.getenv("AUTO_RECOVER_EMPTY_RESPONSES", "true").lower() == "true"

    @property
    def max_recovery_attempts(self) -> int:
        """Get maximum number of recovery attempts for empty responses."""
        return int(os.getenv("MAX_RECOVERY_ATTEMPTS", "2"))

    def _ensure_env_setup(self) -> None:
        """Ensure environment variables are set up, prompt user if missing."""
        # Check if .env exists, if not, check if .env.example exists and copy it
        if not os.path.exists(".env"):
            if os.path.exists(".env.example"):
                console.print("🔧 No .env file found, but .env.example exists.", style="yellow")
                if (
                    Prompt.ask(
                        "Would you like to copy .env.example to .env?",
                        choices=["y", "n"],
                        default="y",
                    )
                    == "y"
                ):
                    shutil.copy(".env.example", ".env")
                    console.print("✅ Created .env file from .env.example", style="green")
                    console.print(
                        "📝 Please edit .env with your actual API keys and run again.",
                        style="yellow",
                    )
                    return
            else:
                console.print(
                    "⚠️  No .env file found and no .env.example to copy from.", style="yellow"
                )
                if (
                    Prompt.ask(
                        "Would you like to create a .env file now?", choices=["y", "n"], default="y"
                    )
                    == "y"
                ):
                    self._create_env_file()
                    # Continue to load the newly created .env file
                else:
                    # User declined to create .env file
                    return

        # Reload environment variables after potential .env creation
        load_dotenv(override=True)

        # Validate required variables
        self._validate_required_vars()

    def _create_env_file(self) -> None:
        """Create .env file by prompting user for values."""
        console.print("🔧 Creating .env file...", style="blue")

        # Prompt for required values
        console.print("\n📋 Required configuration:")
        xai_key = Prompt.ask(
            "Enter your xAI API key (get from https://console.x.ai/)", password=True
        )
        github_token = Prompt.ask(
            "Enter your GitHub token (get from https://github.com/settings/tokens)", password=True
        )
        github_username = Prompt.ask("Enter your GitHub username")

        # Ask if user wants to configure optional values
        configure_optional = Prompt.ask(
            "\nWould you like to configure optional settings?", choices=["y", "n"], default="n"
        )

        model_name = self.model_name
        log_level = self.log_level

        if configure_optional == "y":
            console.print("\n⚙️  Optional configuration:")
            model_name = Prompt.ask("AI model name", default=self.model_name)
            log_level = Prompt.ask(
                "Log level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default=self.log_level
            )

        # Write .env file
        env_content = f"""# Grok4Git Environment Configuration
# Generated on setup

# Required: xAI API Key for Grok AI model
XAI_API_KEY={xai_key}

# Required: GitHub Personal Access Token
GITHUB_TOKEN={github_token}

# Required: Your GitHub username
GITHUB_USERNAME={github_username}

# Optional: AI model name
MODEL_NAME={model_name}

# Optional: xAI API base URL
XAI_BASE_URL={self.xai_base_url}

# Optional: GitHub API base URL
GITHUB_API_BASE_URL={self.github_api_base_url}

# Optional: Log level
LOG_LEVEL={log_level}

# Optional: Maximum file size in MB for processing
MAX_FILE_SIZE_MB={self.max_file_size_mb}

# Optional: API timeout in seconds (for GitHub API calls, not AI requests)
API_TIMEOUT={self.api_timeout}

# Optional: GitHub API version
GITHUB_API_VERSION={self.github_api_version}

# Optional: Enable peer review for pull requests
ENABLE_PR_PEER_REVIEW={str(self.pr_peer_review_enabled).lower()}

# Optional: AI model to use for peer review (defaults to main model)
PEER_REVIEW_MODEL={self.peer_review_model}

# Optional: Maximum number of review iterations
MAX_REVIEW_ITERATIONS={self.max_review_iterations}

# Optional: Auto-recover from empty responses
AUTO_RECOVER_EMPTY_RESPONSES={str(self.auto_recover_empty_responses).lower()}

# Optional: Maximum recovery attempts for empty responses
MAX_RECOVERY_ATTEMPTS={self.max_recovery_attempts}
"""

        with open(".env", "w") as f:
            f.write(env_content)

        console.print("✅ .env file created successfully!", style="green")
        console.print("🔐 Your API keys are now securely stored in .env", style="green")

    def _validate_required_vars(self) -> None:
        """Validate that all required environment variables are set."""
        required_vars = [
            ("XAI_API_KEY", self.xai_api_key),
            ("GITHUB_TOKEN", self.github_token),
            ("GITHUB_USERNAME", self.github_username),
        ]

        missing_vars = [var_name for var_name, var_value in required_vars if not var_value]

        if missing_vars:
            console.print(
                f"❌ Missing required environment variables: {', '.join(missing_vars)}", style="red"
            )
            console.print(
                "💡 Please check your .env file and ensure all required values are set.",
                style="yellow",
            )
            console.print("📖 See .env.example for reference.", style="yellow")
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

        logger.info("Configuration validated successfully")

    def get_github_headers(self) -> dict:
        """Get headers for GitHub API requests."""
        return {
            "Authorization": f"Bearer {self.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": self.github_api_version,
        }

    def setup_logging(self) -> None:
        """Setup logging configuration."""
        numeric_level = getattr(logging, self.log_level, None)
        if not isinstance(numeric_level, int):
            raise ValueError(f"Invalid log level: {self.log_level}")

        logging.getLogger().setLevel(numeric_level)
        logger.info(f"Logging level set to {self.log_level}")


# Global configuration instance (lazy initialization)
_config_instance = None

def get_config() -> Config:
    """Get the global configuration instance (lazy initialization)."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance

# For backward compatibility, create a property-like access
class ConfigProxy:
    """Proxy object that provides lazy access to config properties."""
    def __getattr__(self, name):
        return getattr(get_config(), name)

config = ConfigProxy()
