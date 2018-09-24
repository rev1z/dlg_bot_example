from googletrans import Translator
import logging
# for patch
import re
import ast
import time
import math
from googletrans.gtoken import TokenAcquirer
from googletrans.compat import unicode

logging.basicConfig(format='[%(asctime)s]: %(name)s -  %(levelname)s: \n %(message)s',
                    level=logging.WARNING)
logger = logging.getLogger(__name__)

telegram_token = "some_token"


# start of googletrans patch
from googletrans.compat import PY3
RE_TKK = re.compile(r'TKK=eval\(\'\(\(function\(\)\{(.+?)\}\)\(\)\)\'\);',
                    re.DOTALL)
RE_RAWTKK = re.compile(r'TKK=\'([^\']*)\';', re.DOTALL)


def _update(self):
    """update tkk
    """
    # we don't need to update the base TKK value when it is still valid
    now = math.floor(int(time.time() * 1000) / 3600000.0)
    if self.tkk and int(self.tkk.split('.')[0]) == now:
        return
    r = self.session.get(self.host)
    raw_tkk = self.RE_RAWTKK.search(r.text)
    if raw_tkk:
        self.tkk = raw_tkk.group(1)
        return
    # this will be the same as python code after stripping out a reserved word 'var'
    code = unicode(self.RE_TKK.search(r.text).group(1)).replace('var ', '')
    # unescape special ascii characters such like a \x3d(=)
    if PY3:  # pragma: no cover
        code = code.encode().decode('unicode-escape')
    else:  # pragma: no cover
        code = code.decode('string_escape')
    if code:
        tree = ast.parse(code)
        visit_return = False
        operator = '+'
        n, keys = 0, dict(a=0, b=0)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                name = node.targets[0].id
                if name in keys:
                    if isinstance(node.value, ast.Num):
                        keys[name] = node.value.n
                    # the value can sometimes be negative
                    elif isinstance(node.value, ast.UnaryOp) and \
                            isinstance(node.value.op, ast.USub):  # pragma: nocover
                        keys[name] = -node.value.operand.n
            elif isinstance(node, ast.Return):
                # parameters should be set after this point
                visit_return = True
            elif visit_return and isinstance(node, ast.Num):
                n = node.n
            elif visit_return and n > 0:
                # the default operator is '+' but implement some more for
                # all possible scenarios
                if isinstance(node, ast.Add):  # pragma: nocover
                    pass
                elif isinstance(node, ast.Sub):  # pragma: nocover
                    operator = '-'
                elif isinstance(node, ast.Mult):  # pragma: nocover
                    operator = '*'
                elif isinstance(node, ast.Pow):  # pragma: nocover
                    operator = '**'
                elif isinstance(node, ast.BitXor):  # pragma: nocover
                    operator = '^'
        # a safety way to avoid Exceptions
        clause = compile('{1}{0}{2}'.format(
            operator, keys['a'], keys['b']), '', 'eval')
        value = eval(clause, dict(__builtin__={}))
        result = '{}.{}'.format(n, value)
        self.tkk = result


TokenAcquirer.RE_TKK = RE_TKK
TokenAcquirer.RE_RAWTKK = RE_RAWTKK
TokenAcquirer._update = _update
# end of googletrans patch


class TextTranslator:

    @staticmethod
    def lang_detect(string: str):
        detected = detect(string)
        # print(detected)
        return detected

    def translate(self, text: str) -> str:

        detected = self.lang_detect(text)
        t = Translator()
        if detected == "ru":
            return t.translate(text, dest="en", src="ru").text
        else:
            return t.translate(text, dest="ru", src="en").text
        pass



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
