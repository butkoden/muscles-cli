from __future__ import annotations
import threading
import getpass

# import sys
#
#
# def parse_arguments():
#     args = sys.argv[1:]  # Игнорировать первый элемент, так как он является именем скрипта
#     parsed_args = {}
#
#     i = 0
#     while i < len(args):
#         arg = args[i]
#         if arg.startswith("--"):
#             # Длинный аргумент с префиксом "--"
#             if "=" in arg:  # Аргумент содержит значение
#                 key, value = arg[2:].split("=")
#                 parsed_args[key] = value
#             else:  # Аргумент является флагом
#                 key = arg[2:]
#                 parsed_args[key] = True
#         elif arg.startswith("-"):
#             # Короткая версия аргумента с префиксом "-"
#             if len(arg) > 2:  # Аргумент содержит значение
#                 key = arg[1]
#                 value = arg[2:]
#                 parsed_args[key] = value
#             else:  # Аргумент является флагом
#                 key = arg[1]
#                 parsed_args[key] = True
#         i += 1
#
#     return parsed_args


def argsparse(arguments, args):
    """
    @TODO переписать логику
    Парсер аргументов командной строки

    :param arguments:
    :param args:
    :return:
    """
    kwargs = {}
    args = list(args)
    i = 0
    arguments.reverse()
    for argument in arguments:
        if argument.required and argument.argument not in args:
            args.insert(i, argument.argument)
            i = i + 1
    new_args = args
    for argument in arguments:
        if argument.nargs > 1 or argument.multiple:
            kwargs[argument.dest] = []
        else:
            kwargs[argument.dest] = argument.default
        _args = iter(args)
        arg = next(_args, False)
        while arg:
            next_arg = next(_args, False)
            if arg == argument.argument or arg == argument.short:
                if arg in new_args:
                    new_args.remove(arg)
                if argument.nargs <= 0:
                    '''Обрабатываем флаги'''
                    kwargs[argument.dest] = argument.flag_value
                elif argument.nargs == 1:
                    '''Обрабатываем элемент со значением'''
                    value = False if next_arg and next_arg[0:1] == '-' else next_arg
                    if value:
                        if value in new_args:
                            new_args.remove(value)
                        if argument.multiple:
                            kwargs[argument.dest].append(value)
                        else:
                            kwargs[argument.dest] = value
                    if argument.prompt and not kwargs[argument.dest] and argument.password:
                        kwargs[argument.dest] = getpass.getpass(
                            f"{argument.prompt if argument.prompt else 'Password'}: ").strip()
                    if argument.prompt and not kwargs[argument.dest] and not argument.password:
                        kwargs[argument.dest] = input(f"{argument.prompt}: ").strip()
                elif argument.nargs > 1:
                    '''Обрабатываем списки аргументов'''
                    for l in range(argument.nargs):
                        value = False if next_arg and next_arg[0:1] == '-' else next_arg
                        if value:
                            if value in new_args:
                                new_args.remove(value)
                            kwargs[argument.dest].append(value)
                        if argument.prompt and len(kwargs[argument.dest]) <= l:
                            kwargs[argument.dest].append(input(f"{argument.prompt}: ").strip())
                        # arg = next_arg
                        if value:
                            '''Берем следующий только если текущий был найден, 
                            иначе будем получать пропуски элементов'''
                            next_arg = next(_args, False)
            arg = next_arg

        if argument.nargs > 1:
            if argument.required and argument.nargs != len(kwargs[argument.dest]):
                raise Exception(
                    f"Argument {argument.argument if argument.argument else argument.short} is required")
        elif argument.required and not kwargs[argument.dest]:
            raise Exception(
                f"Argument {argument.argument if argument.argument else argument.short} is required")

    return tuple(new_args), kwargs


def parse_arguments(argument_list, args):
    """
    Парсер аргументов командной строки

    :param argument_list: Список возможных аргументов командной строки в виде объектов
    :param args: Список аргументов командной строки
    :return: Кортеж с невостребованными аргументами и словарь полученных аргументов
    """
    kwargs = {}
    unused_args = list(args)

    for argument in argument_list:
        if argument.argument:
            prefix = f"{argument.argument}="
            for idx, token in enumerate(list(unused_args)):
                if isinstance(token, str) and token.startswith(prefix):
                    value = token[len(prefix):]
                    unused_args[idx:idx + 1] = [argument.argument, value]
                    break
        if argument.short:
            prefix = f"{argument.short}="
            for idx, token in enumerate(list(unused_args)):
                if isinstance(token, str) and token.startswith(prefix):
                    value = token[len(prefix):]
                    unused_args[idx:idx + 1] = [argument.short, value]
                    break

        if argument.dest not in kwargs and argument.default is not None:
            kwargs[argument.dest] = argument.default

        if argument.short and argument.short in unused_args:
            index = unused_args.index(argument.short)
            process_argument(argument, unused_args, kwargs, index)

        elif argument.argument and argument.argument in unused_args:
            index = unused_args.index(argument.argument)
            process_argument(argument, unused_args, kwargs, index)

        if argument.required and argument.dest not in kwargs:
            if argument.prompt:
                value = getpass.getpass(argument.prompt) if argument.hide else input(argument.prompt).strip()
                kwargs[argument.dest] = value.strip()
            else:
                raise ValueError(
                    f"Required argument {argument.argument if argument.argument else argument.short} is missing")

    return tuple(unused_args), kwargs


def process_argument(argument, unused_args, kwargs, index):
    """
    Обработка аргумента командной строки

    :param argument: Объект аргумента командной строки
    :param unused_args: Список невостребованных аргументов
    :param kwargs: Словарь полученных аргументов
    :param index: Индекс аргумента в списке аргументов командной строки
    """

    if argument.multiple:
        values = []
        for value in unused_args[index + 1:]:
            if value.startswith('-'):
                break
            values.append(value)
        kwargs[argument.dest] = values
        del unused_args[index: index + len(values) + 1]

    elif argument.nargs > 1:
        values = unused_args[index + 1: index + 1 + argument.nargs]
        kwargs[argument.dest] = values
        del unused_args[index: index + 1 + argument.nargs]

    elif argument.flag_value is True:
        kwargs[argument.dest] = argument.flag_value
        del unused_args[index]

    elif argument.nargs == 1:
        try:
            value = unused_args[index + 1].strip()
            kwargs[argument.dest] = value
            del unused_args[index: index + 2]
        except IndexError as e:
            pass

    else:
        raise ValueError(f"Invalid argument: {unused_args[index]}")


def daemon(*args, function=None, as_daemon=False, **kwargs):
    """
    Создает процесс демона

    :param args:
    :param function: Функция для запуска в качестве демона
    :param as_daemon: запускает как демон. Т.е. ждем когда функция закончит выполнения перед остановкой демона
    :param kwargs:
    :return:
    """
    thread = threading.current_thread()
    if callable(function):
        function(thread)

    # print(thread.__dict__)
    # print(thread.daemon)
    # print(thread.isDaemon())
    # set thread as Daemon
    # thread.setDaemon(True)
    # print(thread.isDaemon())
