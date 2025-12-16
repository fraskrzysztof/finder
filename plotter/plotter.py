

class plotter:
    def __init__(self):
        pass
    
    def update(self, curve_x, curve_y, error_time, error_x_data, error_y_data):
        curve_x.setData(error_time, error_x_data)
        curve_y.setData(error_time, error_y_data)