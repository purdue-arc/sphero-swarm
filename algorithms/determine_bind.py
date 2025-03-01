import random

class Field:

    INVALID = -1
    SPOT_TAKEN = -2
    OK = 0

    sphero_from_id = {} # input an id (0, 1, 2, ...) and get the associated sphero object.

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.field_arr = self.create_field()
        self.next_field_arr = self.create_field();

    def initialize_spheros(self, spheros):
        '''
        instantiates list of spheros
        populates field_arr
        '''
        self.spheros = spheros
        self.sphero_pos_init_arr(spheros)


    def create_field(self):
        '''
        Create field with dimensions given by parameters, fills in 
        invalid positions values with '-' and valid ones with 0
        '''
        field_arr = []
        for i in range(0, self.height, 1):
            field_arr.append([0] * self.width)
            
            for j in range(0, self.width, 1):
                if (i % 2 == 0):
                    if (j % 2 != 0):
                        field_arr[i][j] = '-'
                else:
                    if (j % 2 != 1):
                        field_arr[i][j] = '-'

        return field_arr
        #self.field_arr = field_arr

    def print_array(self):
        '''
        Prints out array for debugging
        '''
        for row in self.field_arr:
            row_vals = ""
            for val in row:
                row_vals += str(val)+" "
            print(row_vals)

    def gen_random_sphero_pos(self, n):
        '''
        Puts n Spheros in random positions on the field as number
        '''
        for i in range(1, n + 1, 1):
            while (True):
                rand_row = random.randint(0, len(self.field_arr) - 1)
                rand_col = random.randint(0, len(self.field_arr[0]) - 1)

                if (self.field_arr[rand_row][rand_col] == 0):
                    self.field_arr[rand_row][rand_col] = i
                    break
            
    def sphero_pos_init_arr(self, spheros):
        '''
        Takes in list of sphero objects, adds all to field_arr.

        Returns Field.INVALID if a sphero position is invalid
        Returns Field.SPOT_TAKEN if the spot is taken
        Returns Field.OK on success of all spheros
        '''
        for sphero in spheros:
            status = self.sphero_pos_init(sphero)
            if status != Field.OK:
                return status
        return Field.OK

    def sphero_pos_init(self, sphero):
        '''
        Takes in a singular sphero object (defined in sphero_driver.py), adds to field_arr

        Returns Field.INVALID if a sphero position is invalid
        Returns Field.SPOT_TAKEN if the spot is taken
        Returns Field.OK on success of all spheros
        '''
        if (sphero.x < 0):
            # This should never happen
            # print(f"No, bad x: {sphero.id}, x = {sphero.x}")
            return Field.INVALID
        if (sphero.y < 0):
            # This should never happen
            # print(f"No, bad y: {sphero.id}, y = {sphero.y}")
            return Field.INVALID
        if (sphero.x >= self.width):
            # This should never happen
            # print(f"No, bad x: {sphero.id}, x = {sphero.x}")
            return Field.INVALID
        if (sphero.y >= self.height):
            # This should never happen
            # print(f"No, bad y: {sphero.id}, y = {sphero.y}")
            return Field.INVALID
        if (self.field_arr[sphero.y][sphero.x] == '-'):
            # This should never happen
            # print("Error")
            return Field.INVALID
        if (self.field_arr[sphero.y][sphero.x] != 0):
            # This should never happen, two spheroes being initialized to the same place
            # print("Error")
            return Field.SPOT_TAKEN
        self.field_arr[sphero.y][sphero.x] = sphero.id
        return Field.OK

    def sphero_pos_init_next(self, sphero, target_x, target_y):
        if self.check_coords_next(target_x, target_y) == Field.OK:
            self.next_field_arr[sphero.target_y][sphero.target_x] = sphero.id
            return Field.OK
        else:
            return Field.INVALID

    def check_coords_next(self, x, y):
        '''
        checks if x and y are valid coordinates inside the next_field_arr.

        **does not update next_field_arr**

        returns Field.INVALID or Field.SPOT_TAKEN on error, else
        returns Field.OK on success.
        '''
        if (x < 0):
            # This should never happen
            # print(f"No, bad x: {sphero.id}, x = {sphero.x}")
            return Field.INVALID
        if (y < 0):
            # This should never happen
            # print(f"No, bad y: {sphero.id}, y = {sphero.y}")
            return Field.INVALID
        if (x >= self.width):
            # This should never happen
            # print(f"No, bad x: {sphero.id}, x = {sphero.x}")
            return Field.INVALID
        if (y >= self.height):
            # This should never happen
            # print(f"No, bad y: {sphero.id}, y = {sphero.y}")
            return Field.INVALID
        if (self.next_field_arr[y][x] == '-'):
            # This should never happen
            # print("Error")
            return Field.INVALID
        if (self.next_field_arr[y][x] != 0):
            # This should never happen, two spheroes being initialized to the same place
            # print("Error")
            return Field.SPOT_TAKEN
        return Field.OK

    def reset_next_field(self):
        '''
        used to wipe the next_field_arr each iteration of the driver loop.
        '''
        self.next_field_arr = self.create_field()

    def determine_close(self, n):
        '''
        Returns all ball pairings with distances less than n
        as list of lists
        '''
        
        relevant_info_on_spheros = []

        # identifying position of spheros
        for row in range(0, len(self.field_arr), 1):
            for col in range(0, len(self.field_arr[row]), 1):
                if (self.field_arr[row][col] != 0 and self.field_arr[row][col] != '-'):
                    relevant_info_on_spheros.append((row, col, self.field_arr[row][col]))

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

    def group_sphero_objects(self, spheros):
        '''
        returns list of sphero lists.
        each list's spheros represents a group and its spheros.

        logic taken from siddh-sphero.py (Thanks Siddh)
        '''

        bonds = []

        for sphero in spheros:
            bonds.append([sphero])

            i = 0           
            while (i < len(bonds)):
                j = 0
                while (j < len(bonds[i])):
                    sphero = bonds[i][j]
                    k = i + 1
                    while(k < len(bonds)):
                        l = 0
                        while (l < len(bonds[k])):
                            other = bonds[k][l]

                            # if two spheros are a SET distance apart, bond them
                            # When bonding we combine their two individual arrays into one
                            if (sphero.check_bonding(other)):
                                bonds[i].extend(bonds[k])
                                bonds.pop(k)
                                k -= 1
                                break
                            l += 1
                        k += 1
                    j += 1
                i += 1

        return bonds


# ------------------------------------
# EXAMPLE USAGE
# class Sphero:
#     def __init__(self, x, y, id):
#         self.x = x
#         self.y = y
#         self.id = id

# field_arr = Field(10, 11)
# field_arr.create_field()

# sphero = Sphero(2,0,8)
# print(field_arr.sphero_pos_init(sphero)) # Will print 0 (OK)
# sphero_taken = Sphero(2,0,7)
# print(field_arr.sphero_pos_init(sphero_taken)) # Will print -2 (SPOT_TAKEN)
# sphero_inv = Sphero(-3,0,6)
# print(field_arr.sphero_pos_init(sphero_inv)) # Will print -1 (INVALID)
# field_arr.print_array()

# sphero_bond = Sphero(2,2,5)
# field_arr.sphero_pos_init(sphero_bond)
# field_arr.print_array()


# pairs_of_spheros = field_arr.determine_close(2)
# print(pairs_of_spheros)

# if (len(pairs_of_spheros) > 0):
#     groups_of_spheros = field_arr.group_spheros(pairs_of_spheros)
#     print(groups_of_spheros)
