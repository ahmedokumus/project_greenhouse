import os
from openai import OpenAI
from dotenv import load_dotenv
import time
import threading
import logging
from typing import Dict, Any, List, Tuple
import snap7

# Setup logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('sera_ai_agent')

# Load environment variables
load_dotenv()
base_url = os.getenv("BASE_URL")
deepseek_api_key = os.getenv("GEMINI_API_KEY")
deepseek_model = os.getenv("GEMINI_MODEL")


class PLCConnection:
    """Class to handle PLC connections and operations for sera control"""

    def __init__(self, ip_address: str, rack: int = 0, slot: int = 1):
        """Initialize PLC connection

        Args:
            ip_address: IP address of the PLC
            rack: Rack number (default 0)
            slot: Slot number (default 1)
        """
        self.ip_address = ip_address
        self.rack = rack
        self.slot = slot
        self.plc_client = None
        self.connect()
        logger.info(
            f"PLC connection initialized to {ip_address} rack {rack} slot {slot}")

    def connect(self):
        """Connect to the PLC"""
        try:
            import snap7
            self.plc_client = snap7.client.Client()
            self.plc_client.connect(self.ip_address, self.rack, self.slot)
            logger.info("Successfully connected to PLC")
        except Exception as e:
            logger.error(f"Failed to connect to PLC: {str(e)}")
            self.plc_client = None

    def read_md_float(self, md_address: int) -> float:
        """Read a float value from MD area

        Args:
            md_address: MD address to read from

        Returns:
            Float value from the PLC
        """
        try:
            if not self.plc_client or not self.plc_client.get_connected():
                self.connect()
                if not self.plc_client or not self.plc_client.get_connected():
                    logger.error("Not connected to PLC")
                    return 0.0

            # Read 4 bytes from the MD area (float is 4 bytes)
            result = self.plc_client.read_area(
                snap7.type.Areas.MK, 0, md_address, 4)

            # Convert the bytes to float
            import struct
            value = struct.unpack('>f', result)
            return value[0]
        except Exception as e:
            logger.error(f"Error reading from MD{md_address}: {str(e)}")
            return 0.0

    def write_bool(self, output_address: str, value: bool) -> bool:
        """Write a boolean value to a Q output

        Args:
            output_address: Output address (e.g. "Q0.0")
            value: Boolean value to write

        Returns:
            Success status (True/False)
        """
        try:
            if not self.plc_client or not self.plc_client.get_connected():
                self.connect()
                if not self.plc_client or not self.plc_client.get_connected():
                    logger.error("Not connected to PLC")
                    return False

            # Parse the output address (e.g. "Q0.0")
            if not output_address.startswith("Q"):
                output_address = output_address.replace("%Q", "Q")

            parts = output_address.replace("Q", "").split(".")
            byte_offset = int(parts[0])
            bit_offset = int(parts[1])

            # Read the current byte
            result = self.plc_client.read_area(
                snap7.type.Areas.PA, 0, byte_offset, 1)

            # Modify the specific bit
            mask = 1 << bit_offset
            result_byte = result[0]

            if value:
                result_byte |= mask  # Set bit
            else:
                result_byte &= ~mask  # Clear bit

            # Write back the modified byte
            result[0] = result_byte
            self.plc_client.write_area(
                snap7.type.Areas.PA, 0, byte_offset, result)

            logger.info(f"Successfully wrote {value} to {output_address}")
            return True
        except Exception as e:
            logger.error(f"Error writing to {output_address}: {str(e)}")
            return False

    def write_db_string(self, db_number: int, start_offset: int, data: str, max_size: int = 230) -> bool:
        """
        Write a string value to a DB area
            Args:
                db_number: DB number to write to
                start_offset: Start offset within the DB
                data: String data to write
                max_size: Maximum string size (default: 100)

            Returns:
                Success status (True/False)
        """
        try:
            if not self.plc_client or not self.plc_client.get_connected():
                self.connect()
                if not self.plc_client or not self.plc_client.get_connected():
                    logger.error("Not connected to PLC")
                    return False

            # Prepare the string in Siemens format
            # +2 for header (max length and actual length)
            buffer = bytearray(max_size + 2)

            # Set maximum string length (first byte)
            buffer[0] = max_size

            # Set actual string length (second byte)
            actual_length = min(len(data), max_size)
            buffer[1] = actual_length

            # Convert the string to bytes and copy it to the buffer
            data_bytes = data.encode('ascii', 'ignore')
            for i in range(actual_length):
                if i < len(data_bytes):
                    buffer[i + 2] = data_bytes[i]

            # Write to PLC
            self.plc_client.db_write(db_number, start_offset, buffer)
            logger.info(
                f"Successfully wrote string '{data}' to DB{db_number}.{start_offset}")
            return True

        except Exception as e:
            logger.error(f"Error writing to DB{db_number}: {str(e)}")
            return False

    def read_all_sensor_data(self) -> Dict[str, float]:
        """Read all sensor data from PLC

        Returns:
            Dictionary with all sensor values
        """
        data = {}
        try:
            data["Isik"] = self.read_md_float(0)
            data["CO2"] = self.read_md_float(2)
            data["ToprakNemi"] = self.read_md_float(4)
            data["Nem"] = self.read_md_float(6)
            data["Sicaklik"] = self.read_md_float(8)

            # Log the readings
            logger.info(f"Sera Işık Değeri: {data['Isik']}")
            logger.info(f"CO2 Seviyesi: {data['CO2']}")
            logger.info(f"Toprak Nemi: {data['ToprakNemi']}")
            logger.info(f"Nem Seviyesi: {data['Nem']}")
            logger.info(f"Sıcaklık: {data['Sicaklik']}")

            return data
        except Exception as e:
            logger.error(f"Error reading sensor data: {str(e)}")
            return {}


