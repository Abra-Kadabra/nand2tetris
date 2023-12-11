import os.path
import sys
from collections import deque

source_file = 'SimpleFunction.vm'
output_file = 'Sys.asm'

add_bootstrap = False  # shows if we are processing the directory (if True) or the file (if False)
add_debug_info = True  # adds comments to the output .asm file, contains executed vm command and its source
console_debug = True  # adds console output, contains full stack state for each vm command

if len(sys.argv) > 1:
    if sys.argv[1].partition('.')[2] == 'vm':
        if os.path.isfile(sys.argv[1]):
            file = sys.argv[1]
            path = os.path.dirname(file)
            if len(path) > 0:
                os.chdir(path)
                file = os.path.basename(file)
            source_file = file
            output_file = source_file.partition('.')[0] + '.asm'
        else:
            print('\n Указано несуществующее имя файла')
            sys.exit()
    else:
        if os.path.isdir(sys.argv[1]):
            path = sys.argv[1]
            if not path.startswith('/') and len(path) > 1 and path[1] != ':':
                path = os.getcwd() + '\\' + path  # change relative path to absolute
            os.chdir(path)  # change directory
            if os.path.isfile('Sys.vm'):
                add_bootstrap = True
                source_file = 'Sys.vm'
                output_file = os.path.basename(os.path.normpath(os.getcwd())) + '.asm'
            else:
                print('\n В указанной директории нет файла Sys.vm')
                sys.exit()
        else:
            print('\n Указано некорректное имя директории')
            sys.exit()
else:
    output_file = source_file.partition('.')[0] + '.asm'

files_parsed = set()  # set of already parsed files
static_offset = 16  # the first available static offset
static_offsets = dict()  # ['Sys', 16] [Class_name, class_static_offset]
func_stack = deque()  # ['Sys.init', 0, 0] [Class.function, current_instruction_number, called_subfuctions_counter]
func_translated = set()  # set of already translated functions, uses to avoid bloating of the asm file


def main():
    if add_bootstrap == False:
        print('\n   Входящий файл: ' + source_file
              + '\n  Исходящий файл: ' + output_file + '\n')
        vm_lines = clean_source(load_file(source_file))
        if vm_lines[0].startswith('function '):  # если имя функции прямо указано, стартуем с неё
            # а почему стартуем с первой встреченой функции, а не пытаемся найти сначала init(), потом main() ?
            # потому что гладиолус. этот кусок кода будет выкинут после прохождения тестов, вот почему не паримся
            func_name = vm_lines[0].partition(' ')[2].partition(' ')[0]
            vm_lines = load_func(func_name, True)
        else:
            # в случае когда в файле только тело функции без его объявления, задаём имя функции по умолчанию = main
            func_name = source_file.partition('.')[0] + '.main'
            # для совместимости с более сложными программами добавляем нашу виртуальную (не объявленную) функцию в стэк
            func_stack.append([func_name, 0, 0])
        output_lines = translate_to_asm(vm_lines)
    else:
        print('\n      Директория: ' + os.getcwd() + '\\'
              + '\n  Исходящий файл: ' + output_file + '\n')
        func_name = 'Bootstrap'
        func_stack.append([func_name, 0, 0])
        # инициализируем поинтеры сегментов (все кроме SP заведомо недопустимыми значениями, для отладки)
        # и запускаем нашу виртуальную функцию Bootstrap, единственная задача которой - запустить Sys.init()
        output_lines = setting_pointers() + translate_to_asm(bootstrap())
    save_output(output_lines)
    print('\n *** Успешно завершено ***')
    sys.exit()


def setting_pointers():
    return form_asm(
        '// Setting up default segment pointers',
        '@256', 'D=A', '@SP', 'M=D',  # setting *SP=256
        '@1', 'D=-A', '@LCL', 'M=D',  # setting *LCL=-1
        '@2', 'D=-A', '@ARG', 'M=D',  # setting *ARG=-2
        '@3', 'D=-A', '@THIS', 'M=D',  # setting *THIS=-3
        '@4', 'D=-A', '@THAT', 'M=D\n')  # setting *THAT=-4


def bootstrap():
    return ('function Bootstrap 0',
            'call Sys.init 0')


