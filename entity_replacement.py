import re


def replace_dumbledore_with_benjamin(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    content = re.sub(r'\balbus\b', 'Gandalf', content, flags=re.IGNORECASE)

    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)


replace_dumbledore_with_benjamin('harry.txt')
