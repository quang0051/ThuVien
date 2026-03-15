import socket
import paho.mqtt.client as mqtt
import json
from datetime import datetime

TCP_HOST, TCP_PORT = '127.0.0.1', 6001
MQTT_BROKER = '127.0.0.1'

tong_kho = 1000  # Tổng kho sách mặc định
koha_conn = None


def get_time():
    """Lấy thời gian thực để dán vào Log"""
    return datetime.now().strftime("%H:%M:%S")


def update_web(client):
    """Cập nhật Đồng hồ và Biểu đồ Kho trên Web"""
    client.publish("library/inventory/count", tong_kho)


def on_message(client, userdata, msg):
    global tong_kho, koha_conn
    try:
        data = json.loads(msg.payload.decode('utf-8'))
        ma_sv = data.get('ma_sv', '')
        so_luong_yeu_cau = int(data.get('so_luong', 0))
        hanh_dong = data.get('action', '').strip().lower()

        if not ma_sv:
            client.publish("library/kiosk/log", f"[{get_time()}] ⚠️ Vui lòng nhập Tên/Mã SV để thực hiện!")
            return

        msg_log = ""
        link_anh = "clear"  # Mặc định gửi lệnh 'clear' để giấu ảnh đi khi chọn lệnh khác

        # --- NHỮNG HÀNH ĐỘNG TẤU HÀI ---
        if hanh_dong == "sleep":
            msg_log = f"[{get_time()}] 💤 {ma_sv} thấy sách là buồn NGỦ, gục luôn xuống bàn khò khò..."
        elif hanh_dong == "eat":
            msg_log = f"[{get_time()}] 🍜 {ma_sv} lén mang đồ ĂN vào thư viện. Giám thị đang cầm chổi tới kìa!"

        # --- HỘP QUÀ BÍ MẬT ---
        elif hanh_dong == "secret":
            msg_log = f"[{get_time()}] Nơi đó"
            # Gắn link ảnh GIF con mèo (Bạn có thể tự đổi link ảnh khác nếu muốn)
            link_anh = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRkWbmMBFKwVI6Rw67W0MeP1_SzZyyZs4aYpw&s"

            # --- LOGIC MƯỢN SÁCH ---
        elif hanh_dong == "borrow":
            if so_luong_yeu_cau <= 0:
                msg_log = f"[{get_time()}] ⚠️ {ma_sv} mượn 0 cuốn thì lên thư viện làm gì cho mỏi chân?"
            elif tong_kho <= 0:
                msg_log = f"[{get_time()}] ❌ Kho đã hết sạch sách rồi!"
            else:
                if so_luong_yeu_cau > tong_kho:
                    msg_log = f"[{get_time()}] ⚠️ Kho chỉ còn {tong_kho}. Đã vét sạch kho cho {ma_sv}!"
                    tong_kho = 0
                else:
                    tong_kho -= so_luong_yeu_cau
                    msg_log = f"[{get_time()}] ✅ {ma_sv} mượn {so_luong_yeu_cau} cuốn. Kho còn {tong_kho}."

                # Gửi lệnh SIP2 mượn sách tới Koha
                if koha_conn:
                    koha_conn.send(f"11N|AA{ma_sv}|".encode('utf-8'))
                    koha_conn.recv(1024)

        # --- LOGIC TRẢ SÁCH ---
        elif hanh_dong == "return":
            if so_luong_yeu_cau <= 0:
                msg_log = f"[{get_time()}] ⚠️ {ma_sv} trả 0 cuốn? Lại định lừa hệ thống à?"
            elif tong_kho >= 1000:
                msg_log = f"[{get_time()}] ❌ Kho đã đầy 1000 cuốn, không nhận thêm nữa!"
            else:
                cho_trong_kho = 1000 - tong_kho
                so_luong_nhan = min(so_luong_yeu_cau, cho_trong_kho)
                tong_kho += so_luong_nhan

                if so_luong_nhan < so_luong_yeu_cau:
                    msg_log = f"[{get_time()}] ⚠️ Kho sắp full, chỉ nhận {so_luong_nhan}/{so_luong_yeu_cau} cuốn từ {ma_sv}."
                else:
                    msg_log = f"[{get_time()}] 🔄 {ma_sv} trả {so_luong_yeu_cau} cuốn. Kho hiện có {tong_kho}."

                # Gửi lệnh SIP2 trả sách tới Koha
                if koha_conn:
                    koha_conn.send(f"09N|AA{ma_sv}|".encode('utf-8'))
                    koha_conn.recv(1024)
        else:
            msg_log = f"[{get_time()}] ⚠️ Lệnh lạ quá, không hiểu!"

        # --- BẮN DỮ LIỆU LÊN WEB (NODE-RED) ---
        client.publish("library/kiosk/log", msg_log)  # Gửi text log
        client.publish("library/kiosk/inline_image", link_anh)  # Gửi link ảnh (hoặc 'clear')
        update_web(client)  # Gửi số lượng sách để vẽ biểu đồ

        print(msg_log)

    except Exception as e:
        print(f"Lỗi xử lý tin nhắn: {e}")


def start_kiosk():
    global koha_conn
    koha_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        koha_conn.connect((TCP_HOST, TCP_PORT))
        koha_conn.send("9300CNkiosk_user|COkiosk_pass|".encode('utf-8'))
        koha_conn.recv(1024)
        print("[+] Đã kết nối tới Koha Server (Máy chủ SIP2) thành công!")
    except:
        print("⚠️ Cảnh báo: Không thể kết nối Koha Server (koha_server.py). Nhớ bật file đó lên nhé!")
        koha_conn = None

    mqtt_client = mqtt.Client()
    mqtt_client.on_message = on_message

    try:
        mqtt_client.connect(MQTT_BROKER, 1883)
        mqtt_client.subscribe("library/kiosk/request")
        update_web(mqtt_client)
        print("[*] Bộ não Python đã online! Đang đợi lệnh từ giao diện Web...")
        mqtt_client.loop_forever()
    except Exception as e:
        print(f"❌ Lỗi kết nối MQTT: {e}. Vui lòng kiểm tra lại Mosquitto Broker!")


if __name__ == "__main__":
    start_kiosk()