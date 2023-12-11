import fnmatch
import os
import os.path
import sys


class JackCompiler:
    source_files = []

    allow_argumentless = True  # allows to run the program without any arguments, taking '.' directory by default
    separator = '\n     ---------------------------------------------------\n'

    def main(self):
        self.get_source_files()
        tokenizer = self.Tokenizer()
        parser = self.Parser()
        print(self.separator)
        for file in self.source_files:
            sourse_lines = self.load_file(file)
            cleaned_lines = self.clean_lines(sourse_lines)
            lexical_lines = tokenizer.do(cleaned_lines)
            self.save_token_file(lexical_lines, file)
            parsed_lines = parser.do(lexical_lines)
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
        string_out = string_out.partition('//')[0]  # отбрасываем все java-like комментарии
        string_out = string_out.partition('/*')[0]
        if string_out.startswith(' *'):
            string_out = string_out.partition(' *')[0]
        string_out = string_out.lstrip()  # удаляем пробелы в начале строки
        string_out = string_out.rstrip()  # удаляем пробелы в конце строки
        return string_out

    def save_token_file(self, lines_in, file_name):
        file = open((file_name.partition('.')[0] + 'T.xml'), 'w')
        instruction_count = lines_in.count('\n') + 1
        print('    Файл токенов:', f'{instruction_count}'.rjust(4), 'токен(ов)')
        file.write(lines_in)
        file.close()

    def save_parsed_file(self, lines_in, file_name):
        file = open((file_name.partition('.')[0] + '.xml'), 'w')
        instruction_count = lines_in.count('\n') + 1
        print('   Файл парсинга:', f'{instruction_count}'.rjust(4), 'токен(ов)')
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
            print('\nSomething went wrong:', self.current_line)
            sys.exit()

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

    class Parser:

        input_lines = ''  # type: str
        indent = 0  # type: int

        def do(self, lines_in):
            self.input_lines = lines_in
            return self.parse_lines()

        def parse_lines(self):
            self.input_lines = self.input_lines.split('\n')
            self.clean_input()
            if self.input_lines[0] == '<keyword> class </keyword>':
                lines_out = self.add_open_token('<class>')
                lines_out += self.compile_class()
                lines_out += self.add_close_token('</class>')
                return lines_out
            print('Unsupported file format. Expected <class> declaration')
            sys.exit()

        def clean_input(self):
            if self.input_lines[0] == '<tokens>':
                del self.input_lines[0]
            if self.input_lines[len(self.input_lines) - 1] == '':
                del self.input_lines[len(self.input_lines) - 1]
            if self.input_lines[len(self.input_lines) - 1] == '</tokens>':
                del self.input_lines[len(self.input_lines) - 1]

        def add_open_token(self, line_in) -> str:
            token = ' ' * self.indent + line_in + '\n'
            self.indent += 2
            return token

        def add_close_token(self, line_in) -> str:
            self.indent -= 2
            return ' ' * self.indent + line_in + '\n'

        def get_token(self, id=0) -> str:
            return self.input_lines[id]

        def get_token_type(self, id=0) -> str:
            token = self.input_lines[id]
            type = token.partition(' ')[0]
            return type[1:len(type) - 1]

        def get_token_body(self, id=0) -> str:
            token = self.input_lines[id]
            return token.partition(' ')[2].partition('<')[0].rstrip()

        def use_token(self, n=1) -> str:
            tokens_out = ''
            for i in range(n):
                tokens_out += ' ' * self.indent + self.input_lines[0] + '\n'
                del self.input_lines[0]
            return tokens_out

        # compiles complete class
        def compile_class(self) -> str:
            lines_out = self.use_token(3)  # class, class_name, {
            if not self.get_token() == '<symbol> } </symbol>':
                while self.get_token_body() in ('static', 'field'):
                    lines_out += self.add_open_token('<classVarDec>')
                    lines_out += self.compile_class_variables()
                    lines_out += self.add_close_token('</classVarDec>')
                while self.get_token_body() in ('constructor', 'function', 'method'):
                    lines_out += self.add_open_token('<subroutineDec>')
                    lines_out += self.compile_subroutine_declaration()
                    lines_out += self.add_close_token('</subroutineDec>')
                lines_out += self.use_token()  # }
            else:
                lines_out += self.use_token()  # } - empty class
            return lines_out

        # compiles static valiable declarations and field variable declarations
        def compile_class_variables(self) -> str:
            lines_out = self.use_token(3)  # static | field, var_type, var_name
            while not self.get_token() == '<symbol> ; </symbol>':
                lines_out += self.use_token(2)  # ,,var_name
            lines_out += self.use_token()  # ;
            return lines_out

        # compiles a complete method, function or constructor
        def compile_subroutine_declaration(self) -> str:
            lines_out = self.use_token(4)  # subroutine_type, return_type, subroutine_name, (
            lines_out += self.add_open_token('<parameterList>')
            lines_out += self.compile_parameters()
            lines_out += self.add_close_token('</parameterList>')
            lines_out += self.use_token()  # )
            lines_out += self.add_open_token('<subroutineBody>')
            lines_out += self.compile_subroutine_body()
            lines_out += self.add_close_token('</subroutineBody>')
            return lines_out

        # compiles a (possible empty) paramener list, does NOT handle enclosing '()'
        def compile_parameters(self) -> str:
            if self.get_token_type() == 'keyword' and self.get_token_body() in ('int', 'char', 'boolean'):
                lines_out = self.use_token(2)  # parameter_type, parameter_name
                if self.get_token_body() == ',':
                    lines_out += self.use_token()  # ,
                    return lines_out + self.compile_parameters()  # resursion call
                return lines_out
            else:
                return ''  # empty param_list

        # compiles a subroutine's body
        def compile_subroutine_body(self) -> str:
            lines_out = self.use_token()  # {
            while self.get_token() == '<keyword> var </keyword>':
                lines_out += self.add_open_token('<varDec>')
                lines_out += self.compile_variables()
                lines_out += self.add_close_token('</varDec>')
            lines_out += self.add_open_token('<statements>')
            lines_out += self.compile_statements()
            lines_out += self.add_close_token('</statements>')
            lines_out += self.use_token()  # }
            return lines_out

        # compiles a variable declaration
        def compile_variables(self) -> str:
            lines_out = ''
            if self.get_token() == '<keyword> var </keyword>':
                lines_out += self.use_token(2)  # var, var_type
            lines_out += self.use_token()  # var_name
            if self.get_token_body() == ',':
                lines_out += self.use_token()  # ,
                return lines_out + self.compile_variables()  # resursion call
            lines_out += self.use_token()  # ;
            return lines_out

        # compiles a sequence of statements, does NOT handle enclosing '{}'
        def compile_statements(self) -> str:
            lines_out = ''
            while self.get_token_body() in ('let', 'if', 'while', 'do', 'return'):
                statement_type = self.get_token_body()
                lines_out += self.add_open_token('<' + statement_type + 'Statement>')
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
                lines_out += self.add_close_token('</' + statement_type + 'Statement>')
            return lines_out

        # compiles a let statement
        def compile_let(self) -> str:
            lines_out = self.use_token(2)  # let, var_name
            if self.get_token_type() == 'symbol' and self.get_token_body() == '[':
                lines_out += self.use_token()  # [
                lines_out += self.add_expression()
                lines_out += self.use_token()  # ]
            lines_out += self.use_token()  # =
            lines_out += self.add_expression()
            lines_out += self.use_token()  # ;
            return lines_out

        def add_expression(self) -> str:
            lines_out = self.add_open_token('<expression>')
            lines_out += self.compile_expression()
            lines_out += self.add_close_token('</expression>')
            return lines_out

        def add_case_body(self) -> str:
            lines_out = self.use_token()  # {
            lines_out += self.add_open_token('<statements>')
            lines_out += self.compile_statements()
            lines_out += self.add_close_token('</statements>')
            lines_out += self.use_token()  # }
            return lines_out

        # compiles an if statement, possible with trailing else clause
        def compile_if(self) -> str:
            lines_out = self.use_token(2)  # if, (
            lines_out += self.add_expression()
            lines_out += self.use_token()  # )
            lines_out += self.add_case_body()  # { statements }
            if self.get_token() == '<keyword> else </keyword>':
                lines_out += self.use_token()  # else
                lines_out += self.add_case_body()  # { statements }
            return lines_out

        # compiles a while statement
        def compile_while(self) -> str:
            lines_out = self.use_token(2)  # while, (
            lines_out += self.add_expression()
            lines_out += self.use_token()  # )
            lines_out += self.add_case_body()  # { statements }
            return lines_out

        # compiles a do statement
        def compile_do(self) -> str:
            lines_out = self.use_token()  # do
            lines_out += self.use_token()  # subroutine_name | class_name | var_name
            if self.get_token_body() == '.':
                lines_out += self.use_token(2)  # ., subroutine_name
            lines_out += self.compile_expression_list()  # ( expression(s) )
            lines_out += self.use_token()  # ;
            return lines_out

        # compiles a return statement
        def compile_return(self) -> str:
            lines_out = self.use_token()  # return
            if self.get_token_body() != ';':
                lines_out += self.add_expression()
            lines_out += self.use_token()  # ;
            return lines_out

        # compiles an expression
        def compile_expression(self) -> str:
            lines_out = self.add_open_token('<term>')
            lines_out += self.compile_term()
            lines_out += self.add_close_token('</term>')
            if self.get_token_body() in ('+', '-', '*', '/', '&amp;', '|', '&lt;', '&gt;', '='):
                lines_out += self.use_token()  # operator
                lines_out += self.compile_expression()
            return lines_out

        def compile_term(self) -> str:
            lines_out = ''
            if self.get_token_type() == 'symbol' and self.get_token_body() in ('-', '~'):
                lines_out += self.use_token()  # unary operator
                return lines_out + self.compile_expression()
            if self.get_token_type(1) == 'symbol' and self.get_token_body(1) == '[':
                lines_out += self.use_token()  # var_name
            if self.get_token_type() == 'symbol' and self.get_token_body() in ('(', '['):
                lines_out += self.use_token()  # open bracket
                lines_out += self.add_expression()
                lines_out += self.use_token()  # closed bracket
                return lines_out
            if self.get_token_type(1) == 'symbol' and self.get_token_body(1) == '.':
                lines_out += self.use_token()  # subroutine_name | class_name | var_name
                if self.get_token_body() == '.':
                    lines_out += self.use_token(2)  # ., subroutine_name
                lines_out += self.compile_expression_list()  # ( expression(s) )
                return lines_out
            lines_out += self.use_token()  # terminal constant (int, str or keyword)
            return lines_out

        # compiles a (possible empty) comma-separated list of expressions
        def compile_expression_list(self) -> str:
            lines_out = self.use_token()  # (
            lines_out += self.add_open_token('<expressionList>')
            while self.get_token_body() != ')':
                lines_out += self.add_open_token('<expression>')
                lines_out += self.compile_expression()
                lines_out += self.add_close_token('</expression>')
                if self.get_token_body() == ',':
                    lines_out += self.use_token()  # ,
            lines_out += self.add_close_token('</expressionList>')
            lines_out += self.use_token()  # )
            return lines_out

    class CodeGenerator:
        pass  # next module


if __name__ == '__main__':
    compiler = JackCompiler()
    compiler.main()
