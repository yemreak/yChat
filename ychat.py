from revChatGPT.V1 import AsyncChatbot
from settings import settings
from httpx import ReadTimeout
from traceback import format_exc
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    filters,
    MessageHandler,
)


class yChat:
    __slots__ = ("chatbot", "is_bot_in_use")

    chatbot: AsyncChatbot
    is_bot_in_use: bool

    def __init__(self):
        self.is_bot_in_use = False
        if settings.chatGPT.access_token:
            self.chatbot = AsyncChatbot(
                config={
                    "access_token": settings.chatGPT.access_token,
                    "paid": settings.chatGPT.paid,
                }
            )
        elif settings.chatGPT.email and settings.chatGPT.password:
            self.chatbot = AsyncChatbot(
                config={
                    "email": settings.chatGPT.email,
                    "password": settings.chatGPT.password,
                    "paid": settings.chatGPT.paid,
                }
            )
        elif settings.chatGPT.session_token:
            self.chatbot = AsyncChatbot(
                config={
                    "session_token": settings.chatGPT.session_token,
                    "paid": settings.chatGPT.paid,
                }
            )
        else:
            raise ValueError(
                "Need any of access_token, email, password or session_token to use revChatGPT"
            )

    def start_telegram_server(self) -> None:
        async def __start(update: Update, context: ContextTypes.DEFAULT_TYPE):
            assert update.effective_chat
            chat_id = update.effective_chat.id
            message = settings.telegram.welcome_message
            await context.bot.send_message(chat_id=chat_id, text=message)

        async def __response(update: Update, context: ContextTypes.DEFAULT_TYPE):
            assert update.effective_chat and update.message
            chat_id = update.effective_chat.id

            if self.is_bot_in_use:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=settings.telegram.processing_message
                    + f"({settings.telegram.timeout}s)",
                )
                return

            self.is_bot_in_use = True
            message = await context.bot.send_message(
                chat_id=chat_id,
                text=settings.telegram.processing_message
                + f"({settings.telegram.timeout}s)",
            )

            sent_text = prev_text = ""
            try:
                async for data in self.chatbot.ask(
                    update.message.text,
                    timeout=settings.telegram.timeout,
                    conversation_id=settings.telegram.conv_id_by_chat_id.get(chat_id),
                ):
                    text = data["message"]
                    if (
                        len(text.split()) - len(sent_text.split()) > 3
                        and prev_text != text.strip()
                    ):
                        await context.bot.edit_message_text(
                            chat_id=chat_id, message_id=message.id, text=text
                        )
                        sent_text = text
                    prev_text = text
                if sent_text != prev_text:
                    await context.bot.edit_message_text(
                        chat_id=chat_id, message_id=message.id, text=prev_text
                    )
                    sent_text = prev_text
                settings.telegram.conv_id_by_chat_id[
                    chat_id
                ] = self.chatbot.conversation_id
                settings.save()
            except Exception as e:
                if isinstance(e, ReadTimeout):
                    text = settings.telegram.timeout_message
                else:
                    text = settings.telegram.error_message + format_exc()[-100:]
                await context.bot.edit_message_text(
                    chat_id=chat_id, message_id=message.id, text=text
                )
            self.is_bot_in_use = False

        # https://chat.openai.com/api/auth/session
        application = ApplicationBuilder().token(settings.telegram.access_token).build()
        start_handler = CommandHandler("start", __start)
        message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), __response)
        application.add_handler(start_handler)
        application.add_handler(message_handler)

        application.run_polling()
