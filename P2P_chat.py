import socket
import threading

def is_valid_ip(ip):
    """
    Validates an IPv4 address.
    """
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False

# Global dictionary to store active peers (from incoming messages or sent messages).
active_peers = {}

# Global dictionary to store connected peers (explicit connections).
connected_peers = {}

# Globals to store this peer's listening port and team name
my_listening_port = None
my_team_name = None

def handle_client(conn, addr):

    ip, ephemeral_port = addr
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            
            full_message = data.decode().strip()
            # Default values.
            sender_listening_port = ephemeral_port
            sender_team_name = "unknown_team"
            actual_message = full_message
            
            if full_message.startswith("LISTENING_PORT:"):
                parts = full_message.split("|", 2)
                if len(parts) == 3:
                    try:
                        sender_listening_port = int(parts[0].split(":", 1)[1])
                    except ValueError:
                        sender_listening_port = ephemeral_port
                    if parts[1].startswith("TEAM_NAME:"):
                        sender_team_name = parts[1].split(":", 1)[1]
                    actual_message = parts[2]
            
            print(f"Received from {ip}:{sender_listening_port} {sender_team_name} -> {actual_message}")
            
            # Update active peers with sender's details.
            active_peers[(ip, sender_listening_port)] = True
            
            # If this is a connection message, record it as an explicit connection.
            if actual_message.lower() in ["connection message", "manual connection message"]:
                connected_peers[(ip, sender_listening_port)] = True
            
            if actual_message.lower() == "exit":
                print(f"Peer {ip}:{sender_listening_port} disconnected.")
                active_peers.pop((ip, sender_listening_port), None)
                connected_peers.pop((ip, sender_listening_port), None)
                break
    
    except Exception as e:
        print(f"Error handling client {ip}:{sender_listening_port}: {e}")
    finally:
        conn.close()

def server_thread(my_port):
    """
    Starting a TCP server that listens for incoming connections.
    For each connection, spawning a new thread to handle it.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', my_port))
    s.listen(5)
    while True:
        try:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
        except Exception as e:
            print("Server accept error:", e)
            break

def send_message():
    """
    Upon sending, the peer is added only to active_peers.
    """
    global my_listening_port, my_team_name
    recipient_ip = input("Enter the recipient's IP address: ").strip()
    if not is_valid_ip(recipient_ip):
        print("You entered an invalid ip address.")
        return
    try:
        recipient_port = int(input("Enter the recipient's port number: ").strip())
    except ValueError:
        print("Invalid port number.")
        return

    message = input("Enter your message: ").strip()
    full_message = f"LISTENING_PORT:{my_listening_port}|TEAM_NAME:{my_team_name}|{message}"
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((recipient_ip, recipient_port))
        s.send(full_message.encode())
        print(f"Message sent to {recipient_ip}:{recipient_port}")
        # Only add to active_peers here.
        active_peers[(recipient_ip, recipient_port)] = True
    except Exception as e:
        print(f"Connection error: {e}")
    finally:
        s.close()

def query_peers():
    """
    Displays two lists:
      1. Active Peers - those who have exchanged messages.
      2. Connected Peers - those with which an explicit connection has been established.
    """
    print("\n--- Active Peers (from incoming/sent messages) ---")
    if active_peers:
        for idx, (ip, port) in enumerate(active_peers.keys(), start=1):
            print(f"{idx}. {ip}:{port}")
    else:
        print("No active peers.")
    
    print("\n--- Connected Peers (explicit connections) ---")
    if connected_peers:
        for idx, (ip, port) in enumerate(connected_peers.keys(), start=1):
            print(f"{idx}. {ip}:{port}")
    else:
        print("No connected peers.")

def connect_to_peers():
    """
    Connects to peers.
    You can choose to automatically connect to all active peers
    or manually enter an IP address and port number to connect.
    Upon a successful explicit connection, the peer is added to connected_peers.
    """
    global my_listening_port, my_team_name
    print("\nChoose connection mode:")
    print("A - Automatically connect to all active peers")
    print("M - Manually enter IP and port to connect")
    mode = input("Enter your choice (A/M): ").strip().upper()
    
    if mode == "A":
        if active_peers:
            for (ip, port) in list(active_peers.keys()):
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.connect((ip, port))
                    connection_message = f"LISTENING_PORT:{my_listening_port}|TEAM_NAME:{my_team_name}|connection message"
                    s.send(connection_message.encode())
                    print(f"Connected to {ip}:{port}")
                    # Record explicit connection on the sender side.
                    connected_peers[(ip, port)] = True
                except Exception as e:
                    print(f"Failed to connect to {ip}:{port}: {e}")
                finally:
                    s.close()
        else:
            print("No active peers to connect.")
    
    elif mode == "M":
        manual_ip = input("Enter the IP address to connect to: ").strip()
        if not is_valid_ip(manual_ip):
            print("You entered an invalid ip address.")
            return
        try:
            manual_port = int(input("Enter the port number to connect to: ").strip())
        except ValueError:
            print("Invalid port number.")
            return
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((manual_ip, manual_port))
            connection_message = f"LISTENING_PORT:{my_listening_port}|TEAM_NAME:{my_team_name}|manual connection message"
            s.send(connection_message.encode())
            print(f"Connected to {manual_ip}:{manual_port}")
            connected_peers[(manual_ip, manual_port)] = True
        except Exception as e:
            print(f"Failed to connect to {manual_ip}:{manual_port}: {e}")
        finally:
            s.close()
    else:
        print("Invalid choice. Please try again.")

def main():
    global my_listening_port, my_team_name
    my_team_name = input("Enter your team name: ").strip()
    try:
        my_port = int(input("Enter your port number: ").strip())
    except ValueError:
        print("Invalid port number. Exiting.")
        return
    my_listening_port = my_port

    threading.Thread(target=server_thread, args=(my_port,), daemon=True).start()
    print(f"Server listening on port {my_port}")

    while True:
        print("\n***** Menu *****")
        print("1. Send message")
        print("2. Query peers")
        print("3. Connect to peers (Auto or Manual)")
        print("0. Quit")
        choice = input("Enter your choice: ").strip()
        if choice == "1":
            send_message()
        elif choice == "2":
            query_peers()
        elif choice == "3":
            connect_to_peers()
        elif choice == "0":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
