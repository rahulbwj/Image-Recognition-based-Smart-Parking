import socket
import cv2
import threading
from util import get_parking_spots_bboxes, empty_or_not

mask_path = ".g"

mask = cv2.imread(mask_path, 0)
src = cv2.VideoCapture(0)

if not src.isOpened():
    print("Error: Could not open video source.")
    exit()

connected_components = cv2.connectedComponentsWithStats(mask, 4, cv2.CV_32S)
spots = get_parking_spots_bboxes(connected_components)
spots_status = [None for _ in spots]

def get_vacant_spots():
    vacant_spots = []
    for spot_index, spot in enumerate(spots):
        spot_status = spots_status[spot_index]
        if spot_status:
            vacant_spots.append(spot_index + 1)
    return vacant_spots

def handle_client_connection(client_socket):
    try:
        vacant_spots = get_vacant_spots()
        avl_spots_count = sum(spots_status)
        total_spots_count = len(spots_status)
        data_to_send = f"Avl spots count: {avl_spots_count}/{total_spots_count}\nVacant spots: {','.join(map(str, vacant_spots))}"
        client_socket.sendall(data_to_send.encode())
    except Exception as e:
        print(f"Error during client connection: {e}")
    finally:
        client_socket.close()

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(('0.0.0.0', 65432))
server_socket.listen(1)
print('Waiting for client connection...')

frame_nmr = 0
ret = True
step = 30

while ret:
    ret, frame = src.read()
    
    if not ret:
        print("Error - Could not read frame")
        break

    if frame_nmr % step == 0:
        for spot_index, spot in enumerate(spots):
            x1, y1, w, h = spot

            spot_crop = frame[y1:y1 + h, x1:x1 + w]

            spot_status = empty_or_not(spot_crop)
            spots_status[spot_index] = spot_status

    vacant_spots = get_vacant_spots()
    for spot_index, spot in enumerate(spots):
        spot_status = spots_status[spot_index]
        x1, y1, w, h = spots[spot_index]
        if spot_status:
            frame = cv2.rectangle(frame, (x1, y1), (x1 + w, y1 + h), (0, 255, 0), 2)
        else:
            frame = cv2.rectangle(frame, (x1, y1), (x1 + w, y1 + h), (0, 0, 255), 2)
        spot_number = str(spot_index + 1)
        text_x = x1 + w // 2 
        text_y = y1 + h // 2 
        cv2.putText(frame, spot_number, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    avl_spots_count = sum(spots_status)
    total_spots_count = len(spots_status)
    cv2.putText(frame, f'Avl spots count: {avl_spots_count}/{total_spots_count}', (110, 430), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
    vacant_spots_text = ', '.join(map(str, vacant_spots))
    cv2.putText(frame, 'Vacant spots: {}'.format(vacant_spots_text), (110, 447), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,0, 0), 2)
    cv2.imshow('frame', frame)

    server_socket.settimeout(0.01)
    try:
        client_socket, addr = server_socket.accept()
        print('Connected by', addr)
        client_thread = threading.Thread(target=handle_client_connection, args=(client_socket,))
        client_thread.start()
    except socket.timeout:
        pass

    if cv2.waitKey(25) & 0xFF == ord('q'):
        break
    frame_nmr += 1

src.release()
cv2.destroyAllWindows()
server_socket.close()
