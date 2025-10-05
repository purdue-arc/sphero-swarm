class Swarm:
    def __init__(self, n):

        # A 2D array where each individual array represents a bonding group
        # and stores all sphero ids that are apart of the same bonding group
        self.bonded_groups = [[id] for id in range(1, n + 1)]

        # an array containing the bonding group index for each sphero, accessed by id - 1
        self.bonded_group_index = [index for index in range(n)]

    def find_bonding_group(self, id): # -> List[Sphero]
        """
        Find the bonding group given a sphero's id

        Args:
            id: (int) a sphero's id
        
        Returns:
            (List[Sphero]): a list of sphero ids within the same bonding group as the passed in sphero
        """
        return self.bonded_groups[self.bonded_group_index[id - 1]]

    def is_bonded(self, id1, id2): # -> bool
        """
        Check if two spheros are bonded

        Args:
            id1: (int) the first sphero's id
            id2: (int) the second sphero's id

        Returns:
            (bool): Are the two sphero's bonded?
        """
        return self.bonded_group_index[id1 - 1] == self.bonded_group_index[id2 - 1]

    def combine(self, id1, id2): # -> bool
        """
        Bond the two spheros if they are not already bonded

        Args:
            id1: (int) the first sphero's id
            id2: (int) the second sphero's id
        
        Returns:
            (bool): Were the two spheros able to bond
        """
        group_index1 = self.bonded_group_index[id1 - 1]
        group_index2 = self.bonded_group_index[id2 - 1]

        # if they are not already apart of the same bonding group
        if (group_index1 != group_index2):

            # add all ids from bonding_group2 to bonding_group 1
            # and update the bonding_group_index array
            for id in self.bonded_groups[group_index2]:
                self.bonded_group_index[id - 1] = group_index1
            self.bonded_groups[group_index1].extend(self.bonded_groups[group_index2])
            self.bonded_groups[group_index2] = []
            return True
        return False