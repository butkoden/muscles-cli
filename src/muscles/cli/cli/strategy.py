from muscles.core import BaseStrategy
import os
import io
import sys
import shutil
from typing import List, Optional
from .colory import Colors
from .instance import cli, Console
from .error_handler import ConsoleErrorHandler


class flushfile(object):

    def __init__(self, f):
        self.f = f

    def write(self, x):
        pass

    def flush(self):
        pass


class CliStrategy(BaseStrategy):
    """
    Стратегия для контекста переводящая обработку в режим работы в консоли

    """
    try:
        size = shutil.get_terminal_size(fallback=(100, 50))
        rows, columns = size.lines, size.columns
    except:
        rows = 50
        columns = 100

    def _print_header(self):
        """
        Печатаем базовый заголовок в консоли

        :return:
        """
        author = '(c) Butko Denis'
        lines = [
            '-' * (int(self.columns) - 4),
            'Muscular',
            'CLI',
            author.rjust(int(self.columns)-len(author)),
            '-' * (int(self.columns) - 4),
        ]
        for line in lines:
            print(f"{Colors.HEADER}--{line.center(int(self.columns)-4)}--{Colors.ENDC}")

    def execute(self, *args,
                error_handler: Optional[ConsoleErrorHandler] = None,
                shutup=False,
                print_header=False,
                **kwargs) -> List:
        """
        Первичный обработчик консольных команд

        :param args:
        :param shutup: приглушаем весь вывод в stdout
        :param error_handler:
        :param kwargs:
        :return:
        """
        try:
            if shutup:
                sys.stdout = io.StringIO()
                print_header = False
            if not print_header:
                self._print_header()
            if len(args) <= 0:
                args = sys.argv[1:]
            # console = Console()
            # result = console.root_group.execute(*args, {})
            result = cli.execute(*args)
            if shutup:
                sys.stdout = sys.__stdout__
            return result
        except KeyboardInterrupt:
            print(f"\n\n{Colors.WARNING}The programme was terminated (Ctrl+C).{Colors.ENDC}")
