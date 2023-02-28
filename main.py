from ychat import yChat

if __name__ == "__main__":
    # https://chat.openai.com/api/auth/session
    yChat().start_telegram_server()
    # yChat().start_sms_server()
