from dataclasses import dataclass, field
from ruamel.yaml import YAML, yaml_object
from pathlib import Path

yaml = YAML()


@yaml_object(yaml)
@dataclass
class Settings:
    access_token: str = ""

    @yaml_object(yaml)
    @dataclass
    class Telegram:
        access_token: str = ""
        timeout: int = 60
        error_message: str = "❌ An error occurred while processing your request"
        welcome_message: str = "👋 Hello, I'm a chatbot. Ask me anything!"
        clear_message: str = "🗑️ Conversation cleared"
        processing_message: str = "⌛️ Processing your request"
        timeout_message: str = "⏰ Request timed out"
        in_use_message: str = "🚫 Bot is in use, try again later"

    @yaml_object(yaml)
    @dataclass
    class ChatGPT:
        access_token: str | None = None
        email: str | None = None
        password: str | None = None
        session_token: str | None = None
        paid: bool = False

    telegram: Telegram = field(default_factory=Telegram)
    chatGPT: ChatGPT = field(default_factory=ChatGPT)

    @classmethod
    def load(cls):
        """Loads configuration settings from file"""
        filepath = Path("settings.yaml")
        if not filepath.exists():
            yaml.dump(cls(), filepath)
            raise FileNotFoundError(f"`{str(filepath)}` file needs to filled")
        cls_ = yaml.load(filepath)
        assert isinstance(cls_, cls)  # Okuma sorunlarını fark etmek için
        return cls_

    def save(self):
        """Save configuration settings to file"""
        yaml.dump(self, Path(f"settings.yaml"))


settings = Settings.load()
assert isinstance(settings, Settings)
assert isinstance(settings.telegram, Settings.Telegram)
assert isinstance(settings.chatGPT, Settings.ChatGPT)
