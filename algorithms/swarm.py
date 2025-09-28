class Swarm:
    def __init__(self, n):
        self.bonded_groups = [[id] for id in range(1, n + 1)]
        self.bonded_group_index = [index for index in range(n)] # maybe should change to parent?

    def is_bonded(self, id1, id2): # -> bool
        return self.bonded_group_index[id1 - 1] == self.bonded_group_index[id2 - 1]

    def combine(self, id1, id2): # -> bool
        group_index1 = self.bonded_group_index[id1 - 1]
        group_index2 = self.bonded_group_index[id2 - 1]

        if (group_index1 != group_index2):
            for id in self.bonded_groups[group_index2]:
                self.bonded_group_index[id - 1] = group_index1
            self.bonded_groups[group_index1].extend(self.bonded_groups[group_index2])
            self.bonded_groups[group_index2] = []
            return True
        return False
    
    # rename swarm to Network or something else?
    # change empty grids to -1, start ids at 0 to make it easier to call values from arrays given ID?