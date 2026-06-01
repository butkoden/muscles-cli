# CLI

## Принцип обработки команд/запросов


1. Вызов команды инстанса основанного из метакласса `ApplicationMeta` и контекста `Context`
2. Запуск команды `execute` с передачей параметров. `self.context.execute(<params>)`
3. Передача управления в текущую стратегию, основанную на `BaseStrategy` в метод `execute` с передачей всех параметров
4. Вызов метода `cli.execute(*args)` с передачей всех параметров запроса
5. В классе `Group` обрабатываем аргументы команды, определяя последовательность вызова ее точек и вызываем `command.execute`
6. В классе `Command` вызываем обработчик команды 
7. Обработчик обрабатывает запрос, и формирует результат обработки, который затем перенаправляется в точку вызова.


Для работы из консоли существует эта надстройка. Она позволяет добавлять команды в консоль и вызвать их по требованию.

ВАЖНО: Для одной точки входа существует только одно пространство команд. Это значит что в каком бы месте не находилось
описание команд, оно будет добавленною к общему списку, поэтому следите за именами своих команд и не позволяйте им 
дублироваться



## Общее описание


Консольные команды делятся на команды и группы. Группа объединяет набор команд, изолирую пространство имен.

`from muscles import cli` - импортирует инстанс пространства консольных команд

`@cli.group()` - Декоратор для создания группы команд, вешается на функцию. Если функция содержит описание в __doc__ оно
будет использовано как описание группы, иначе можно поместить описание в атрибут description 
`@cli.group(description='Описание')`. Бывают случае когда нужно вложить одну группу в другую, для этого родительская 
группа наследуется от @cli.group, а остальные от `@<НазваниеРодительскойФункцииКотораяОпределяетГруппу>.group`. Вызов 
таких команд осуществляется так же в иерархии `script.py main_group second_group command`. Имя команды может быть взято 
по имени функции, либо определенно атрибутом `command_name`. Имейте ввиду имя команды не должно содержать пробелов и 
специальных символов.


#### Пример
```python
from muscles import ApplicationMeta
from muscles import Context
from muscles import Console
from muscles import cli
from muscles import CliStrategy


class TestApp(metaclass=ApplicationMeta):
    context = Context(CliStrategy)

    console = Console()

    def run(self, *args):
        return self.context.execute(*args, shutup=True)

m = TestApp()

@cli.group()
def user(*args):
    """test_0_0"""
    return 'Group User Control'

@user.group()
def group(*args):
    """test_0_1"""
    return 'Group User/Group Control'

@user.group()
def roles(*args):
    """test_0_2"""
    return 'Group User/Roles Control'

@roles.group(command_name='delete')
def drop(*args):
    """test_0_2"""
    return 'Group User/Roles/Delete'


# RUN 1: this_script.py user group
# RUN 2: this_script.py user roles
# RUN 3: this_script.py user roles delete / имя команды определенно атрибутом command_name=delete
```


`@cli.command()` - определяет команду. Команды имеют больше возможностей чем группы, поэтому для определения 
функциональных команд консоли рекомендуем использовать этот декоратор. Если функция, которую определяет декоратор, 
содержит описание в __doc__ оно будет использовано как описание команды, иначе можно поместить описание в атрибут description 
`@cli.command(description='Описание')`. Имя команды может быть взято по имени функции, либо определенно атрибутом 
`command_name`. Имейте в виду имя команды не должно содержать пробелов и специальных символов. Для уточнения возможных 
аргументов команды применяется описывающий их декоратор `@cli.argument`.

`@cli.argument(<argument>)` - Описывает атрибуты команды:

