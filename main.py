from telegram.ext import Updater, MessageHandler, CommandHandler, Filters
from langdetect import detect, detect_langs
from translate import Translator as Ttrans
import logging

logging.basicConfig(format='[%(asctime)s]: %(name)s -  %(levelname)s: \n %(message)s',
                    level=logging.WARNING)
logger = logging.getLogger(__name__)

telegram_token = "sometoken"

class TextTranslator:

    @staticmethod
    def lang_detect(string: str):
        detected =  detect(string)
        # print(detected)
        return detected

    def translate(self, text: str) -> str:

        detected = self.lang_detect(text)
        if detected == "ru":
            t = Ttrans(to_lang="en", from_lang=detected)
            return t.translate(text)
        else:

            t = Ttrans(to_lang="ru", from_lang="en")
            return t.translate(text)


class ChatHandler:
    def __init__(self):
        self.translator = None

    def set_translator(self, translator:TextTranslator):
        self.translator = translator

    @staticmethod
    def send_response(text: str, bot, update):
        update.message.reply_text(text)

    def greet(self, bot, update):
        txt = 'Привет. Я Переводчик. Стараюсь переводить с английского на русский и обратно'
        self.send_response(txt, bot, update)

    def error(self, bot, update, error):
        logger.warning('Update "%s" caused error "%s"', update, error)

    def translate(self, bot, update):
        msg = update.message.text
        translated_txt = self.translator.translate(msg)
        self.send_response(translated_txt, bot, update)

def executor():
    chat = ChatHandler()
    chat.set_translator(TextTranslator())
    updater = Updater(telegram_token)


    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", chat.greet))
    dispatcher.add_handler(MessageHandler(Filters.text, chat.translate))
    dispatcher.add_error_handler(chat.error)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    executor()
