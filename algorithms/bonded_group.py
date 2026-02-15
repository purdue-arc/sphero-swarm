class BondedGroup:
    def __init__(self,list_spheros,id):
        self.group_id = id
        self.spheros = list_spheros
        self.center = None
        self.size = len(list_spheros)
        self.box = [0,0,0,0]
    



