import random

class Field:

    def create_field(self, width, height):
        '''
        Create field with dimensions given by parameters, fills in 
        invalid positions values with '-' and valid ones with 0
        '''
        field_arr = []
        for i in range(0, height, 1):
            field_arr.append([0] * width)
            
            for j in range(0, width, 1):
                if (i % 2 == 0):
                    if (j % 2 != 0):
                        field_arr[i][j] = '-'
                else:
                    if (j % 2 != 1):
                        field_arr[i][j] = '-'

        return field_arr

    def print_array(self, field):
        '''
        Prints out array in more readable manner
        '''
        for row in field:
            row_vals = ""
            for val in row:
                row_vals += str(val)+" "
            print(row_vals)

    def gen_random_sphero_pos(self, field, n):
        '''
        Puts n Spheros in random positions on the field as number
        '''
        for i in range(1, n + 1, 1):
            while (True):
                rand_row = random.randint(0, len(field) - 1)
                rand_col = random.randint(0, len(field[0]) - 1)

                if (field[rand_row][rand_col] == 0):
                    field[rand_row][rand_col] = i
                    break
        
        return field

    def determine_close(self, field, n):
        '''
        Returns all ball pairings with distances less than n
        as list of lists
        '''
        
        relevant_info_on_spheros = []

        # identifying position of spheros
        for row in range(0, len(field), 1):
            for col in range(0, len(field[row]), 1):
                if (field[row][col] != 0 and field[row][col] != '-'):
                    relevant_info_on_spheros.append((row, col, field[row][col]))

        bound_spheros = []
        for i in range(0, len(relevant_info_on_spheros) - 1, 1):
            for j in range(i + 1, len(relevant_info_on_spheros), 1):
                y_diff = abs(relevant_info_on_spheros[i][0] - relevant_info_on_spheros[j][0])
                x_diff = abs(relevant_info_on_spheros[i][1] - relevant_info_on_spheros[j][1])
                dist = x_diff + y_diff
                if (dist <= n and y_diff != n):
                    bound_spheros.append([relevant_info_on_spheros[i][2], relevant_info_on_spheros[j][2]])
        return bound_spheros

    def group_spheros(self, bound_spheros):
        '''
        Processes list of pairs into list of list groups
        '''
        groups_of_spheros = []
        groups_of_spheros.append(set(bound_spheros[0]))

        for i in range(0, len(bound_spheros), 1):
            found_group = False
            for group_num in range(0, len(groups_of_spheros), 1):
                if (len(groups_of_spheros[group_num].intersection(set(bound_spheros[i]))) != 0):
                    for val in bound_spheros[i]:
                        groups_of_spheros[group_num].add(val)
                    found_group = True
                    break
            if (not found_group):
                groups_of_spheros.append(set(bound_spheros[i]))
        
        return groups_of_spheros


# field_arr = create_field(10, 11)
# field_arr = gen_random_sphero_pos(field_arr, 9)
#
# print_array(field_arr)
#
# pairs_of_spheros = determine_close(field_arr, 2)
# print(pairs_of_spheros)
#
# groups_of_spheros = group_spheros(pairs_of_spheros)
# print(groups_of_spheros)
