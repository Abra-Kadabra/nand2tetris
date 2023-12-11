import os.path
import sys

source_file = 'source_file.vm'
instructions_file = 'clean_file.vm'
output_file = 'output_file.asm'

if len(sys.argv) > 1:
    if os.path.isfile(sys.argv[1]):
        source_file = sys.argv[1]
        instructions_file = 'clear_' + source_file
        output_file = source_file.partition('.')[0] + '.asm'
    else:
        print('\n Указано несуществующее имя файла')
        sys.exit()
else:
    if not os.path.isfile(source_file):
        print('\n Не указано имя файла и файл по умолчанию не найден')
        sys.exit()


current_line = 0  # 0 - processing not started yet

# stack: M[256]..M[2047] ; SP = M[0] - stack pointer (NEXT available location of the stack)

# LCL = M[1] - local pointer (BASE address of the local segment, allocated DYNAMICALLY)
# ARG = M[2] - the method's arguments (BASE address, allocated dynamically)
# THIS = M[3] - fields of the current object (BASE address, allocated dynamically)
 # THAT = M[4]- array that the current method may be processing (BASE address, allocated dynam.)

 # constants: push constant i: *SP = i, SP++
# static M[16] - M[255] - each static variable i in file Xxx -> Xxx.i
 # pointer is a fixed memery segment and has 2 entries (0 and 1 = THIS and THAT)
 # temp M[5] - M[12]

# M[13]..M[15] - R13..R15 - general purpose registers
# local argument this that constant static pointer temp

def main():
    print('\n   Входящий файл: ' + source_file + '\n  Исходящий файл: ' + output_file + '\n')
    source_lines = load_source()
    cleaned_lines = process_source(source_lines)
    if 1 == 0:  # задать условие для сохранения очищенного исходника
        save_instructions(cleaned_lines)
    output_lines = translate_to_asm(cleaned_lines)
    save_output(output_lines)
    print('\n *** Успешно завершено ***')
    sys.exit()


def load_source():
    file_in = open(source_file, "r")
    lines = file_in.readlines()
    file_in.close()
    print(' Итого загружено: ' + str(len(lines)) + ' строк(и)')
    return (lines)


def save_instructions(lines_in):
    file = open(instructions_file, 'w')
    for i, line in enumerate(lines_in, start=1):
        if i == len(lines_in):
            file.write(line)
            break
        file.write(line + '\n')
    file.close()


def save_output(lines_in):
    file = open(output_file, 'w')
    print('В итоговом файле: ' + str(lines_in.count('\n') + 1) + ' инструкций(и)')
    file.write(lines_in)
    file.close()


def process_source(lines_in):
    lines_out = list()
    empty = 0
    i = 0
    while i < len(lines_in):
        line = clean_string(lines_in[i])
        if len(line) == 0:
            empty += 1
        else:
            lines_out.append(line)
        i += 1
    print('       Отброшено: ' + str(empty) + ' пустых строк(и)')
    print('  В новом списке: ' + str(len(lines_out)) + ' строк(и)')
    return lines_out


def clean_string(string_in):
    string_out = string_in.replace('\n', '')  # удаляем перевод строки
    string_out = string_out.partition('//')[0]  # отбрасываем все java-like комментарии
    string_out = string_out.partition('#')[0]  # отбрасываем все python-like комментарии
    string_out = string_out.lstrip()  # удаляем пробелы в начале строки
    string_out = string_out.rstrip()  # удаляем пробелы в конце строки
    return string_out


def translate_to_asm(lines_in):
    lines_out = ''
    global current_line
    while current_line < len(lines_in):
        lines_out += translate_instruction(lines_in[current_line])
        current_line += 1
        if current_line == len(lines_in):
            break
        lines_out += '\n'
    return lines_out


def translate_instruction(line_in):
    line_out = line_in
    if line_out.startswith('push '):
        line_out = process_push(line_out.partition('push ')[2])
    elif line_out.startswith('pop '):
        line_out = process_pop(line_out.partition('pop ')[2])
    else:
        line_out = process_comp(line_out)
    return str('// [' + str(current_line) + '] ' + line_in + '\n' + line_out)
    # return line_out


def process_push(line_in):
    args = line_in.split()
    segment = args[0]
    offset = args[1]
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
        offset = str(int(offset) + 16)
        return form_asm('@' + offset, 'D=M', push())
    elif segment == 'pointer':
        offset = int(offset)
        return form_asm('@THIS' if offset == 0 else '@THAT', 'D=M', push())
    elif segment == 'temp':
        offset = str(int(offset) + 5)
        return form_asm('@' + offset, 'D=M', push())
    return 'unsupported instruction' + str(line_in)  # добавить exit с предупреждением


def push():  # saves D to stack
    return form_asm('@SP', 'M=M+1', 'A=M-1', 'M=D')  # optimized version
    # return form_asm('@SP', 'A=M', 'M=D', '@SP', 'M=M+1')  # standart version


def segment_push(segment, offset):
    return form_asm(segment, 'D=M', '@' + offset, 'A=A+D', 'D=M', push())


def process_pop(line_in):
    args = line_in.split()
    segment = args[0]
    offset = args[1]
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
        offset = str(int(offset) + 16)
        return form_asm(pop(), 'D=M', '@' + offset, 'M=D')
    elif segment == 'pointer':
        offset = int(offset)
        return form_asm(pop(), 'D=M', '@THIS' if offset == 0 else '@THAT', 'M=D')
    elif segment == 'temp':
        offset = str(int(offset) + 5)
        return form_asm(pop(), 'D=M', '@' + offset, 'M=D')
    return 'unsupported instruction' + str(line_in)  # добавить exit с предупреждением


def pop():  # loads last stack M
    return form_asm('@SP', 'AM=M-1')


def segment_pop(segment, offset):
    return form_asm(segment, 'D=M', '@' + offset, 'D=D+A',  # D = address
                    '@SP', 'M=M-1', 'A=M+1', 'M=D', 'A=A-1', 'D=M', 'A=A+1', 'A=M', 'M=D')
    # D - адрес КУДА нам писать поп
    # @SP
    # M=M-1 - меняем укзатель как будто уже делаем поп
    # A=M+1 - но прыгаем на следующий адрес М, его содержание мертво на данный момент
    # M=D - записываем в мёртвый (M+1) значение КУДА нам писать в поп
    # A=A-1 - переходим на адрес указывающий ЧТО нам писать поп
    # D=M - запоминаем ЧТО писать в D
    # A=A+1 - возвращаемся к М = КУДА писать в поп
    # A=M - прыгаем КУДА писать
    # M=D - пишем ЧТО надо


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
    true = 'true.' + str(current_line)
    end = 'end.' + str(current_line)
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


if __name__ == '__main__':
    main()
