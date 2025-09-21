class BondedGroups:
    def __init__(self, n):
        self.bonded_groups = [[id] for id in range(n)]
        self.bonded_group_index = [index for index in range(n)] # maybe should change to parent?

    def is_bonded(self, id1, id2): # -> bool
        return self.bonded_group_index[id1] == self.bonded_group_index[id2]

    def combine(self, id1, id2): # -> bool
        group_index1 = self.bonded_group_index[id1]
        group_index2 = self.bonded_group_index[id2]

        if (group_index1 != group_index2):
            for id in self.bonded_groups[group_index2]:
                self.bonded_group_index[id] = group_index1
            self.bonded_groups[group_index1].append(self.bonded_groups[group_index2])
            self.bonded_groups.pop(group_index2)
            return True
        return False