- `<argument>` - имя аргумента, всегда начинается с `--`.
- `short` - короткий аргумент, всегда начихается с одной `-` (по умолчанию = `None`).
- `description` - описание аргумента (по умолчанию = `''`).
- `required` - если `True` то отмечает аргумент как обязательный. Его отсутствие вызовет ошибку (по умолчанию = `False`).
- `default` - значение по умолчанию, если указано то в случае отсутствия аргумента подставит именно его и так же не 
будет учитываться `required` (по умолчанию = None).
- `multiple` - если `True` то аргумент может содержать несколько значений подряд, в этом случае они будет объеденины в 
массив (по умолчанию = `False`). 
Такая команда выглядит так `this_script.py command --arg val1 val2 ... valN --nextArg ...`.
- `flag_value` - значение `True`, указывает на то что атрибут представляет собой булево значение. Т.е его наличие укажет 
на True, а отсутствие в команде на `False` (по умолчанию = `False`).
- `dest` - по умолчанию значение атрибута из консоли попадает в инстанс с имением равным `argument`, но без `--` в начале. 
Этот атрибут позволяет указать другое имя назначения для атрибута (по умолчанию = `None`).
- `nargs` - указывает на кол-во элементов, которые должны обязательно присутствовать в атрибуте. 
(по умолчанию = `0`, но если указан атрибут `required` становиться равным `1`)
- `prompt` - работает совместно с атрибутом `required=True`, позволяет избежать появления ошибки выдавая приглашения 
ввести требуемое значение. Если указана строка, то эта строка будет использована как приглашение к вводу 
(по умолчанию = `None`).
- `hide` - если указана в True, то позволяет подавить введенное значение так что бы оно не осталось в истории. 
- Полезно применять для ввода таких значений как пароль (по умолчанию = `False`).

### Nested commands: canonical options binding

Для вложенных команд опции нужно вешать на объект родительской группы/роута, а не на корневой `@cli`:

```python
@cli.group(command_name='bookings')
def bookings(*args):
    return True

@bookings.command(command_name='list')
@bookings.argument('--limit', nargs=1, default='25')
def bookings_list(*args, limit):
    return limit
```

Каноничные варианты вызова для benchmark/automation:

```bash
bookings list --limit 10
bookings list --limit=10
```


#### Пример
```python
import sys
from muscles import ApplicationMeta
from muscles import Context
from muscles import Console
from muscles import cli
from muscles import CliStrategy


class TestApp(metaclass=ApplicationMeta):
    context = Context(CliStrategy)

    console = Console()

    def run(self, *args):
        return self.context.execute(*args, shutup=True)

m = TestApp()

@cli.group()
def user(*args):
    """test_0_0"""
    return 'Group User Control'

@user.command(command_name='test_0_1')
@user.argument('--name', short='-n', required=True, description='User Name',
               prompt='Send User Name')
@user.argument('--password', short='-p', required=True, description='Password',
               prompt='Send Password', hide=True)
def add(*args, name, password):
    
    # Код для добавления пользователя
    
    return name, password

```


`cli.flag()` - то же самое что и `@cli.argument(<argument>, flag_value=True)`. Просто сокращенная версия. 
Позволяет указать что атрибут это флаг `True`/`False`

### Пример
```python
@cli.command(command_name='test_2_1')
@cli.flag('--arg21', short='-a21', description='Argument 21')
@cli.flag('--arg22', short='-a22', description='Argument 22')
@cli.flag('--arg23', short='-a23', description='Argument 23')
def test_2_1(*args, arg21, arg22, arg23):
    return arg21, arg22, arg23

result = m.run('test_2_1', '--arg21', '--arg22', '--arg23')
assert result == (True, True, True)

result = m.run('test_2_1', '--arg21', '--arg23')
assert result == (True, False, True)
```


### Пример @cli.argument(required=True, prompt="Text")
```python
@cli.command(command_name='test_3_1')
@cli.argument('--arg31', short='-a31', description='Argument 31', required=True, prompt="Enter text")
def test_3_1(*args, arg31):
    return arg31

# this_script.py test_3_1 --arg31
#> Enter text:

```


`this_script.py help` - введенное в косноли показывает все группы команд и команды в этом пространстве
`this_script.py <command_group> help` - введенное в косноли показывает все группы команд и команды в выбранной подгруппе
