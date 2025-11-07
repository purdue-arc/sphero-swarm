import csv

id_map = dict([])

with open("name_to_id.csv") as csv_file:
    file = csv.reader(csv_file)

    first = True

    for pair in file:
        if (first):
            first = False
            continue
        id_map[pair[0]] = int(pair[1])

print(id_map)