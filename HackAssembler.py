import os.path
import sys

CONST = {'R0': '0', 'R1': '1', 'R2': '2', 'R3': '3', 'R4': '4', 'R5': '5', 'R6': '6', 'R7': '7',
         'R8': '8', 'R9': '9', 'R10': '10', 'R11': '11', 'R12': '12', 'R13': '13', 'R14': '14', 'R15': '15',
         'SP': '0', 'LCL': '1', 'ARG': '2', 'THIS': '3', 'THAT': '4', 'SCREEN': '16384', 'KBD': '24576'}

DEST = {
    '0': '000',
    'M': '001',
    'D': '010',
    'DM': '011',  # special case
    'MD': '011',
    'A': '100',
    'AM': '101',
    'AD': '110',
    'ADM': '111',  # special case
    'AMD': '111'
}

JUMP = {
    'null': '000',
    'JGT': '001',
    'JEQ': '010',
    'JGE': '011',
    'JLT': '100',
    'JNE': '101',
    'JLE': '110',
    'JMP': '111'
}

COMP = {
    '0': '0101010',
    '1': '0111111',
    '-1': '0111010',
    'D': '0001100',
    'A': '0110000',
    'M': '1110000',
    '!D': '0001101',
    '!A': '0110001',
    '!M': '1110001',
    '-D': '0001111',
    '-A': '0110011',
    '-M': '1110011',
    'D+1': '0011111',
    'A+1': '0110111',
    'M+1': '1110111',
    'D-1': '0001110',
    'A-1': '0110010',
    'M-1': '1110010',
    'D+A': '0000010',
    'D+M': '1000010',
    'D-A': '0010011',
    'D-M': '1010011',
    'A-D': '0000111',
    'M-D': '1000111',
    'D&A': '0000000',
    'D&M': '1000000',
    'D|A': '0010101',
    'D|M': '1010101'
}

labels = {}
vars = {}

source_file = 'source_file.asm'
# instructions_file = 'instructions.asm'
digital_file = 'output_file.hack'

if len(sys.argv) > 1:
    if os.path.isfile(sys.argv[1]):
        source_file = sys.argv[1]
        digital_file = source_file.partition('.')[0] + '.hack'
    else:
        print('\n Указано несуществующее имя файла')
        sys.exit()
else:
    if not os.path.isfile(source_file):
        print('\n Не указано имя файла и файл по умолчанию не найден')
        sys.exit()


def main():
    print('\n   Входящий файл: ' + source_file + '\n  Исходящий файл: ' + digital_file + '\n')
    source_lines = load_source_file()
    cleaned_lines = process_the_source(source_lines)
    # save_instructions(cleaned_lines)
    digital_lines = do_assemble(cleaned_lines)
    save_digital(digital_lines)
    print('\n *** Успешно завершено ***')
    sys.exit()


def load_source_file():
    file_in = open(source_file, "r")
    lines = file_in.readlines()
    file_in.close()
    print(' Итого загружено: ' + str(len(lines)) + ' строк(и)')
    return (lines)


# def save_instructions(lines_in):
#     file = open(instructions_file, 'w')
#     for line in lines_in:
#         file.write(line + '\n')
#     file.close()


def save_digital(lines_in):
    file = open(digital_file, 'w')
    print('В итоговом файле: ' + str(lines_in.count('\n') + 1) + ' инструкций(и)')
    file.write(lines_in)
    file.close()


def process_the_source(lines_in):
    lines_out = list()
    empty_lines = 0
    line_number = 0
    while line_number < len(lines_in):
        the_line = clean_string(lines_in[line_number])
        if len(the_line) == 0:
            empty_lines += 1
        elif the_line.startswith('(') and the_line.endswith(')'):
            labels[the_line[1:(len(the_line) - 1)]] = str(line_number - empty_lines)
            empty_lines += 1
        else:
            lines_out.append(the_line)
        line_number += 1
    print('       Отброшено: ' + str(empty_lines) + ' пустых строк(и)')
    print('  В новом списке: ' + str(len(lines_out)) + ' строк(и)')
    return (lines_out)


def clean_string(string_in):
    string_out = string_in.replace('\n', '')  # удаляем перевод строки
    string_out = string_out.replace(' ', '')  # удаляем все пробелы
    string_out = string_out.partition('//')[0]  # отбрасываем все java-like комментарии
    string_out = string_out.partition('#')[0]  # отбрасываем все python-like комментарии
    return string_out


def do_assemble(lines_in):
    lines_out = ''
    line_number = 0
    while line_number < len(lines_in):
        lines_out += translate_instruction(lines_in[line_number])
        line_number += 1
        if line_number == len(lines_in):
            break
        lines_out += '\n'
    return lines_out


def translate_instruction(line_in):
    line_out = line_in
    if line_out[0] == '@':
        line_out = process_a_instruction(line_out)
    else:
        line_out = process_c_instruction(line_out)
    return line_out


def process_a_instruction(line_in):
    line = line_in.partition('@')[2]
    if line in CONST:
        line = CONST[line]
    elif line in labels:
        line = labels[line]
    elif line in vars:
        line = vars[line]
    elif not line.isdigit() and not line in vars:  # found new variable
        var_address = 16 + len(vars)
        vars[line] = str(var_address)
        line = vars[line]
    return '{0:016b}'.format(int(line))


def process_c_instruction(line_in):
    line = line_in

    jump_out = line.partition(';')[2]
    if jump_out:
        jump_out = JUMP[jump_out]
        line = line.partition(';')[0]
    else:
        jump_out = JUMP['null']

    if line.partition('=')[2]:
        dest_out = DEST[line.partition('=')[0]]
        line = line.partition('=')[2]
    else:
        dest_out = DEST['0']

    comp_out = COMP[line]
    return '111' + comp_out + dest_out + jump_out


if __name__ == '__main__':
    main()
