#!/bin/bash

# Atualizando pacotes do sistema
echo "Atualizando pacotes do sistema..."
sudo apt update -y && sudo apt upgrade -y

# Instalando OpenVPN e Easy-RSA
echo "Instalando OpenVPN e Easy-RSA..."
sudo apt install -y openvpn easy-rsa

# Criando diretório para Easy-RSA
echo "Configurando Easy-RSA..."
make-cadir ~/openvpn-ca
cd ~/openvpn-ca

# Configurando variáveis para Easy-RSA
echo "Editando variáveis de configuração..."
sed -i 's/KEY_COUNTRY="US"/KEY_COUNTRY="BR"/' vars
sed -i 's/KEY_PROVINCE="CA"/KEY_PROVINCE="SP"/' vars
sed -i 's/KEY_CITY="SanFrancisco"/KEY_CITY="SaoPaulo"/' vars
sed -i 's/KEY_ORG="Fort-Funston"/KEY_ORG="MinhaOrganizacao"/' vars
sed -i 's/KEY_EMAIL="me@myhost.mydomain"/KEY_EMAIL="email@example.com"/' vars
sed -i 's/KEY_OU="MyOrganizationalUnit"/KEY_OU="MinhaUnidade"/' vars

# Gerando certificados e chaves
echo "Gerando certificados e chaves..."
source ./vars
./clean-all
./build-ca
./build-key-server server
./build-dh
openvpn --genkey --secret keys/ta.key

# Movendo chaves e certificados para o diretório do OpenVPN
sudo cp keys/{server.crt,server.key,ca.crt,dh.pem,ta.key} /etc/openvpn/

# Criando arquivo de configuração do OpenVPN com suporte a IPv6
echo "Criando arquivo de configuração do OpenVPN com suporte a IPv6..."
sudo tee /etc/openvpn/server.conf > /dev/null <<EOF
port 1194
proto udp
dev tun
ca ca.crt
cert server.crt
key server.key
dh dh.pem

# Configuração de IPv4
server 10.8.0.0 255.255.255.0
push "redirect-gateway def1 bypass-dhcp"
push "dhcp-option DNS 8.8.8.8"
push "dhcp-option DNS 8.8.4.4"

# Configuração de IPv6
server-ipv6 2a01:4f9:6b:f887::1/64  # Substitua pelo bloco IPv6
push "route-ipv6 2000::/3"
push "redirect-gateway ipv6"
tun-ipv6

keepalive 10 120
cipher AES-256-CBC
persist-key
persist-tun
status /var/log/openvpn-status.log
log-append /var/log/openvpn.log
verb 3
explicit-exit-notify 1
EOF

# Habilitando roteamento de pacotes IPv4 e IPv6
echo "Ativando roteamento de pacotes IPv4 e IPv6..."
sudo sed -i 's/#net.ipv4.ip_forward=1/net.ipv4.ip_forward=1/' /etc/sysctl.conf
echo 'net.ipv6.conf.all.forwarding = 1' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p

# Configurando o firewall para IPv4 e IPv6
echo "Configurando o firewall para IPv4 e IPv6..."
sudo ufw allow 1194/udp
sudo ufw allow OpenSSH
sudo ufw enable
sudo ufw reload

# Certificando que o UFW aceita conexões IPv6
echo "Configurando o UFW para suportar IPv6..."
sudo sed -i 's/IPV6=no/IPV6=yes/' /etc/default/ufw
sudo ufw reload

# Iniciando e habilitando o OpenVPN
echo "Iniciando e habilitando o OpenVPN..."
sudo systemctl start openvpn@server
sudo systemctl enable openvpn@server

# Adicionando repositório do Emby
echo "Adicionando repositório do Emby..."
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 41DFE385
echo "deb http://deb.emby.media/ stable main" | sudo tee /etc/apt/sources.list.d/emby-server.list
sudo apt update

# Instalando o Emby Server
echo "Instalando o Emby Server..."
sudo apt install -y emby-server

# Iniciando e habilitando o Emby Server
echo "Iniciando o Emby Server..."
sudo systemctl start emby-server
sudo systemctl enable emby-server

# Liberando portas do Emby no firewall
echo "Liberando portas do Emby no firewall..."
sudo ufw allow 8096/tcp
sudo ufw allow 8920/tcp
sudo ufw reload

echo "Instalação e configuração do OpenVPN (IPv6) e Emby finalizadas!"
