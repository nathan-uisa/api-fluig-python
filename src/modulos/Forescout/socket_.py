import socket
import sys

# Garante que não estamos importando um arquivo local errado
if "forescout/socket.py" in sys.argv[0]:
    
    sys.exit()

def iniciar():
    # Usando o módulo real do sistema
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 0.0.0.0 ouve em todas as interfaces de rede
        sock.bind(("0.0.0.0", 514))
        print("Servidor Syslog online na porta 514...")
        
        while True:
            data, addr = sock.recvfrom(4096)
            print(f"Recebido de {addr[0]}: {data.decode('utf-8', errors='ignore')}")
    except PermissionError:
        print("Erro: No Windows, você precisa rodar o VS Code/Terminal como ADMINISTRADOR para usar a porta 514.")
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    iniciar()