import socket
import time

HOST, PORT = '127.0.0.1', 6001


def start_koha_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen(1)
    print(f"[*] MÁY CHỦ KOHA (SIP2) ĐANG CHẠY TẠI CỔNG {PORT}...")

    conn, addr = server_socket.accept()
    print(f"[+] Kiosk đã kết nối: {addr}")

    while True:
        data = conn.recv(1024).decode('utf-8')
        if not data: break

        if data.startswith("93"):
            conn.send("941".encode('utf-8'))
        elif data.startswith("11"):
            time.sleep(0.5)
            conn.send("121|U1234|".encode('utf-8'))
        elif data.startswith("09"):
            time.sleep(0.5)
            conn.send("101|U1234|".encode('utf-8'))

    conn.close()


if __name__ == "__main__":
    start_koha_server()