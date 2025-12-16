import serial

class serialMenager:
    def __init__(self):
        
        self.ser = None

    def detect_serial_ports(self):

        ports = serial.tools.list_ports.comports()
        available = []

        accepted_keywords = [
            "USB", "UART", "ACM", "CH340", "CH910",
            "CP210", "FTDI", "FT232", "Arduino",
            "STM", "ESP", "Silicon Labs"
        ]

        for port in ports:
            desc = port.description.upper()
            if any(keyword in desc for keyword in accepted_keywords):
                available.append((port.device, port.description))

        return available

    def open_serial_port(self, port, brate=115200):
        if self.ser is not None:
            self.ser.close()
       
        try:
            self.ser = serial.Serial(port, baudrate = brate, timeout = 1)
            print("port opened")
            return True 
        except Exception as e:
            print(f"[SerialManager] Error opening port: {e}")
            self.ser = None
            return False
        

    def close_serial_port(self):
        if self.ser and not self.ser.is_open:
            try:
                self.ser.close()
            except Exception as e:
                print(f"[SerialMenager] Error closing port: {e}")
        self.ser = None

    def serial_send(self, data_a, data_b, precision = 3):
        if not self.ser or not self.ser.is_open:
            return False
        
        try:
            data = f"{data_a:.{precision}f} {data_b:.{precision}f}\n"
            data = data.encode('utf-8')
            self.ser.write(data)
            response = self.ser.readline().decode('utf-8').strip()
            print("Odpowiedź z ESP32:", response)
            return True
        except Exception as e:
            print(f"[SerialMenager] Error sending data: {e}")
            return False