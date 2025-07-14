from machine import Pin, PWM
import time

# ===== TM1637 4-digit display class =====
class TM1637:
    def __init__(self, clk_pin, dio_pin):
        self.clk = Pin(clk_pin, Pin.OUT)
        self.dio = Pin(dio_pin, Pin.OUT)
        self.digits = [0x3f, 0x06, 0x5b, 0x4f, 0x66,
                       0x6d, 0x7d, 0x07, 0x7f, 0x6f, 0x00]

    def start(self):
        self.dio.value(1)
        self.clk.value(1)
        self.dio.value(0)
        self.clk.value(0)

    def stop(self):
        self.clk.value(0)
        self.dio.value(0)
        self.clk.value(1)
        self.dio.value(1)

    def write_byte(self, b):
        for i in range(8):
            self.clk.value(0)
            self.dio.value((b >> i) & 1)
            self.clk.value(1)
        self.clk.value(0)
        self.dio.init(Pin.IN)
        self.clk.value(1)
        self.dio.init(Pin.OUT)
        self.clk.value(0)

    def display(self, nums, colon=False):
        self.start()
        self.write_byte(0x40)
        self.stop()

        self.start()
        self.write_byte(0xC0)
        for i, num in enumerate(nums):
            seg = self.digits[num] if num < len(self.digits) else 0x00
            if colon and i == 1:
                seg |= 0x80
            self.write_byte(seg)
        self.stop()

        self.start()
        self.write_byte(0x88 + 7)
        self.stop()

# ===== Setup =====
display = TM1637(2, 3)	

btn_hour = Pin(19, Pin.IN, Pin.PULL_UP)
btn_minute = Pin(18, Pin.IN, Pin.PULL_UP)
btn_start = Pin(20, Pin.IN, Pin.PULL_UP)

servo3 = None

def init_servo():
    global servo3
    servo3 = PWM(Pin(10))
    servo3.freq(50)

def deinit_servo():
    global servo3
    if servo3:
        servo3.deinit()
        servo3 = None

def set_servo_angle(angle):
    if servo3 is None:
        return
    min_duty = 1638
    max_duty = 8192
    duty = min_duty + (max_duty - min_duty) * angle / 180
    servo3.duty_u16(int(duty))

# ===== Timer State =====
hours = 0
minutes = 0
timer_running = False
last_minute_tick = time.ticks_ms()

# ===== Debounce =====
debounce_ms = 200
prev_hour = prev_minute = prev_start = True
last_hour_press = last_minute_press = last_start_press = 0

# ===== Main Loop =====
while True:
    now = time.ticks_ms()

    # --- BUTTON HANDLING ---
    curr_hour = btn_hour.value()
    curr_minute = btn_minute.value()
    curr_start = btn_start.value()

    if prev_hour and not curr_hour and time.ticks_diff(now, last_hour_press) > debounce_ms:
        hours = (hours + 1) % 100
        last_hour_press = now

    if prev_minute and not curr_minute and time.ticks_diff(now, last_minute_press) > debounce_ms:
        minutes = (minutes + 1) % 60
        last_minute_press = now

    if prev_start and not curr_start and time.ticks_diff(now, last_start_press) > debounce_ms:
        timer_running = not timer_running
        last_start_press = now

        if timer_running:
            print("Timer started")
            init_servo()
            set_servo_angle(90)
            time.sleep(0.5)
            deinit_servo()
        else:
            print("Timer stopped manually")

    prev_hour = curr_hour
    prev_minute = curr_minute
    prev_start = curr_start

    # --- TIMER LOGIC (non-blocking) ---
    if timer_running and time.ticks_diff(now, last_minute_tick) >= 60000:  # 60 sec passed
        last_minute_tick = now
        if minutes == 0:
            if hours == 0:
                timer_running = False
                print("Timer finished")
                init_servo()
                set_servo_angle(0)
                time.sleep(0.5)
                deinit_servo()
            else:
                hours -= 1
                minutes = 59
        else:
            minutes -= 1

    # --- DISPLAY ---
    colon_state = (now // 500) % 2 == 0
    display.display([hours // 10, hours % 10, minutes // 10, minutes % 10], colon=colon_state)

    time.sleep(0.01)  # smooth loop