class AIAgent:
    """AI Agent that analyzes PLC data and makes decisions for sera control"""

    def __init__(self, model_name: str, api_key: str, base_url: str = None):
        """Initialize AI Agent

        Args:
            model_name: Name of the model to use
            api_key: API key for the AI service
            base_url: Optional base URL for the API
        """
        self.model_name = model_name
        client_args = {"api_key": api_key}
        if base_url:
            client_args["base_url"] = base_url
        self.client = OpenAI(**client_args)
        logger.info(f"AI Agent initialized with model {model_name}")

    def analyze_data(self, sensor_data: Dict[str, float], context: str = "") -> Dict[str, Any]:
        """Analyze sera sensor data and recommend actions

        Args:
            sensor_data: Dictionary of sensor values
            context: Additional context information

        Returns:
            Dictionary of recommended actions
        """
        try:
            # Prepare the prompt with the sensor data
            prompt = f"""
            Sera Sensör Verileri:
            Işık Değeri: {sensor_data.get('Isik', 'Okunamadı')}
            CO2 Seviyesi: {sensor_data.get('CO2', 'Okunamadı')}
            Toprak Nemi: {sensor_data.get('ToprakNemi', 'Okunamadı')}
            Nem Seviyesi: {sensor_data.get('Nem', 'Okunamadı')}
            Sıcaklık: {sensor_data.get('Sicaklik', 'Okunamadı')}
            
            Ek Bilgiler:
            {context}
            
            Bir serada optimal koşullar:
            - Sıcaklık: 20-28°C arası olmalı
            - Nem: %60-80 arası olmalı
            - Toprak Nemi: %70-90 arası olmalı
            - CO2: 800-1200 ppm arası olmalı
            - Işık: Sabah/öğlen saatlerinde yüksek, akşam düşük olmalı
            
            Yukarıdaki sera verilerine göre, seranın durumunu analiz et ve uygun eylemleri öner.
            Aşağıdaki ekipmanları kontrol edebilirsin (True=açık, False=kapalı):
            - Havalandırma (%Q0.0): Sıcaklık/nem/CO2 kontrolü için
            - Gölgelendirme (%Q0.1): Işık kontrolü için
            - Isıtıcı (%Q0.2): Sıcaklık kontrolü için
            - Nemlendirici (%Q0.3): Nem kontrolü için
            - Sulama (%Q0.4): Toprak nemi kontrolü için
            - Drenaj (%Q0.5): Fazla su kontrolü için
            - CO2_Tupu (%Q0.6): CO2 seviyesi kontrolü için
            - Led (%Q0.7): Ek ışık kontrolü için
            
            Yanıtını aşağıdaki JSON formatında ver:
            {{
                "analiz": "mevcut durum analizi",
                "eylemler": [
                    {{"ekipman": "ekipman_adı(Örn: Havalandırma,Gölgelendirme,Isıtıcı,Nemlendirici,Sulama,Drenaj,CO2_Tupu,Led)", "durum": true/false, "neden": "bu eylemin nedeni"}}
                ],
                "uyarılar": [
                    "serada oluşabilecek sorunlar ile ilgili uyarılar"
                ]
            }}
            """

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "Sen bir sera otomasyonu asistanısın. Sera sensör verilerini analiz ederek en iyi büyüme koşullarını sağlamak için ekipmanların kontrolünü önerirsin."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )

            # Extract and parse the response
            result = response.choices[0].message.content
            import json
            return json.loads(result)

        except Exception as e:
            logger.error(f"Veri analizi hatası: {str(e)}")
            return {
                "analiz": f"Hata oluştu: {str(e)}",
                "eylemler": [],
                "uyarılar": ["AI analizi başarısız"]
            }


