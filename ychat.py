from revChatGPT.V1 import AsyncChatbot
from settings import settings
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    filters,
    MessageHandler,
)


class yChat:
    __slots__ = "chatbot"

    chatbot: AsyncChatbot

    def __init__(self):
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

    async def __response(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        assert update.effective_chat and update.message
        chat_id = update.effective_chat.id
        message = await context.bot.send_message(
            chat_id=chat_id,
            text=settings.telegram.processing_message
            + f"({settings.telegram.timeout}s)",
        )

        sent_text = prev_text = ""
        try:
            async for data in self.chatbot.ask(
                update.message.text,
                conversation_id=settings.telegram.conv_id,
                timeout=settings.telegram.timeout,
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

            assert self.chatbot.conversation_id
            settings.telegram.conv_id = self.chatbot.conversation_id
            settings.save()
        except Exception:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message.id,
                text=settings.telegram.error_message,
            )

    async def __new(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        assert update.effective_chat
        if settings.telegram.conv_id:
            await self.chatbot.delete_conversation(settings.telegram.conv_id)
            settings.telegram.conv_id = None
            settings.save()
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=settings.telegram.clear_message
        )

    async def __start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        assert update.effective_chat
        chat_id = update.effective_chat.id
        message = settings.telegram.welcome_message
        await context.bot.send_message(chat_id=chat_id, text=message)

    def start(self) -> None:
        # https://chat.openai.com/api/auth/session
        application = ApplicationBuilder().token(settings.telegram.access_token).build()
        start_handler = CommandHandler("start", self.__start)
        message_handler = MessageHandler(
            filters.TEXT & (~filters.COMMAND), self.__response
        )
        clear_handler = CommandHandler("new", self.__new)
        application.add_handler(start_handler)
        application.add_handler(clear_handler)
        application.add_handler(message_handler)

        application.run_polling()
