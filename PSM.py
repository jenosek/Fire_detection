import machine
import time
import BG77

class PSM:
    # TAU constants (Tracking Area Update)
    TAU_6_hours = "00100001"  # 6 hours
    TAU_1_hour = "00010001"  # 1 hour
    TAU_5_minutes = "10100101"  # 5 minutes

    # Active time constants
    ACTIVE_30_seconds = "00001111"  # 30 seconds
    ACTIVE_15_seconds = "00000111"  # 15 seconds
    ACTIVE_2_seconds = "00000001"  # 2 seconds

    def __init__(self, module=None, pon_trig_pin=None, tau=TAU_5_minutes, active=ACTIVE_15_seconds):

        self.module = module
        self.pon_trig = pon_trig_pin
        self.tau = tau if tau is not None else self.TAU_5_minutes
        self.active = active if active is not None else self.ACTIVE_15_seconds
        self.is_enabled = False

    def enable(self):

        if not self.module:
            print("Error: BG77 module not initialized")
            return False
        # AT+QPSMS=1,,,"10100101","00000001"
        result = self.module.sendCommand(f"AT+QPSMS=1,,,\"{self.tau}\",\"{self.active}\"\r\n")
        if "OK" not in result:
            print("Error enabling PSM")
            return False

        result = self.module.sendCommand("AT+QCFG=\"psm/urc\",1\r\n")  # Enable PSM notifications
        if "OK" not in result:
            print("Error enabling PSM notifications")
            return False

        self.is_enabled = True
        return True

    def disable(self):

        if not self.module:
            print("Error: BG77 module not initialized")
            return False

        result = self.module.sendCommand(f"AT+QPSMS=0\r\n")
        if "OK" not in result:
            print("Error disabling PSM")
            return False

        self.is_enabled = False
        return True

    def wakeup(self):

        if not self.pon_trig:
            print("Error: PON trigger pin not initialized")
            return False

        self.pon_trig.value(1)
        time.sleep(0.3)
        self.pon_trig.value(0)
        time.sleep(1)  # Wait for module to wake up
        return True

    def get_psm_status(self):

        if not self.module:
            print("Error: BG77 module not initialized")
            return None

        result = self.module.sendCommand("AT+QPSMS?\r\n")
        if "+QPSMS" in result:
            parts = result.split("+QPSMS: ")[1].split("\r\n")[0].split(",")
            if len(parts) >= 4:
                network_tau = parts[3].strip('"') if parts[3] else "Unknown"
                network_active = parts[4].strip('"') if len(parts) > 4 and parts[4] else "Unknown"
                return {
                    "enabled": parts[0],
                    "network_tau": network_tau,
                    "network_active": network_active,
                }

        return None