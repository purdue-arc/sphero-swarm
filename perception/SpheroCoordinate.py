class SpheroCoordinate:
    def __init__(self, ID, x_coordinate=0.0, y_coordinate=0.0):
        self.ID = ID
        self.x_coordinate = x_coordinate
        self.y_coordinate = y_coordinate

    def __repr__(self):
        return f"Sphero(ID={self.ID}, x={self.x_coordinate}, y={self.y_coordinate})"