def load_func(full_name, silently=False):
    file = full_name.split('.')[0]
    file_lines = load_file(file + '.vm', silently)
    func_stack.append([full_name, 0, 0])  # [Class.function, current_instruction_number, called_subfuctions_counter]
    func_translated.add(full_name)
    return cut_func(file_lines, full_name)


def update_stack(curr_line):
    curr_state = func_stack.pop()
    curr_state[1] = curr_line
    func_stack.append(curr_state)
    if console_debug:
        print(str(func_stack).partition('([')[2].partition('])')[0])


def update_stack_ret(ret_counter, callee_name):
    curr_state = func_stack.pop()
    curr_state[2] = ret_counter
    func_stack.append(curr_state)
    if console_debug:
        print(str(func_stack).partition('([')[2].partition('])')[0] + ' -> calling ' + callee_name + separator)


def load_file(file_name, silently=False):
    file = open(file_name, "r")
    lines = file.readlines()
    file.close()
    if not silently: print('       Загружено:', f'{len(lines)} строк(и)'.rjust(12), f'   из файла: {file_name}')
    if file_name not in files_parsed:
        parse_statics(file_name.partition('.')[0], lines)
        files_parsed.add(file_name)
    return lines


def parse_statics(file_name, file_lines):
    max_static = 0
    for line in file_lines:
        if line.startswith('push static ') or line.startswith('pop static '):
            n = int(line.partition(' static ')[2]) + 1
            if n > max_static:
                max_static = n
    if max_static > 0:
        global static_offset
        static_offsets[file_name] = static_offset
        static_offset += max_static
        print('      Обнаружено:', f'{max_static} статик(ов)'.rjust(14), f' смещение: {static_offsets[file_name]}')


def cut_func(file_lines, func_name):
    func_lines = list()
    do_cut = False
    for line in file_lines:
        if line.startswith('function '):
            if len(func_lines) != 0:
                break
            elif line.startswith('function ' + func_name + ' '):
                do_cut = True
        if do_cut:
            line = clean_string(line)
            if len(line) != 0:
                func_lines.append(line)
    print('        Вырезано:', f'{str(len(func_lines))} строк(и)'.rjust(12), f'    функции: {func_name}' + separator)
    return func_lines


def clean_source(source_lines):
    clean_lines = list()
    for line in source_lines:
        line = clean_string(line)
        if len(line) != 0:
            clean_lines.append(line)
    print('       Отброшено:', f'{len(source_lines) - len(clean_lines)} строк(и)'.rjust(12))
    print('        Получено:', f'{len(clean_lines)} строк(и)'.rjust(12))
    return clean_lines


def clean_string(string_in):
    string_out = string_in.replace('\n', '')  # удаляем перевод строки
    string_out = string_out.partition('//')[0]  # отбрасываем все java-like комментарии
    string_out = string_out.partition('#')[0]  # отбрасываем все python-like комментарии
    string_out = string_out.lstrip()  # удаляем пробелы в начале строки
    string_out = string_out.rstrip()  # удаляем пробелы в конце строки
    return string_out


def save_output(lines_in):
    file = open(output_file, 'w')
    instruction_count = lines_in.count('\n') + 1 - lines_in.count('//')
    print('\nВ итоговом файле:', f'{instruction_count}'.rjust(3), 'инструкций(и)')
    file.write(lines_in)
    file.close()


def translate_to_asm(func_lines):
    lines_out = ''
    current_line = 0
    while current_line < len(func_lines):
        update_stack(current_line)
        lines_out += translate_instruction(func_lines[current_line])
        current_line += 1
        if current_line == len(func_lines):
            func_stack.pop()  # убираем из стэка
            break
        lines_out += '\n'
    return lines_out


def translate_instruction(instruction):
    line_out = instruction
    func_name = func_stack[-1][0]
    instruction_id = func_stack[-1][1]
    if line_out.startswith('push '):
        line_out = process_push(line_out.partition('push ')[2])
    elif line_out.startswith('pop '):
        line_out = process_pop(line_out.partition('pop ')[2])
    elif line_out.startswith('label '):
        line_out = process_label(func_name, line_out.partition('label ')[2])
    elif line_out.startswith('goto '):
        line_out = process_goto(func_name, line_out.partition('goto ')[2])
    elif line_out.startswith('if-goto '):
        line_out = process_if_goto(func_name, line_out.partition('if-goto ')[2])
    elif line_out.startswith('call '):
        line_out = process_call(line_out.partition('call ')[2])
    elif line_out.startswith('function '):
        line_out = process_func(line_out.partition('function ')[2])
    elif line_out.startswith('return'):
        line_out = process_return()
    else:
        line_out = process_comp(line_out)

    if add_debug_info:
        comment = ('// [' + func_name + ':' + str(instruction_id) + '] ' + instruction + '\n')
        line_out = comment + line_out

    return line_out


