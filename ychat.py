from revChatGPT.V1 import Chatbot
from settings import settings
from telegram import Update, Message
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    filters,
    MessageHandler,
)
from traceback import format_exc


class yChat:
    __slots__ = "chatbot"

    chatbot: Chatbot

    def __init__(self):
        if settings.chatGPT.access_token:
            self.chatbot = Chatbot(
                config={
                    "access_token": settings.chatGPT.access_token,
                    "paid": settings.chatGPT.paid,
                }
            )
        elif settings.chatGPT.email and settings.chatGPT.password:
            self.chatbot = Chatbot(
                config={
                    "email": settings.chatGPT.email,
                    "password": settings.chatGPT.password,
                    "paid": settings.chatGPT.paid,
                }
            )
        elif settings.chatGPT.session_token:
            self.chatbot = Chatbot(
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
        assert update.message and update.effective_chat
        chat_id = update.effective_chat.id

        prev_text = ""
        sent_text = ""
        message: None | Message = None

        try:
            for data in self.chatbot.ask(
                update.message.text,
                conversation_id=settings.telegram.conv_id_by_chat_id.get(chat_id),
            ):
                text = data["message"]
                if len(text.split()) - len(sent_text.split()) > 3:
                    if message is None:
                        message = await context.bot.send_message(
                            chat_id=chat_id, text=text
                        )
                    elif prev_text != text.strip():
                        await context.bot.edit_message_text(
                            chat_id=chat_id, message_id=message.id, text=text
                        )
                    sent_text = text
                prev_text = text
            if sent_text != prev_text and message:
                await context.bot.edit_message_text(
                    chat_id=chat_id, message_id=message.id, text=prev_text
                )
                sent_text = prev_text

            assert self.chatbot.conversation_id
            settings.telegram.conv_id_by_chat_id[chat_id] = self.chatbot.conversation_id
            settings.save()
        except Exception:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"{settings.telegram.error_message}:\n\n" + format_exc(),
            )

    async def __new(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        assert update.effective_chat
        if update.effective_chat.id in settings.telegram.conv_id_by_chat_id:
            conv_id = settings.telegram.conv_id_by_chat_id.pop(update.effective_chat.id)
            settings.save()
            self.chatbot.delete_conversation(conv_id)
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
