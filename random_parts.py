import random

parts_number_by_product = [20, 22, 25, 30, 33]

def make_parts_list():

    parts = []

    for i in range(44, 101):
        parts.append(i)

    return parts

with open("products_and_parts.txt", "w") as file:

    for i, parts_number in enumerate(parts_number_by_product):
        string = ""
        # file.write('product ' + str(i) + ' with ' + str(parts_number) + ' parts' + '\n')
        parts = make_parts_list()
        random.shuffle(parts)
        for i in range(parts_number):
            random_pos = parts.pop()
            # file.write(str(random_pos)) + " "
            string += str(random_pos) + ";"

        string = string[:-1]
        # string[-1] = "]"
        file.write(string)
        file.write('\n')