def process_push(line_in):
    segment, offset = line_in.split()
    if segment == 'constant':
        return form_asm('@' + offset, 'D=A', push())
    elif segment == 'local':
        return segment_push('@LCL', offset)
    elif segment == 'argument':
        return segment_push('@ARG', offset)
    elif segment == 'this':
        return segment_push('@THIS', offset)
    elif segment == 'that':
        return segment_push('@THAT', offset)
    elif segment == 'static':
        file_name = func_stack[-1][0].partition('.')[0]
        file_offset = static_offsets[file_name]
        offset = str(file_offset + int(offset))
        return form_asm('@' + offset, 'D=M', push())
    elif segment == 'pointer':
        offset = int(offset)
        return form_asm('@THIS' if offset == 0 else '@THAT', 'D=M', push())
    elif segment == 'temp':
        offset = str(int(offset) + 5)
        return form_asm('@' + offset, 'D=M', push())
    return 'unsupported instruction' + str(line_in)  # добавить exit с предупреждением


def push():
    return form_asm('@SP', 'M=M+1', 'A=M-1', 'M=D')


def segment_push(segment, offset):
    return form_asm(segment, 'D=M', '@' + offset, 'A=A+D', 'D=M', push())


def process_pop(line_in):
    segment, offset = line_in.split()
    if segment == 'constant':
        return form_asm(pop(), 'D=M', '@' + offset, 'M=D')
    elif segment == 'local':
        return segment_pop('@LCL', offset)
    elif segment == 'argument':
        return segment_pop('@ARG', offset)
    elif segment == 'this':
        return segment_pop('@THIS', offset)
    elif segment == 'that':
        return segment_pop('@THAT', offset)
    elif segment == 'static':
        file_name = func_stack[-1][0].partition('.')[0]
        file_offset = static_offsets[file_name]
        offset = str(file_offset + int(offset))
        return form_asm(pop(), 'D=M', '@' + offset, 'M=D')
    elif segment == 'pointer':
        offset = int(offset)
        return form_asm(pop(), 'D=M', '@THIS' if offset == 0 else '@THAT', 'M=D')
    elif segment == 'temp':
        offset = str(int(offset) + 5)
        return form_asm(pop(), 'D=M', '@' + offset, 'M=D')
    return 'unsupported instruction' + str(line_in)  # добавить exit с предупреждением


def pop():
    return form_asm('@SP', 'AM=M-1')


def segment_pop(segment, offset):
    return form_asm(segment, 'D=M', '@' + offset, 'D=D+A',  # D = address
                    '@SP', 'M=M-1', 'A=M+1', 'M=D', 'A=A-1', 'D=M', 'A=A+1', 'A=M', 'M=D')


def process_label(func_name, label):
    return '(' + func_name + '$' + label + ')'


def process_goto(func_name, label):
    return form_asm('@' + func_name + '$' + label, 'D;JMP')


def process_if_goto(func_name, label):
    return form_asm(pop(), 'D=M', '@' + func_name + '$' + label, 'D;JNE')


def process_call(line_in):
    callee_name = line_in.split(' ')[0]
    callee_args = int(line_in.split(' ')[1])
    # генерируем уникальную метку в формате 'Sys.init$ret.1' для каждого CALL из функции
    ret_counter = func_stack[-1][2] + 1
    update_stack_ret(ret_counter, callee_name)
    ret_label = func_stack[-1][0] + '$ret.' + str(ret_counter)
    caller_asm = form_asm(
        # push return-address // (Using the label declared below)
        '@' + ret_label, 'D=A', push(),
        # push LCL/ARG/THIS/THAT // Save LCL/ARG/THIS/THAT of the calling function
        '@LCL', 'D=M', push(),
        '@ARG', 'D=M', push(),
        '@THIS', 'D=M', push(),
        '@THAT', 'D=M', push(),
        # ARG = SP-n-5 // Reposition ARG (n = number of args.)
        '@' + str(callee_args + 5), 'D=A', '@SP', 'D=M-D', '@ARG', 'M=D',
        # LCL = SP // Reposition LCL
        '@SP', 'D=M', '@LCL', 'M=D',
        # goto (callee) // Transfer control to callee
        '@' + callee_name, 'D;JMP'
    )
    if callee_name in func_translated:
        if console_debug:
            print('               Already translated. Skipping...', separator)
        callee_asm = ''
    else:
        callee_lines = load_func(callee_name)
        callee_asm = translate_to_asm(callee_lines)  # вложенная функция запускается, на выходе получаем asm код
    return caller_asm + callee_asm + '\n(' + ret_label + ')'  # складываем и добавляем метку для возврата