def util(text):
    replacements = {
        'ç': 'c', 'Ç': 'C',
        'ğ': 'g', 'Ğ': 'G',
        'ı': 'i', 'İ': 'I',
        'ö': 'o', 'Ö': 'O',
        'ş': 's', 'Ş': 'S',
        'ü': 'u', 'Ü': 'U'
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


class SeraKontrolSistemi:
    """Main system that coordinates PLC connections and AI analysis for sera control"""

    def __init__(self, plc_config: Dict[str, Any], ai_config: Dict[str, Any]):
        """Initialize the Sera Kontrol System

        Args:
            plc_config: PLC connection configuration
            ai_config: AI agent configuration
        """
        self.plc = PLCConnection(plc_config["ip_address"], plc_config.get(
            "rack", 0), plc_config.get("slot", 1))
        self.ai_agent = AIAgent(
            ai_config["model_name"], ai_config["api_key"], ai_config.get("base_url"))
        self.running = False
        self.monitoring_interval = plc_config.get(
            "monitoring_interval", 60)  # seconds

        # Define the equipment mapping
        self.equipment_mapping = {
            "Havalandırma": "Q0.0",
            "Gölgelendirme": "Q0.1",
            "Isıtıcı": "Q0.2",
            "Nemlendirici": "Q0.3",
            "Sulama": "Q0.4",
            "Drenaj": "Q0.5",
            "CO2_Tupu": "Q0.6",
            "Led": "Q0.7"
        }

    def start(self):
        """Start the monitoring and control loop"""
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        logger.info("Sera Kontrol Sistemi başlatıldı")
        print("-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------")

    def stop(self):
        """Stop the monitoring and control loop"""
        self.running = False
        logger.info("Sera Kontrol Sistemi durduruluyor")

    def _monitoring_loop(self):
        """Main monitoring loop that reads data and calls the AI agent"""
        while self.running:
            try:
                # Read current sensor data
                sensor_data = self.plc.read_all_sensor_data()
                if not sensor_data:
                    logger.error("Sensör verileri okunamadı")
                    time.sleep(self.monitoring_interval)
                    continue

                # Get time of day for context
                import datetime
                current_time = datetime.datetime.now()
                hour = current_time.hour
                time_context = ""
                if 6 <= hour < 12:
                    time_context = "Şu an sabah vakti."
                elif 12 <= hour < 18:
                    time_context = "Şu an öğleden sonra/öğle vakti."
                else:
                    time_context = "Şu an akşam/gece vakti."

                print("-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------")

                # Get AI recommendations
                analysis_result = self.ai_agent.analyze_data(
                    sensor_data, time_context)

                print("-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------")

                logger.info(f"AI analizi: {analysis_result['analiz']}\n")
                self.plc.write_db_string(1, 0, util(
                    analysis_result['analiz'][:100]))
                self.plc.write_db_string(2, 0, util(
                    analysis_result['analiz'][100:200]))
                self.plc.write_db_string(3, 0, util(
                    analysis_result['analiz'][200:250]))

                j = 0

                for j in range(5):
                    self.plc.write_db_string(4+j, 0, "")

                i = 0

                # Process any alerts
                for alert in analysis_result.get("uyarılar", []):
                    logger.warning(f"UYARI: {alert}\n")
                    i = i+1
                    if i == 1:
                        self.plc.write_db_string(
                            4, 0, f"1.UYARI: {util(alert[:100])}")
                    if i == 2:
                        self.plc.write_db_string(
                            5, 0, f"2.UYARI: {util(alert[:100])}")
                    if i == 3:
                        self.plc.write_db_string(
                            6, 0, f"3.UYARI: {util(alert[:100])}")
                    if i == 4:
                        self.plc.write_db_string(
                            7, 0, f"4.UYARI: {util(alert[:100])}")
                    if i == 5:
                        self.plc.write_db_string(
                            8, 0, f"5.UYARI: {util(alert[:100])}")

                # Execute recommended actions
                for action in analysis_result.get("eylemler", []):
                    equipment_name = action.get(
                        "ekipman")
                    state = action.get("durum")
                    reason = action.get("neden", "Neden belirtilmedi")

                    print("-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------")

                    # Check if equipment exists in mapping
                    if equipment_name in self.equipment_mapping:
                        output_address = self.equipment_mapping[equipment_name]
                        logger.info(
                            f"Eylem uygulanıyor: {equipment_name} = {state} ({reason})")
                        success = self.plc.write_bool(output_address, state)
                        if not success:
                            logger.error(
                                f"Eylem uygulanamadı: {equipment_name} = {state}")
                    else:
                        logger.warning(f"Bilinmeyen ekipman: {equipment_name}")

                # Wait for next cycle
                time.sleep(self.monitoring_interval)

            except Exception as e:
                logger.error(f"İzleme döngüsünde hata: {str(e)}")
                time.sleep(self.monitoring_interval)


# Example usage
if __name__ == "__main__":
    # Configuration
    plc_config = {
        "ip_address": "192.168.0.1",  # PLC IP address
        "rack": 0,                      # PLC rack number
        "slot": 1,                      # PLC slot number
        "monitoring_interval": 60       # How often to check PLC data (seconds)
    }

    ai_config = {
        "model_name": deepseek_model or "deepseek-chat",
        "api_key": deepseek_api_key,
        "base_url": base_url
    }

    # Create and start the system
    system = SeraKontrolSistemi(plc_config, ai_config)

    try:
        system.start()
        # Keep the main thread running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        system.stop()
        logger.info("Sistem kullanıcı tarafından durduruldu")
