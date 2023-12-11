import collections
import fnmatch
import os
import os.path
import sys
from enum import Enum


class JackCompiler:
    source_files = []

    allow_argumentless = True  # allows to run the program without any arguments, taking '.' directory by default
    separator = '\n     ---------------------------------------------------\n'

    def main(self):
        self.get_source_files()
        tokenizer = self.Tokenizer()
        symbol_tabler = self.SymbolTable()
        parser = self.Parser()
        print(self.separator)
        for file in self.source_files:
            sourse_lines = self.load_file(file)
            cleaned_lines = self.clean_lines(sourse_lines)
            lexical_lines = tokenizer.do(cleaned_lines)
            self.save_token_file(lexical_lines, file)
            symbol_table_lines = symbol_tabler.do(lexical_lines)
            self.save_symbol_file(symbol_table_lines, file)
            parsed_lines = parser.do(symbol_table_lines)
            self.save_parsed_file(parsed_lines, file)
            print(self.separator)
        print(' *** Успешно завершено ***')

    # input: OR .jack file OR directory with some .jack files
    def get_source_files(self):
        if len(sys.argv) > 1:
            if sys.argv[1].partition('.')[2] == 'jack':
                if os.path.isfile(sys.argv[1]):
                    file = sys.argv[1]
                    path = os.path.dirname(file)
                    if len(path) > 0:
                        os.chdir(path)
                        file = os.path.basename(file)
                    self.source_files.append(file)
                else:
                    print('\n Указано несуществующее имя файла')
                    sys.exit()
            else:
                if os.path.isdir(sys.argv[1]):
                    path = sys.argv[1]
                    if not path.startswith('/') and len(path) > 1 and path[1] != ':':
                        path = os.getcwd() + '\\' + path  # change relative path to absolute
                    os.chdir(path)  # change directory
                    files = os.listdir('.')
                    pattern = "*.jack"
                    for file in files:
                        if fnmatch.fnmatch(file, pattern):
                            self.source_files.append(file)
                    if len(self.source_files) == 0:
                        print('\n В указаной директории не найдено *.jack файлов')
                        sys.exit()
                else:
                    print('\n Указано некорректное имя директории')
                    sys.exit()
        else:
            if self.allow_argumentless:
                files = os.listdir('.')
                pattern = "*.jack"
                for file in files:
                    if fnmatch.fnmatch(file, pattern):
                        self.source_files.append(file)
            else:
                print('\n Необходимо указать файл или директорию для обработки')
                sys.exit()

    def load_file(self, file_name):
        file = open(file_name, "r")
        lines = file.readlines()
        file.close()
        print('       Загружено:', f'{len(lines)} строк(и)'.rjust(13), f'   из файла: {file_name}')
        return lines

    def clean_lines(self, source_lines):
        clean_lines = list()
        for line in source_lines:
            line = self.clean_string(line)
            if len(line) != 0:
                clean_lines.append(line)
        print('       Отброшено:', f'{len(source_lines) - len(clean_lines)} строк(и)'.rjust(13))
        print('        Получено:', f'{len(clean_lines)} строк(и)'.rjust(13))
        return clean_lines

    def clean_string(self, string_in):
        string_out = string_in.replace('\n', '')  # удаляем перевод строки
        string_out = string_out.lstrip()  # удаляем пробелы в начале строки
        string_out = string_out.rstrip()  # удаляем пробелы в конце строки
        string_out = string_out.partition('//')[0]  # отбрасываем все java-like комментарии
        string_out = string_out.partition('/*')[0]
        if string_out.startswith('*'):
            string_out = string_out.partition('*')[0]
        return string_out

    def save_token_file(self, lines_in, file_name):
        file = open((file_name.partition('.')[0] + 'T.xml'), 'w')
        instruction_count = lines_in.count('\n') + 1
        print('    Файл токенов:', f'{instruction_count}'.rjust(4), 'токен(ов)')
        file.write(lines_in)
        file.close()

    def save_symbol_file(self, lines_in, file_name):
        file = open((file_name.partition('.')[0] + 'TS.xml'), 'w')
        instruction_count = lines_in.count('\n') + 1
        print('Таблица символов:', f'{instruction_count}'.rjust(4), 'токен(ов)')
        file.write(lines_in)
        file.close()

    def save_parsed_file(self, lines_in, file_name):
        file_name = file_name.partition('.')[0] + '.vm'
        file = open((file_name), 'w')
        instruction_count = lines_in.count('\n') + 1
        print('           Итого:', f'{instruction_count}'.rjust(4), 'команд(а)', f'   в файле: {file_name}')
        file.write(lines_in)
        file.close()

    class Tokenizer:

        keywords = ('class', 'constructor', 'function', 'method', 'field', 'static', 'var', 'int', 'char', 'boolean',
                    'void', 'true', 'false', 'null', 'this', 'let', 'do', 'if', 'else', 'while', 'return')
        symbols = ('{', '}', '(', ')', '[', ']', '.', ',', ';', '+', '-', '*', '/', '&', '|', '<', '>', '=', '~')
        forbidden_chars = {'<': '&lt;', '>': '&gt;', '"': '&quot;', '&': '&amp;'}

        input_lines = ''
        current_line = ''

        def do(self, lines_in: str) -> str:
            self.input_lines = lines_in
            return self.split_lines(self.input_lines)

        def split_lines(self, lines_in):
            lines_out = ''
            for line in lines_in:
                self.current_line = line
                result = self.process_line()
                if len(result) != 0:
                    lines_out += result
            return '<tokens>\n' + lines_out + '</tokens>\n'

        def process_line(self):
            lines_out = ''
            while len(self.current_line) > 0:
                token = self.get_token()  # gets next token
                self.current_line = self.current_line.lstrip()
                lines_out += token + '\n'
            return lines_out

        def get_token(self):
            for keyword in self.keywords:
                if self.current_line.startswith(keyword):
                    if (len(self.current_line) == len(keyword)
                            or self.current_line[len(keyword)] == ' '
                            or self.current_line[len(keyword)] in self.symbols):
                        self.current_line = self.current_line.partition(keyword)[2]
                        return self.keyword(keyword)
            if self.current_line.startswith(self.symbols):
                symbol = self.current_line[0]
                self.current_line = self.current_line[1:]
                return self.symbol(symbol)
            elif self.current_line[0].isdigit():
                for i in range(1, 6):
                    if (len(self.current_line) == i
                            or not self.current_line[i].isdigit()):
                        int = self.current_line[:i]
                        self.current_line = self.current_line[i:]
                        return self.int_value(int)
            elif self.current_line.startswith('"'):
                id = self.current_line.find('"', 1)
                str = self.current_line[0:(id + 1)]
                self.current_line = self.current_line[id + 1:]
                return self.string_value(str)
            else:
                for i in range(1, len(self.current_line) + 1):
                    if (len(self.current_line) == i
                            or self.current_line[i] == ' '
                            or self.current_line[i] in self.symbols):
                        ident = self.current_line[:i]
                        self.current_line = self.current_line[i:]
                        return self.identifier(ident)

        def keyword(self, token):
            return '<keyword> ' + token + ' </keyword>'

        def symbol(self, token):
            if token in self.forbidden_chars:
                token = self.forbidden_chars.get(token)
            return '<symbol> ' + token + ' </symbol>'

        def identifier(self, token):
            return '<identifier> ' + token + ' </identifier>'

        def int_value(self, token):
            return '<integerConstant> ' + token + ' </integerConstant>'

        def string_value(self, token):
            token = token[1:len(token) - 1]
            for i in range(len(token) - 1, 0, -1):
                if token[i] in self.forbidden_chars:
                    token = token[:i] + self.forbidden_chars.get(token[i]) + token[i + 1:]
            return '<stringConstant> ' + token + ' </stringConstant>'

    class SymbolTable:

        input_lines = ''  # type: str # input from Tokenizer
        subroutines = ''  # type: str # subroutines only part of the class

        class_name = ''  # type: str
        static_index = 0  # type: int
        field_index = 0  # type: int
        class_table = {}  # [name, [kind, type, id]] # уникальная таблица символов для каждого класса

        subroutine_name = ''  # type: str # currently processing subroutine name
        arg_index = 0  # type: int
        local_index = 0  # type: int
        subroutine_table = {}  # [name, [kind, type, id]] # уникальная таблица символов для каждой сабрутины

        class Kind(Enum):
            STATIC = 'static'
            FIELD = 'this'
            ARG = 'argument'
            VAR = 'local'

        def do(self, lines_in: str) -> str:
            self.input_lines = lines_in
            self.input_lines = self.input_lines.split('\n')
            self.input_lines = self.input_lines[1:len(self.input_lines) - 2]  # отбрасываем '<tokens>' и '</tokens>\n'
            self.fill_class_table()
            lines_out = self.process_subroutines()
            return lines_out

        def get_token_body(self, id: int = 0) -> str:
            token = self.input_lines[id]
            return token.partition(' ')[2].partition('<')[0].rstrip()

        def cut_token_body(self, lines_in: str, id: int) -> str:
            token = lines_in[id]
            return token.partition(' ')[2].partition('<')[0].rstrip()

        def cut_token_type(self, lines_in: str, id: int) -> str:
            token = lines_in[id]
            type = token.partition(' ')[0]
            return type[1:len(type) - 1]

        def reset_class(self):
            self.class_table = {}  # обнуляем символьную таблицу класса
            self.class_name = ''
            self.static_index = 0
            self.field_index = 0

        def reset_subroutine(self):
            self.subroutine_table = self.class_table.copy()  # сбрасываем символьную таблицу сабрутины до классовой
            self.subroutine_name = ''
            self.arg_index = 0
            self.local_index = 0

        def assign_index(self, Kind):
            if Kind is self.Kind.STATIC:
                index = self.static_index
                self.static_index += 1
                return index
            elif Kind is self.Kind.FIELD:
                index = self.field_index
                self.field_index += 1
                return index
            elif Kind is self.Kind.ARG:
                index = self.arg_index
                self.arg_index += 1
                return index
            elif Kind is self.Kind.VAR:
                index = self.local_index
                self.local_index += 1
                return index
            print('Wrong usage of assign_index', Kind)
            sys.exit()

        def fill_class_table(self):
            self.reset_class()  # resets name, symbol table and indexes
            self.class_name = self.get_token_body(1)
            for i in range(len(self.input_lines)):
                body = self.get_token_body(i)
                if body in ('static', 'field'):
                    kind = self.Kind.STATIC if body == 'static' else self.Kind.FIELD
                    type = self.get_token_body(i + 1)
                    name = self.get_token_body(i + 2)
                    index = self.assign_index(kind)
                    self.class_table[name] = [kind.value, type, index]
                    n = 3  # static | field, var_type, var_name
                    while not self.get_token_body(i + n) == ';':
                        name = self.get_token_body(i + n + 1)
                        index = self.assign_index(kind)
                        self.class_table[name] = [kind.value, type, index]
                        n += 2  # var_name, ,
                elif body in ('constructor', 'function', 'method', '}'):
                    # отбрасываем объявление класса и классовых переменных, а также закрывающую скобку
                    self.subroutines = self.input_lines[i:len(self.input_lines) - 1]
                    break

        def process_subroutines(self) -> str:
            start_id = 0
            end_id = 0
            lines_out = []
            for i in range(len(self.subroutines)):
                body = self.cut_token_body(self.subroutines, i)
                next_body = self.cut_token_body(self.subroutines, i + 1) if i + 1 != len(self.subroutines) else 'eof'
                if body in ('constructor', 'function', 'method'):
                    start_id = i
                elif next_body in ('constructor', 'function', 'method', 'eof'):
                    end_id = i
                    routine = self.subroutines[start_id:end_id + 1]
                    lines_out += self.handle_subroutine(routine)
            return '\n'.join(lines_out)

        def handle_subroutine(self, lines_in: str) -> str:
            self.reset_subroutine()
            sub_type = self.cut_token_body(lines_in, 0)  # constructor | function | method
            ret_type = self.cut_token_body(lines_in, 1)  # void | int | char | boolean | Class_name
            sub_name = self.class_name + '.' + self.cut_token_body(lines_in, 2)  # rename to: Class_name.name
            lines_out = lines_in.copy()
            if sub_type == 'constructor':
                lines_out[1] = '<identifier> ' + ret_type + ' ' + str(self.field_index) + ' </identifier>'
            lines_out[2] = ('<identifier> ' + self.class_name + ' </identifier>\n'
                            + '<symbol> . </symbol>\n'
                            + lines_out[2])

            def fill_arg_table(params: str) -> None:
                if len(params) > 0 and self.cut_token_body(params, 0) != ')':
                    name = self.cut_token_body(params, 1)
                    type = self.cut_token_body(params, 0)
                    kind = self.Kind.ARG
                    index = self.assign_index(kind)
                    self.subroutine_table[name] = [kind.value, type, index]
                    if len(params) >= 3 and self.cut_token_body(params, 2) == ',':
                        fill_arg_table(params[3:])  # recursion call

            for i in range(4, len(lines_out) - 1):
                if self.cut_token_body(lines_out, i) == ')':
                    if sub_type == 'method':  # special case for methods: first argument is 'this' reference
                        kind = self.Kind.ARG
                        self.subroutine_table['this'] = [kind.value, self.class_name, self.assign_index(kind)]
                    fill_arg_table(lines_out[4:i])  # заполняем символьную таблицу аргументами
                    lines_out[3] = '<integerConstant> ' + str(self.arg_index) + ' </integerConstant>'
                    lines_out = lines_out[:4] + lines_out[i + 1:]  # отбрасываем лист аргументов
                    break

            def fill_lcl_table(locals: str, type: str) -> None:
                if len(locals) > 0 and self.cut_token_body(locals, 0) != ';':
                    name = self.cut_token_body(locals, 0)
                    kind = self.Kind.VAR
                    index = self.assign_index(kind)
                    self.subroutine_table[name] = [kind.value, type, index]
                    if len(locals) >= 3 and self.cut_token_body(locals, 1) == ',':
                        fill_lcl_table(locals[2:], type)  # recursion call

            for i in range(5, len(lines_out) - 1):
                if self.cut_token_body(lines_out, i) == 'var':
                    n = 3  # var, var_type, var_name
                    while self.cut_token_body(lines_out, i + n) != ';':
                        n += 2  # ,, var_name
                    # передаём список (возможно состоящий из 1 записи) переменных для занесения в таблицу символов
                    fill_lcl_table(lines_out[i + 2:i + n + 1], self.cut_token_body(lines_out, i + 1))
                    if self.cut_token_body(lines_out, i + n + 1) != 'var':
                        # print(sub_name, 'variables:', self.local_index, self.subroutine_table)
                        lines_out[5] = '<integerConstant> ' + str(self.local_index) + ' <integerConstant>'
                        lines_out = lines_out[:6] + lines_out[i + n + 1:]
                        break
            # header format: sub_type[0], ret_type[1], sub_name[2 [Class_name, . , name], n_args[3], {[4], n_locals[5]?

            for i in range(6, len(lines_out) - 1):
                type = self.cut_token_type(lines_out, i)
                if type == 'identifier':
                    body = self.cut_token_body(lines_out, i)
                    if body in self.subroutine_table:
                        lines_out[i] = ('<identifier>\n'
                                        + '<name> ' + body + ' </name>\n'
                                        + '<kind> ' + self.subroutine_table[body][0] + ' </kind>\n'
                                        + '<type> ' + self.subroutine_table[body][1] + ' </type>\n'
                                        + '<index> ' + str(self.subroutine_table[body][2]) + ' </index>\n'
                                        + '</identifier>')
                    elif (self.cut_token_body(lines_out, i + 1) != '.'
                          and self.cut_token_body(lines_out, i - 1) != '.'):
                        lines_out[i] = ('<identifier> ___' + self.class_name + ' </identifier>\n'
                                        + '<symbol> . </symbol>\n'
                                        + lines_out[i])
            return lines_out

    class Parser:

        input_lines = ''  # type: str
        class_fields = 0  # type: int

        sub_type = ''  # type: str # type (constructor | method | function) of currently processing subroutine
        ret_type = ''  # type: str # return type of currently processing subroutine
        sub_name = ''  # type: str # name of currently processing subroutine
        sub_args = ''  # type: str
        sub_locals = ''  # type: str

        sub_if_labels = 0  # type: int
        sub_while_labels = 0  # type: int

        called_args = 0  # type: int # holds number of arguments of a last called subroutine

        class Segment(Enum):
            CONST = 'constant'
            ARG = 'argument'
            LOCAL = 'local'
            STATIC = 'static'
            THIS = 'this'
            THAT = 'that'
            POINTER = 'pointer'
            TEMP = 'temp'

        class ACommand(Enum):
            ADD = 'add'
            SUB = 'sub'
            NEG = 'neg'
            EQ = 'eq'
            LT = 'lt'
            GT = 'gt'
            AND = 'and'
            OR = 'or'
            NOT = 'not'

        def do(self, lines_in: str) -> str:
            self.input_lines = lines_in
            self.input_lines = self.input_lines.split('\n')
            self.class_fields = 0
            lines_out = ''
            while len(self.input_lines) > 0 and self.get_token_body() in ('constructor', 'function', 'method'):
                if self.get_token_body() == 'constructor':
                    self.class_fields = self.get_token_body(1).split(' ')[1]
                    self.input_lines[1] = '<identifier> ' + self.get_token_body(1).split(' ')[0] + ' </identifier>'
                lines_out += self.compile_subroutine_declaration()
            return lines_out

        def form_command(self, *parts: str) -> str:
            command = ''
            for i in range(len(parts)):
                part = parts[i]
                if i == len(parts) - 1:
                    command += part + '\n'
                else:
                    command += part + ' '
            return command

        # writes a VM push command
        def write_push(self, segment: Segment, index: int) -> str:
            return self.form_command('push', segment.value, str(index))

        # writes a VM pop command
        def write_pop(self, segment: Segment, index: int) -> str:
            return self.form_command('pop', segment.value, str(index))

        # writes a VM arithmetic-logical command
        def write_arithmetic(self, command: ACommand) -> str:
            return self.form_command(command.value)

        # writes a VM label command
        def write_label(self, label: str) -> str:
            return self.form_command('label', label)

        # writes a VM goto command
        def write_goto(self, label: str) -> str:
            return self.form_command('goto', label)

        # writes a VM if-goto command
        def write_if(self, label: str) -> str:
            return self.form_command('if-goto', label)

        # writes a VM call command
        def write_call(self, name: str, args: int) -> str:
            return self.form_command('call', name, str(args))

        # writes a VM function command
        def write_function(self, name: str, locals: int) -> str:
            return self.form_command('function', name, str(locals))

        # writes a VM return command
        def write_return(self) -> str:
            return self.form_command('return')

        def get_token(self, id=0) -> str:
            return self.input_lines[id]

        def get_token_type(self, id=0) -> str:
            token = self.input_lines[id]
            type = token.partition(' ')[0]
            return type[1:len(type) - 1]

        def get_token_body(self, id=0) -> str:
            token = self.input_lines[id]
            return token.partition(' ')[2].partition('<')[0][:-1]

        def advance(self, n=1) -> None:  # rename to advance
            tokens_out = ''
            for i in range(n):
                tokens_out += self.input_lines[0] + '\n'
                del self.input_lines[0]
            return tokens_out

        # compiles a complete method, function or constructor
        def compile_subroutine_declaration(self) -> str:
            self.sub_if_labels = 0
            self.sub_while_labels = 0
            self.sub_type = self.get_token_body(0)
            self.ret_type = self.get_token_body(1)
            self.sub_name = self.get_token_body(2) + self.get_token_body(3) + self.get_token_body(4)
            self.sub_args = self.get_token_body(5)
            self.sub_locals = self.get_token_body(7) if self.get_token_type(7) == 'integerConstant' else 0
            self.advance(6)  # sub_type, ret_type, sub_class, ., sub_name, n_args
            lines_out = self.write_function(self.sub_name, self.sub_locals)  # function Class_name.name n_locals
            if self.sub_type == 'constructor':
                lines_out += self.write_push(self.Segment.CONST, self.class_fields)  # пушим количество полей в стэк
                lines_out += self.write_call('Memory.alloc', 1)  # выделяем память, возвращая указатель
                lines_out += self.write_pop(self.Segment.POINTER, 0)  # устанавливаем THIS = полученному указателю
            elif self.sub_type == 'method':
                lines_out += self.write_push(self.Segment.ARG, 0)  # считываем указатель на объект = THIS
                lines_out += self.write_pop(self.Segment.POINTER, 0)  # присваемаем THIS значение указателя
            lines_out += self.compile_subroutine_body()
            return lines_out

        # compiles a subroutine's body
        def compile_subroutine_body(self) -> str:
            lines_out = ''
            self.advance()  # {
            if self.get_token_type() == 'integerConstant':
                self.advance()  # n_locals
            lines_out += self.compile_statements()
            self.advance()  # }
            return lines_out

        # compiles a sequence of statements, does NOT handle enclosing '{}'
        def compile_statements(self) -> str:
            lines_out = ''
            while self.get_token_body() in ('let', 'if', 'while', 'do', 'return'):
                statement_type = self.get_token_body()
                if statement_type == 'let':
                    lines_out += self.compile_let()
                elif statement_type == 'if':
                    lines_out += self.compile_if()
                elif statement_type == 'while':
                    lines_out += self.compile_while()
                elif statement_type == 'do':
                    lines_out += self.compile_do()
                elif statement_type == 'return':
                    lines_out += self.compile_return()
            return lines_out

        def get_kind(self, kind_in: str) -> Segment:
            for kind in self.Segment:
                if kind_in == kind.value:
                    return kind
            print('failed getting kind of:', kind_in)

        x_case = False
        x_index = 0 # type: int

        def process_identifier(self, push=True):  # True = push; False = pop
            lines_out = ''
            if self.get_token() == '<identifier>':
                self.advance()  # <identifier>
                name = self.get_token_body(0)
                kind = self.get_kind(self.get_token_body(1))
                type = self.get_token_body(2)
                index = self.get_token_body(3)
                self.advance(5)  # name, kind, type, index, </identifier>
                if self.get_token_body() == '.':
                    name = type + self.get_token_body(0) + self.get_token_body(1)
                    self.x_case = True
                    self.x_index = index
                    self.advance(2)  # . , sub_name
                    lines_out += name
                else:
                    lines_out += self.write_push(kind, index) if push else self.write_pop(kind, index)
            elif self.get_token_type() == 'integerConstant':
                pop_out = self.write_pop(self.Segment.CONST, self.get_token_body())
                push_out = self.write_push(self.Segment.CONST, self.get_token_body())
                self.advance()  # integerConstant
                lines_out += push_out if push else pop_out
            elif self.get_token_type() == 'stringConstant':
                string = self.get_token_body()
                lines_out += self.write_push(self.Segment.CONST, len(string))
                lines_out += self.write_call('String.new', 1)
                for c in string:
                    lines_out += self.write_push(self.Segment.CONST, ord(c))
                    lines_out += self.write_call('String.appendChar', 2)
                self.advance() # stringConstant
            elif self.get_token_type() == 'identifier':  # self.get_token_body(1) == '.':
                full_name = self.get_token_body(0) + self.get_token_body(1) + self.get_token_body(2)
                self.advance(3)  # Class_name, . , name
                lines_out += full_name
            else:
                body = self.get_token_body()
                if body in ('true', 'false', 'null'):
                    lines_out += self.write_push(self.Segment.CONST, 0)
                    if body == 'true':
                        lines_out += self.write_arithmetic(self.ACommand.NOT)
                    self.advance()  # true | false | null const
                elif body == 'this':
                    lines_out += self.write_push(self.Segment.POINTER, 0)
                    self.advance()  # this
                else:
                    print('WE ARE HERE!', self.get_token(), self.input_lines)
                    sys.exit()
                    lines_out += self.advance()
            return lines_out

        # compiles a let statement
        def compile_let(self) -> str:
            self.advance()  # let
            let_before = ''
            let_to = self.process_identifier(False)
            if self.get_token_type(0) == 'symbol' and self.get_token_body(0) == '[':
                self.advance()  # [
                let_before += self.compile_expression() # array offset
                self.advance()  # ]
                let_before += 'push ' + let_to.partition(' ')[2]  # base array address
                let_before += self.write_arithmetic(self.ACommand.ADD) # array offset address
                self.advance()  # =
                let_from = self.compile_expression() # вычисляем присваемое значение
                let_from += self.write_pop(self.Segment.TEMP, 0) # сохраняем присваемое значение в TEMP 0
                self.advance()  # ;
                let_to = self.write_pop(self.Segment.POINTER, 1) # присваиваем THAT вычисленный ранее адрес
                let_to += self.write_push(self.Segment.TEMP, 0) # забираем из TEMP 0 присваемое значение
                let_to += self.write_pop(self.Segment.THAT, 0) # и пушим его в array offset address
            else:
                self.advance()  # =
                let_from = self.compile_expression()
                self.advance()  # ;
                if self.x_case:
                    self.x_case = False
                    let_from = self.write_call(let_from, 1) # количество аргументов?
                    let_from = self.write_push(self.Segment.THIS, self.x_index) + let_from
            return let_before + let_from + let_to

        def add_case_body(self) -> str:
            self.advance()  # {
            lines_out = self.compile_statements()
            self.advance()  # }
            return lines_out

        # compiles an if statement, possible with trailing else clause
        def compile_if(self) -> str:
            lines_out = ''
            if_true = 'IF_TRUE' + str(self.sub_if_labels)
            if_false = 'IF_FALSE' + str(self.sub_if_labels)
            if_end = 'IF_END' + str(self.sub_if_labels)
            self.sub_if_labels += 1
            self.advance(2)  # if, (
            lines_out += self.compile_expression()  # if condition
            self.advance()  # )
            lines_out += self.write_if(if_true)
            lines_out += self.write_goto(if_false)
            lines_out += self.write_label(if_true)
            lines_out += self.add_case_body()  # { if statements }
            if self.get_token_body() == 'else':
                self.advance()  # else
                lines_out += self.write_goto(if_end)
                lines_out += self.write_label(if_false)
                lines_out += self.add_case_body()  # { else statements }
                lines_out += self.write_label(if_end)
            else:
                lines_out += self.write_label(if_false)
            return lines_out

        # compiles a while statement
        def compile_while(self) -> str:
            lines_out = ''
            while_exp_label = 'WHILE_EXP' + str(self.sub_while_labels)
            while_end_label = 'WHILE_END' + str(self.sub_while_labels)
            self.sub_while_labels += 1
            self.advance(2)  # while, (
            lines_out += self.write_label(while_exp_label)
            lines_out += self.compile_expression()  # while condition
            lines_out += self.write_arithmetic(self.ACommand.NOT)  # while ~(condition)
            lines_out += self.write_if(while_end_label)
            self.advance()  # )
            lines_out += self.add_case_body()  # { statements }
            lines_out += self.write_goto(while_exp_label)
            lines_out += self.write_label(while_end_label)
            return lines_out

        # compiles a do statement
        def compile_do(self) -> str:
            lines_out = ''
            self.advance()  # do
            full_name = self.process_identifier()  # + self.get_token_body(1) + self.get_token_body(2)
            lines_out += self.compile_expression_list()  # ( expression(s) )
            if full_name.startswith('___'): # ___ - сигнатура локального _метода_
                full_name = full_name.partition('___')[2]
                lines_out = self.write_push(self.Segment.POINTER, 0) + lines_out # push THIS for local methods
                self.called_args += 1
            elif self.x_case:
                self.x_case = False
                segment = self.Segment.LOCAL if self.sub_type == 'function' else self.Segment.THIS
                lines_out = self.write_push(segment, self.x_index) + lines_out
                self.called_args += 1
            lines_out += self.write_call(full_name, self.called_args)  # call functions with n arguments
            lines_out += self.write_pop(self.Segment.TEMP, 0)  # dump the returning value
            self.advance()  # ;
            return lines_out

        # compiles a return statement
        def compile_return(self) -> str:
            lines_out = ''
            if self.ret_type == 'void':
                lines_out += self.write_push(self.Segment.CONST, 0)  # returns 0 from void function / method
            self.advance()  # return
            if self.get_token_body() != ';':
                lines_out += self.compile_expression()
            self.advance()  # ;
            lines_out += self.write_return()
            return lines_out

        # compiles an expression
        def compile_expression(self) -> str:
            lines_out = ''
            op_queue = collections.deque()  # queue of operators, calls at the end of the expression, Last In First Out
            lines_out += self.compile_term()
            if self.get_token_body() == ('('):
                lines_out = self.compile_expression_list() + lines_out
            if self.get_token_body() == ('['):
                lines_out = self.compile_term() + lines_out # push [ expression ] , push arr *name
                lines_out += self.write_arithmetic(self.ACommand.ADD) # calculate array offset address
                lines_out += self.write_pop(self.Segment.POINTER, 1) # points THAT to the array offset
                lines_out += self.write_push(self.Segment.THAT, 0) # push THAT 0 to the stack
            if self.get_token_body() in ('+', '-', '*', '/', '&amp;', '|', '&lt;', '&gt;', '='):
                op = self.get_token_body()
                op_type = ''
                if op == '+':
                    op_type = self.ACommand.ADD
                elif op == '-':
                    op_type = self.ACommand.SUB
                elif op == '*':
                    op_queue.append(self.write_call('Math.multiply', 2))
                elif op == '/':
                    op_queue.append(self.write_call('Math.divide', 2))
                elif op == '&amp;':
                    op_type = self.ACommand.AND
                elif op == '|':
                    op_type = self.ACommand.OR
                elif op == '&lt;':
                    op_type = self.ACommand.LT
                elif op == '&gt;':
                    op_type = self.ACommand.GT
                elif op == '=':
                    op_type = self.ACommand.EQ
                if op_type != '':
                    op_queue.append(self.write_arithmetic(op_type))
                self.advance()  # operator
                lines_out += self.compile_expression()
            for i in range(len(op_queue)):
                lines_out += op_queue.pop()
            return lines_out

        def compile_term(self) -> str:
            lines_out = ''
            if self.get_token_type() == 'symbol' and self.get_token_body() in ('-', '~'):
                op = self.write_arithmetic(self.ACommand.NEG if self.get_token_body() == '-' else self.ACommand.NOT)
                self.advance()  # - / ~
                return self.compile_expression() + op
            if self.get_token_type() == 'symbol' and self.get_token_body() in ('(', '['):
                self.advance()  # open bracket
                lines_out += self.compile_expression()
                self.advance()  # closed bracket
                return lines_out
            if self.get_token_type(1) == 'symbol' and self.get_token_body(1) == '.':
                full_name = self.process_identifier()
                lines_out += self.compile_expression_list()  # ( expression(s) )
                lines_out += self.write_call(full_name, self.called_args)
                return lines_out
            lines_out += self.process_identifier()  # terminal constant (int, str or keyword)
            return lines_out

        # compiles a (possible empty) comma-separated list of expressions
        def compile_expression_list(self) -> str:
            self.called_args = 0
            lines_out = ''
            self.advance()  # (
            while self.get_token_body() != ')':
                if self.called_args == 0:
                    self.called_args = 1
                lines_out += self.compile_expression()
                if self.get_token_body() == ',':
                    self.called_args += 1
                    self.advance()  # ,
            self.advance()  # )
            return lines_out


if __name__ == '__main__':
    compiler = JackCompiler()
    compiler.main()