def process_func(line_in):
    name = line_in.split(' ')[0]
    vars = int(line_in.split(' ')[1])
    # label: start of the function
    lines_out = ('(' + name + ')')
    # push 0 nVars times: creating LCL segment
    if vars != 0:
        lines_out += '\nD=0\n'
        while vars > 0:
            lines_out += push()
            if vars != 1:
                lines_out += '\n'
            vars -= 1
    return lines_out


def process_return():
    return form_asm(
        '@LCL', 'D=M', '@R13', 'M=D',  # endFrame = R13 = LCL
        # retAddr = R14 = *(R13 - 5), сохраняем адрес возврата, чтобы случайно не перезаписать его если f() 0Args
        '@5', 'D=A', '@R13', 'A=M-D', 'D=M', '@R14', 'M=D',
        # *ARG = pop(), складываем возвращаемое значение по адресу ARG, это будет верхнее значение стека вызывающей f()
        pop(), 'D=M', '@ARG', 'A=M', 'M=D',
        '@ARG', 'D=M', '@SP', 'M=D+1',  # SP = ARG+1, Restore SP of the caller
        restore_segment('@THAT'),  # THAT = *(endFrame - 1) endframe--
        restore_segment('@THIS'),  # THIS = *(endFrame - 2) endframe--
        restore_segment('@ARG'),  # ARG = *(endFrame - 3) endframe--
        restore_segment('@LCL'),  # LCL = *(endFrame - 4) endframe--
        '@R14', 'A=M', 'D;JMP'  # Goto return-address (in the caller’s code)
    )


def restore_segment(segment):
    return form_asm('@R13', 'AM=M-1', 'D=M', segment, 'M=D')


def process_comp(line_in):
    if line_in == 'add':
        return form_asm(pop(), 'D=M', pop(), 'D=M+D', push())
    elif line_in == 'sub':
        return form_asm(pop(), 'D=M', pop(), 'D=M-D', push())
    elif line_in == 'neg':
        return form_asm(pop(), 'D=-M', push())
    elif line_in == 'eq':
        return compare('JEQ')
    elif line_in == 'lt':
        return compare('JLT')
    elif line_in == 'gt':
        return compare('JGT')
    elif line_in == 'and':
        return form_asm(pop(), 'D=M', pop(), 'D=M&D', push())
    elif line_in == 'or':
        return form_asm(pop(), 'D=M', pop(), 'D=M|D', push())
    elif line_in == 'not':
        return form_asm(pop(), 'D=!M', push())
    return 'unsupported instruction' + str(line_in)  # добавить exit с предупреждением


def compare(by):  # by: JEQ / JLT / JGT; = / < / >
    true = 'true.' + str(func_stack[-1][1])
    end = 'end.' + str(func_stack[-1][1])
    return form_asm(pop(), 'D=M', pop(),  # pop y=D; pop x=M
                    'D=M-D', '@' + true, 'D;' + by,  # если x-y удовлетворяет условию by - прыгаем на True
                    '@0', 'D=A', '@' + end, 'D;JMP',  # иначе устанавливаем значение False (0) и в конец
                    '(' + true + ')', '@1', 'D=-A',  # D=True=-1
                    '(' + end + ')', push())  # пуш D - в D запомнен результат (0/-1)


def form_asm(*asm):
    lines_out = ''
    for i, instruction in enumerate(asm, start=1):
        if i == len(asm):
            lines_out += instruction
            break
        lines_out += instruction + '\n'
    return lines_out


separator = '\n     ---------------------------------------------------'

if __name__ == '__main__':
    main()
